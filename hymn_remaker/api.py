import os
import sys
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from fastapi.concurrency import run_in_threadpool
import logging
import json

from hymn_remaker.main import process_single_midi
from hymn_remaker.src.db import get_history, init_db
from hymn_remaker.src.midi_renderer import MidiRenderer
from hymn_remaker.src.remaker import MusicRemaker
from hymn_remaker.src.content_generator import ContentGenerator
from hymn_remaker.src.video_uploader import VideoProducer
from hymn_remaker.src.tts_generator import TTSGenerator
from hymn_remaker.src.musicxml_parser import MusicXMLParser
from hymn_remaker.src.omr_processor import OMRProcessor
from hymn_remaker.src.stem_separator import StemSeparator
from hymn_remaker.src.radio_streamer import RadioStreamer
from hymn_remaker.src.video_generator import AdvancedVideoGenerator

logger = logging.getLogger("HymnRemakerAPI")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Hymn Remaker API", version="5.38.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories and DB exist
os.makedirs("hymn_remaker/input", exist_ok=True)
os.makedirs("hymn_remaker/output", exist_ok=True)
init_db()

app.mount("/output", StaticFiles(directory="hymn_remaker/output"), name="output")

# Lazy load modules to prevent initialization errors on startup if keys are missing
_modules = None
_radio_streamer = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.pending_interactions = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

    async def request_interactive_review(self, data: dict):
        # We broadcast the request and wait for a response
        job_id = data.get("job_id", "default")
        self.pending_interactions[job_id] = asyncio.Future()

        await self.broadcast({
            "type": "interactive_review_request",
            "job_id": job_id,
            "data": data
        })

        # Wait until the frontend sends back the updated payload
        try:
            # Add a timeout so background thread doesn't hang forever if user closes tab
            result = await asyncio.wait_for(self.pending_interactions[job_id], timeout=300) # 5 min timeout
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Interactive review timeout for {job_id}")
            return None
        finally:
            self.pending_interactions.pop(job_id, None)

manager = ConnectionManager()

def get_modules():
    global _modules
    if not _modules:
        try:
            _modules = {
                "renderer": MidiRenderer(),
                "remaker": MusicRemaker(),
                "content_gen": ContentGenerator(),
                "video_producer": VideoProducer(),
                "tts_generator": TTSGenerator(),
                "mxl_parser": MusicXMLParser(),
                "omr_processor": OMRProcessor(),
                "stem_separator": StemSeparator(),
                "advanced_video_gen": AdvancedVideoGenerator(),
            }
        except Exception as e:
            logger.error(f"Failed to initialize modules: {e}")
            raise HTTPException(status_code=500, detail="Failed to initialize AI modules. Check API keys.")
    return _modules


@app.post("/api/v1/generate")
async def generate_hymn(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    style: str = Form("Deep House, high quality, electronic"),
    generate_vocals: bool = Form(False),
    normalize_audio: bool = Form(True),
    fade_in_ms: int = Form(0),
    fade_out_ms: int = Form(0),
    use_advanced_video: bool = Form(False),
    kids_mode: bool = Form(False),
    interactive_mode: bool = Form(False),
):
    """
    Upload a MIDI file and asynchronously generate the hymn remake.
    """
    file_bytes = await file.read()

    # Strict validation
    if len(file_bytes) < 4 or file_bytes[:4] != b'MThd':
        raise HTTPException(status_code=400, detail="Invalid MIDI file uploaded. Missing MThd header.")

    safe_filename = os.path.basename(file.filename)
    file_path = os.path.join("hymn_remaker/input", safe_filename)
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # Load modules
    mods = get_modules()

    # Run the pipeline in the background so the HTTP request doesn't timeout
    loop = asyncio.get_running_loop()

    def sync_interactive_callback(data):
        if not interactive_mode:
            return None
        data["job_id"] = safe_filename
        future = asyncio.run_coroutine_threadsafe(manager.request_interactive_review(data), loop)
        return future.result()

    background_tasks.add_task(
        process_single_midi,
        midi_path=file_path,
        output_dir="hymn_remaker/output",
        style=style,
        skip_render=False,
        skip_remake=False,
        upload=False,
        renderer=mods["renderer"],
        remaker=mods["remaker"],
        content_gen=mods["content_gen"],
        video_producer=mods["video_producer"],
        mxl_parser=mods["mxl_parser"],
        omr_processor=mods["omr_processor"],
        tts_generator=mods["tts_generator"],
        stem_separator=mods["stem_separator"],
        normalize_audio=normalize_audio,
        fade_in_ms=fade_in_ms,
        fade_out_ms=fade_out_ms,
        generate_vocals=generate_vocals,
        use_advanced_video=use_advanced_video,
        advanced_video_gen=mods["advanced_video_gen"],
        kids_mode=kids_mode,
        interactive_callback=sync_interactive_callback,
        status_callback=lambda msg, prog: asyncio.run_coroutine_threadsafe(manager.broadcast({"message": msg, "progress": prog}), loop)
    )

    return JSONResponse(content={
        "status": "accepted",
        "message": f"File {safe_filename} is being processed in the background.",
        "configuration": {
            "style": style,
            "generate_vocals": generate_vocals,
        }
    })


@app.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "interactive_review_response":
                    job_id = msg.get("job_id", "default")
                    if job_id in manager.pending_interactions and not manager.pending_interactions[job_id].done():
                        manager.pending_interactions[job_id].set_result(msg.get("data"))
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/v1/radio/start")
async def start_radio(rtmp_url: str = Form(...)):
    global _radio_streamer
    if _radio_streamer and _radio_streamer.is_alive():
        return JSONResponse(status_code=400, content={"status": "error", "message": "Radio is already streaming"})

    _radio_streamer = RadioStreamer(rtmp_url=rtmp_url, input_dir="hymn_remaker/output")
    _radio_streamer.start()
    return {"status": "success", "message": "Radio streaming started."}

@app.post("/api/v1/radio/stop")
async def stop_radio():
    global _radio_streamer
    if _radio_streamer:
        _radio_streamer.stop()
        _radio_streamer = None
        return {"status": "success", "message": "Radio streaming stopped."}
    return JSONResponse(status_code=400, content={"status": "error", "message": "Radio is not streaming"})

@app.post("/api/v1/radio/skip")
async def skip_radio():
    global _radio_streamer
    if _radio_streamer:
        _radio_streamer.skip_current()
        return {"status": "success", "message": "Skipped current track."}
    return JSONResponse(status_code=400, content={"status": "error", "message": "Radio is not streaming"})

@app.get("/api/v1/radio/status")
async def radio_status():
    global _radio_streamer
    if _radio_streamer and _radio_streamer.is_alive():
        return {"status": "streaming", "current_track": getattr(_radio_streamer, 'current_track_name', 'Unknown')}
    return {"status": "stopped", "current_track": None}

@app.post("/api/v1/editor/preview")
async def editor_preview(file: UploadFile = File(...)):
    file_bytes = await file.read()
    safe_filename = os.path.basename(file.filename)
    file_path = os.path.join("hymn_remaker/input", f"edit_{safe_filename}")
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    mods = get_modules()
    renderer = mods["renderer"]
    out_audio = os.path.join("hymn_remaker/output", f"edit_preview_{safe_filename}.wav")

    target_path = file_path
    if file_path.lower().endswith('.mxl') or file_path.lower().endswith('.xml'):
        target_path = os.path.join("hymn_remaker/output", f"edit_preview_{safe_filename}.mid")
        mods["mxl_parser"].process(file_path, target_path)

    # Run the heavy C++ render operation in a background thread to prevent blocking the async loop
    await run_in_threadpool(renderer.render, target_path, out_audio)

    return {"status": "success", "preview_url": f"/output/edit_preview_{safe_filename}.wav"}

@app.get("/api/v1/history")
def get_generation_history():
    """Retrieve all successfully generated hymns from the SQLite database."""
    history = get_history()
    return {"status": "success", "data": history}

@app.get("/api/v1/system")
def get_system_status():
    """Retrieve system dependencies for debugging."""
    import subprocess
    import importlib.metadata

    status = {"binaries": {}, "python_packages": {}}

    try:
        status["binaries"]["ffmpeg"] = subprocess.check_output(["ffmpeg", "-version"]).decode().split('\n')[0]
    except Exception:
        status["binaries"]["ffmpeg"] = "Not Found"

    try:
        status["binaries"]["fluidsynth"] = subprocess.check_output(["fluidsynth", "--version"]).decode().split('\n')[0]
    except Exception:
        status["binaries"]["fluidsynth"] = "Not Found"

    req_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if os.path.exists(req_path):
        with open(req_path, "r") as f:
            reqs = f.read().splitlines()
        for req in reqs:
            if not req.strip() or req.startswith('#'):
                continue
            pkg_name = req.split('==')[0].split('>=')[0].split('<')[0].strip()
            try:
                status["python_packages"][pkg_name] = importlib.metadata.version(pkg_name)
            except importlib.metadata.PackageNotFoundError:
                status["python_packages"][pkg_name] = "Not Installed"

    return {"status": "success", "data": status}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

@app.post("/api/v1/kids/scrape")
async def kids_scrape(background_tasks: BackgroundTasks):
    """
    Scrape BitMidi for nursery rhymes and process them.
    """
    from hymn_remaker.src.children_song_finder import ChildrenSongFinder

    loop = asyncio.get_running_loop()
    asyncio.run_coroutine_threadsafe(manager.broadcast({"message": "Starting BitMidi dynamic scraper...", "progress": 5}), loop)

    def scrape_and_process():
        finder = ChildrenSongFinder()
        downloaded = finder.download_all("hymn_remaker/input")

        asyncio.run_coroutine_threadsafe(manager.broadcast({"message": f"Downloaded {len(downloaded)} files. Starting pipeline...", "progress": 10}), loop)

        if downloaded:
            mods = get_modules()
            # Just process the first one for the demo/UI
            file_path = downloaded[0]
            safe_filename = os.path.basename(file_path)

            process_single_midi(
                midi_path=file_path,
                output_dir="hymn_remaker/output",
                style="nursery rhyme, playful, happy, glockenspiel, toy piano, acoustic guitar, kids music, upbeat, high quality",
                skip_render=False,
                skip_remake=False,
                upload=False,
                renderer=mods["renderer"],
                remaker=mods["remaker"],
                content_gen=mods["content_gen"],
                video_producer=mods["video_producer"],
                mxl_parser=mods["mxl_parser"],
                omr_processor=mods["omr_processor"],
                tts_generator=mods["tts_generator"],
                stem_separator=mods["stem_separator"],
                normalize_audio=True,
                fade_in_ms=0,
                fade_out_ms=0,
                generate_vocals=False,
                use_advanced_video=False,
                advanced_video_gen=mods["advanced_video_gen"],
                kids_mode=True,
                interactive_callback=None,
                status_callback=lambda msg, prog: asyncio.run_coroutine_threadsafe(manager.broadcast({"message": msg, "progress": prog}), loop)
            )
        else:
            asyncio.run_coroutine_threadsafe(manager.broadcast({"message": "Scraping completed, no new files found.", "progress": 100}), loop)

    background_tasks.add_task(scrape_and_process)

    return JSONResponse(content={
        "status": "accepted",
        "message": "Scraping and processing started in background."
    })
