import os
import sys
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging

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

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

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
):
    """
    Upload a MIDI file and asynchronously generate the hymn remake.
    """
    file_bytes = await file.read()

    # Strict validation
    if len(file_bytes) < 4 or file_bytes[:4] != b'MThd':
        raise HTTPException(status_code=400, detail="Invalid MIDI file uploaded. Missing MThd header.")

    file_path = os.path.join("hymn_remaker/input", file.filename)
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # Load modules
    mods = get_modules()

    # Run the pipeline in the background so the HTTP request doesn't timeout
    loop = asyncio.get_running_loop()
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
        status_callback=lambda msg, prog: asyncio.run_coroutine_threadsafe(manager.broadcast({"message": msg, "progress": prog}), loop)
    )

    return JSONResponse(content={
        "status": "accepted",
        "message": f"File {file.filename} is being processed in the background.",
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
            # Handle incoming WebSocket messages if needed, otherwise just keep alive
            await websocket.send_text(f"Message text was: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/v1/radio/start")
async def start_radio(rtmp_url: str = Form(...)):
    global _radio_streamer
    if _radio_streamer and _radio_streamer.is_alive():
        return JSONResponse(status_code=400, content={"status": "error", "message": "Radio is already streaming"})

    _radio_streamer = RadioStreamer(output_dir="hymn_remaker/output", rtmp_url=rtmp_url)
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
    out_audio = os.path.join("hymn_remaker/output", "edit_preview.wav")

    target_path = file_path
    if file_path.lower().endswith('.mxl') or file_path.lower().endswith('.xml'):
        target_path = os.path.join("hymn_remaker/output", "edit_preview.mid")
        mods["mxl_parser"].process(file_path, target_path)

    renderer.render(target_path, out_audio)
    return {"status": "success", "preview_url": f"/output/edit_preview.wav"}

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
