import os
import sys
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
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

logger = logging.getLogger("HymnRemakerAPI")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Hymn Remaker API", version="1.26.0")

# Ensure directories and DB exist
os.makedirs("hymn_remaker/input", exist_ok=True)
os.makedirs("hymn_remaker/output", exist_ok=True)
init_db()

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
        status_callback=lambda msg, prog: logger.info(f"Background Progress [{prog}%]: {msg}")
    )

    return JSONResponse(content={
        "status": "accepted",
        "message": f"File {file.filename} is being processed in the background.",
        "configuration": {
            "style": style,
            "generate_vocals": generate_vocals,
        }
    })


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
