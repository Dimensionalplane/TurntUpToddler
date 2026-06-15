import os
import sys
import json
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import logging
import redis as redis_lib
import pika
import shutil

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

app = FastAPI(title="Hymn Remaker API", version="1.33.0")

# Add CORS middleware to allow requests from the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; refine for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories and DB exist
os.makedirs("hymn_remaker/input", exist_ok=True)
os.makedirs("hymn_remaker/output", exist_ok=True)
init_db()

# Global radio streamer instance
radio_streamer = None

# Lazy load modules to prevent initialization errors on startup if keys are missing
_modules = None

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


import uuid

@app.post("/api/v1/generate")
async def generate_hymn(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    style: str = Form("Deep House, high quality, electronic"),
    generate_vocals: bool = Form(False),
    voice_id: str = Form(""),
    model: str = Form("eleven_multilingual_v2"),
    video_format: str = Form("Standard 16:9"),
    create_shorts: bool = Form(False),
    enable_visualizer: bool = Form(False),
    visualizer_mode: str = Form("cline"),
    kids_mode: bool = Form(False),
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

    job_id = str(uuid.uuid4())
    redis_host = os.environ.get("REDIS_HOST", "localhost")
    try:
        r = redis_lib.Redis(host=redis_host, port=6379, db=0)
        r.set(f"job:{job_id}:status", "queued")
    except Exception as e:
        logger.warning(f"Failed to set initial job status in Redis: {e}")

    # Load modules
    mods = get_modules()

    # Queue the job to RabbitMQ cluster for distributed processing
    try:
        rabbitmq_host = os.environ.get("RABBITMQ_HOST", "localhost")
        connection = pika.BlockingConnection(pika.ConnectionParameters(rabbitmq_host))
        channel = connection.channel()
        channel.queue_declare(queue='render_jobs', durable=True)

        job_data = {
            "job_id": job_id,
            "midi_path": file_path,
            "output_dir": "hymn_remaker/output",
            "style": style,
            "generate_vocals": generate_vocals,
            "voice_id": voice_id,
            "model": model,
            "video_format": video_format,
            "create_shorts": create_shorts,
            "enable_visualizer": enable_visualizer,
            "visualizer_mode": visualizer_mode,
            "kids_mode": kids_mode
        }

        channel.basic_publish(
            exchange='',
            routing_key='render_jobs',
            body=json.dumps(job_data),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
    except Exception as e:
        logger.error(f"Failed to queue job to RabbitMQ: {e}")
        # Fallback to local background task if cluster is down
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
            voice_id=voice_id,
            model=model,
            video_format=video_format,
            create_shorts=create_shorts,
            enable_visualizer=enable_visualizer,
            visualizer_mode=visualizer_mode,
            kids_mode=kids_mode,
            status_callback=lambda msg, prog: logger.info(f"Background Progress [{prog}%]: {msg}")
        )

    return JSONResponse(content={
        "status": "accepted",
        "job_id": job_id,
        "message": f"File {file.filename} is being processed in the background.",
        "configuration": {
            "style": style,
            "generate_vocals": generate_vocals,
            "voice_id": voice_id,
            "model": model,
            "video_format": video_format,
            "create_shorts": create_shorts,
            "enable_visualizer": enable_visualizer,
            "visualizer_mode": visualizer_mode,
            "kids_mode": kids_mode
        }
    })


@app.get("/api/v1/history")
def get_generation_history():
    """Retrieve all successfully generated hymns from the SQLite database."""
    history = get_history()
    return {"status": "success", "data": history}


@app.post("/api/v1/editor/preview")
async def editor_preview(
    file: UploadFile = File(...),
    soundfont: str = Form(None)
):
    """
    Render a fast audio preview of a MIDI or MusicXML file.
    """
    file_bytes = await file.read()
    # Sanitize filename
    safe_name = "".join([c for c in file.filename if c.isalnum() or c in "._-"])
    temp_in = os.path.join("hymn_remaker/input", f"preview_{safe_name}")
    with open(temp_in, "wb") as f:
        f.write(file_bytes)

    mods = get_modules()
    renderer = mods["renderer"]
    if soundfont:
        renderer = MidiRenderer(soundfont_path=soundfont)

    target_mid = temp_in
    if file.filename.lower().endswith(('.mxl', '.xml')):
        target_mid = os.path.join("hymn_remaker/output", f"preview_{file.filename}.mid")
        mods["mxl_parser"].process(temp_in, target_mid)

    out_wav = os.path.join("hymn_remaker/output", f"preview_{file.filename}.wav")
    renderer.render(target_mid, out_wav)

    return FileResponse(out_wav, media_type="audio/wav", filename=f"preview_{file.filename}.wav")


@app.post("/api/v1/editor/extract")
async def editor_extract(
    file: UploadFile = File(...)
):
    """
    Extract metadata and note-synced lyrics from a MusicXML file.
    """
    if not file.filename.lower().endswith(('.mxl', '.xml')):
        raise HTTPException(status_code=400, detail="Only MusicXML (.mxl, .xml) files are supported for extraction.")

    file_bytes = await file.read()
    # Sanitize filename
    safe_name = "".join([c for c in file.filename if c.isalnum() or c in "._-"])
    temp_in = os.path.join("hymn_remaker/input", f"extract_{safe_name}")
    with open(temp_in, "wb") as f:
        f.write(file_bytes)

    mods = get_modules()
    dummy_mid = os.path.join("hymn_remaker/output", "dummy_extract.mid")
    metadata = mods["mxl_parser"].process(temp_in, dummy_mid)

    return {"status": "success", "metadata": metadata}


@app.post("/api/v1/editor/cluster/submit")
async def editor_cluster_submit(
    prompt: str = Form("stub prompt"),
    target_bpm: int = Form(120),
    model_id: str = Form("stub_model")
):
    """
    Submit a job to the RabbitMQ render cluster.
    """
    try:
        job_id = str(uuid.uuid4())
        redis_host = os.environ.get("REDIS_HOST", "localhost")
        r = redis_lib.Redis(host=redis_host, port=6379, db=0)
        r.set(f"job:{job_id}:status", "queued")

        rabbitmq_host = os.environ.get("RABBITMQ_HOST", "localhost")
        connection = pika.BlockingConnection(pika.ConnectionParameters(rabbitmq_host))
        channel = connection.channel()
        channel.queue_declare(queue='render_jobs', durable=True)

        job_data = {
            "job_id": job_id,
            "prompt": prompt,
            "target_bpm": target_bpm,
            "model_id": model_id
        }

        channel.basic_publish(
            exchange='',
            routing_key='render_jobs',
            body=json.dumps(job_data),
            properties=pika.BasicProperties(
                delivery_mode=2,
            )
        )
        connection.close()

        return {"status": "success", "job_id": job_id, "message": "Job submitted to cluster."}
    except Exception as e:
        logger.error(f"Failed to submit cluster job: {e}")
        raise HTTPException(status_code=500, detail=f"Cluster submission failed: {str(e)}")


@app.post("/api/v1/radio/start")
async def radio_start(
    stream_url: str = Form(...),
    input_dir: str = Form("hymn_remaker/output")
):
    """
    Start the live RTMP radio broadcast.
    """
    global radio_streamer
    if radio_streamer and radio_streamer.is_streaming:
        raise HTTPException(status_code=400, detail="Radio is already streaming.")

    try:
        radio_streamer = RadioStreamer(stream_url, input_dir=input_dir)
        radio_streamer.start()
        return {"status": "success", "message": "Radio broadcast started."}
    except Exception as e:
        logger.error(f"Failed to start radio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/radio/stop")
async def radio_stop():
    """
    Stop the live RTMP radio broadcast.
    """
    global radio_streamer
    if radio_streamer:
        radio_streamer.stop()
        radio_streamer = None
        return {"status": "success", "message": "Radio broadcast stopped."}
    return {"status": "info", "message": "Radio was not running."}


@app.post("/api/v1/radio/skip")
async def radio_skip():
    """
    Skip the current track in the radio broadcast.
    """
    global radio_streamer
    if radio_streamer and radio_streamer.is_streaming:
        radio_streamer.skip_track()
        return {"status": "success", "message": "Skipping current track."}
    raise HTTPException(status_code=400, detail="Radio is not streaming.")


@app.get("/api/v1/radio/status")
async def radio_status():
    """
    Retrieve the current status and track of the radio broadcast.
    """
    global radio_streamer
    if radio_streamer:
        return {
            "is_streaming": radio_streamer.is_streaming,
            "current_track": radio_streamer.current_track
        }
    return {"is_streaming": False, "current_track": None}


@app.get("/api/v1/jobs/{job_id}")
def get_job_status(job_id: str):
    """
    Retrieve the status of a specific background job from Redis.
    Matches the logic used in the Streamlit app.py toolbar.
    """
    try:
        redis_host = os.environ.get("REDIS_HOST", "localhost")
        r = redis_lib.Redis(host=redis_host, port=6379, db=0)
        status = r.get(f"job:{job_id}:status")
        if status:
            return {"job_id": job_id, "status": status.decode("utf-8")}
        else:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    except Exception as e:
        logger.error(f"Failed to connect to Redis for job status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error accessing job store.")


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
