import os
import sys
import json
import uuid
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import logging
import redis as redis_lib
import pika
import shutil
import anyio

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

app = FastAPI(title="Hymn Remaker API", version="1.41.0")

# Add CORS middleware to allow requests from the Next.js frontend
frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories and DB exist
os.makedirs("hymn_remaker/input", exist_ok=True)
os.makedirs("hymn_remaker/output", exist_ok=True)
init_db()

# Serve output directory as static files
app.mount("/output", StaticFiles(directory="hymn_remaker/output"), name="output")

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
    voice_id: str = Form(""),
    model: str = Form("eleven_multilingual_v2"),
    video_format: str = Form("Standard 16:9"),
    create_shorts: bool = Form(False),
    enable_visualizer: bool = Form(False),
    visualizer_mode: str = Form("cline"),
    use_dynamic_video: bool = Form(False),
    kids_mode: bool = Form(False),
    interactive_mode: bool = Form(False),
    suno_session: str = Form(None),
    remake_priority: str = Form("suno"),
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
        "use_dynamic_video": use_dynamic_video,
        "kids_mode": kids_mode,
        "interactive_mode": interactive_mode,
        "suno_session": suno_session,
        "remake_priority": remake_priority,
        "normalize_audio": normalize_audio,
        "fade_in_ms": fade_in_ms,
        "fade_out_ms": fade_out_ms
    }

    try:
        r = redis_lib.Redis(host=redis_host, port=6379, db=0)
        r.set(f"job:{job_id}:status", "queued")
        r.set(f"job:{job_id}:config", json.dumps(job_data))
    except Exception as e:
        logger.warning(f"Failed to set initial job status/config in Redis: {e}")

    # Load modules
    mods = get_modules()

    # Queue the job to RabbitMQ cluster for distributed processing
    async def queue_job():
        rabbitmq_host = os.environ.get("RABBITMQ_HOST", "localhost")

        def blocking_publish():
            connection = pika.BlockingConnection(pika.ConnectionParameters(rabbitmq_host))
            channel = connection.channel()
            channel.queue_declare(queue='render_jobs', durable=True)

            channel.basic_publish(
                exchange='',
                routing_key='render_jobs',
                body=json.dumps(job_data),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            connection.close()

        await anyio.to_thread.run_sync(blocking_publish)

    try:
        await queue_job()
    except Exception as e:
        logger.error(f"Failed to queue job to RabbitMQ: {e}")
        # Fallback to local background task if cluster is down
        # Update Redis to processing since it's immediate
        try:
            r = redis_lib.Redis(host=redis_host, port=6379, db=0)
            r.set(f"job:{job_id}:status", "processing")
        except: pass

        def local_task_wrapper(*args, **kwargs):
            def local_status_callback(msg, prog):
                try:
                    r_l = redis_lib.Redis(host=redis_host, port=6379, db=0)
                    r_l.set(f"job:{job_id}:progress", prog)
                    r_l.set(f"job:{job_id}:message", msg)
                except: pass

            kwargs['status_callback'] = local_status_callback
            try:
                process_single_midi(*args, **kwargs)
                try:
                    r_local = redis_lib.Redis(host=redis_host, port=6379, db=0)
                    r_local.set(f"job:{job_id}:status", "completed")
                    r_local.set(f"job:{job_id}:progress", 100)
                except: pass
            except:
                try:
                    r_local = redis_lib.Redis(host=redis_host, port=6379, db=0)
                    r_local.set(f"job:{job_id}:status", "failed")
                except: pass

        background_tasks.add_task(
            local_task_wrapper,
            midi_path=file_path,
            output_dir="hymn_remaker/output",
            style=style,
            skip_render=False,
            skip_remake=False,
            upload=False,
            renderer=mods["renderer"],
            remaker=mods["remaker"],
            suno_remaker=mods.get("suno_remaker"),
            remake_priority="suno",
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
            use_dynamic_video=use_dynamic_video,
            kids_mode=kids_mode,
            interactive_callback=None, # local fallback doesn't support interactive yet
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
            "use_dynamic_video": use_dynamic_video,
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
    Start the live RTMP radio broadcast via distributed signal.
    """
    try:
        redis_host = os.environ.get("REDIS_HOST", "localhost")
        r = redis_lib.Redis(host=redis_host, port=6379, db=0)
        r.publish('radio_commands', json.dumps({
            "command": "START",
            "stream_url": stream_url,
            "input_dir": input_dir
        }))
        return {"status": "success", "message": "Radio start command published."}
    except Exception as e:
        logger.error(f"Failed to publish radio start: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/radio/stop")
async def radio_stop():
    """
    Stop the live RTMP radio broadcast via distributed signal.
    """
    try:
        redis_host = os.environ.get("REDIS_HOST", "localhost")
        r = redis_lib.Redis(host=redis_host, port=6379, db=0)
        r.publish('radio_commands', json.dumps({"command": "STOP"}))
        return {"status": "success", "message": "Radio stop command published."}
    except Exception as e:
        logger.error(f"Failed to publish radio stop: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/radio/skip")
async def radio_skip():
    """
    Skip the current track in the radio broadcast via distributed signal.
    """
    try:
        redis_host = os.environ.get("REDIS_HOST", "localhost")
        r = redis_lib.Redis(host=redis_host, port=6379, db=0)
        r.publish('radio_commands', json.dumps({"command": "SKIP"}))
        return {"status": "success", "message": "Radio skip command published."}
    except Exception as e:
        logger.error(f"Failed to publish radio skip: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/radio/status")
async def radio_status():
    """
    Retrieve the current status of the radio broadcast from shared Redis state.
    """
    try:
        redis_host = os.environ.get("REDIS_HOST", "localhost")
        r = redis_lib.Redis(host=redis_host, port=6379, db=0)
        status_raw = r.get('radio:status')
        if status_raw:
            return json.loads(status_raw)
        return {"is_streaming": False, "current_track": None}
    except Exception as e:
        logger.error(f"Failed to fetch radio status: {e}")
        return {"is_streaming": False, "current_track": None, "error": str(e)}


@app.get("/api/v1/jobs/{job_id}/review")
def get_job_review_data(job_id: str):
    """
    Retrieve pending metadata/lyrics/art_prompt from Redis for interactive review.
    """
    try:
        redis_host = os.environ.get("REDIS_HOST", "localhost")
        r = redis_lib.Redis(host=redis_host, port=6379, db=0)
        review_data = r.get(f"job:{job_id}:review_data")
        if review_data:
            return json.loads(review_data)
        else:
            raise HTTPException(status_code=404, detail="Review data not found or job not in review state.")
    except Exception as e:
        logger.error(f"Failed to fetch review data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/jobs/{job_id}/review")
async def post_job_review_approval(job_id: str, data: dict):
    """
    Update the generated content and set the approval flag in Redis.
    """
    try:
        redis_host = os.environ.get("REDIS_HOST", "localhost")
        r = redis_lib.Redis(host=redis_host, port=6379, db=0)
        # Update the data the worker is waiting for
        r.set(f"job:{job_id}:review_data", json.dumps(data))
        # Signal approval
        r.set(f"job:{job_id}:approved", "true")
        return {"status": "success", "message": "Content approved and updated."}
    except Exception as e:
        logger.error(f"Failed to submit review approval: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/jobs/{job_id}/retry")
async def retry_job(job_id: str, background_tasks: BackgroundTasks):
    """
    Fetch a failed job's configuration and re-queue it.
    """
    redis_host = os.environ.get("REDIS_HOST", "localhost")
    try:
        r = redis_lib.Redis(host=redis_host, port=6379, db=0)
        config_raw = r.get(f"job:{job_id}:config")
        if not config_raw:
            raise HTTPException(status_code=404, detail="Original job configuration not found.")

        old_config = json.loads(config_raw)

        # Create new job context
        new_job_id = str(uuid.uuid4())
        new_config = old_config.copy()
        new_config["job_id"] = new_job_id

        r.set(f"job:{new_job_id}:status", "queued")
        r.set(f"job:{new_job_id}:config", json.dumps(new_config))
        r.set(f"job:{new_job_id}:message", f"Retrying from job {job_id}...")

        async def queue_job():
            rabbitmq_host = os.environ.get("RABBITMQ_HOST", "localhost")
            def blocking_publish():
                connection = pika.BlockingConnection(pika.ConnectionParameters(rabbitmq_host))
                channel = connection.channel()
                channel.queue_declare(queue='render_jobs', durable=True)
                channel.basic_publish(
                    exchange='',
                    routing_key='render_jobs',
                    body=json.dumps(new_config),
                    properties=pika.BasicProperties(delivery_mode=2)
                )
                connection.close()
            await anyio.to_thread.run_sync(blocking_publish)

        try:
            await queue_job()
        except Exception as e:
            logger.error(f"Failed to queue retry job to RabbitMQ: {e}")
            r.set(f"job:{new_job_id}:status", "processing")
            mods = get_modules()

            def local_task_wrapper(config):
                job_id_loc = config["job_id"]
                def local_status_callback(msg, prog):
                    try:
                        r_l = redis_lib.Redis(host=redis_host, port=6379, db=0)
                        r_l.set(f"job:{job_id_loc}:progress", prog)
                        r_l.set(f"job:{job_id_loc}:message", msg)
                    except: pass
                try:
                    process_single_midi(
                        midi_path=config["midi_path"],
                        output_dir=config["output_dir"],
                        style=config["style"],
                        skip_render=False,
                        skip_remake=False,
                        upload=False,
                        renderer=mods["renderer"],
                        remaker=mods["remaker"],
                        suno_remaker=mods.get("suno_remaker"),
                        remake_priority=config.get("remake_priority", "suno"),
                        content_gen=mods["content_gen"],
                        video_producer=mods["video_producer"],
                        mxl_parser=mods["mxl_parser"],
                        omr_processor=mods["omr_processor"],
                        tts_generator=mods["tts_generator"],
                        stem_separator=mods["stem_separator"],
                        normalize_audio=config.get("normalize_audio", True),
                        fade_in_ms=config.get("fade_in_ms", 0),
                        fade_out_ms=config.get("fade_out_ms", 0),
                        generate_vocals=config["generate_vocals"],
                        voice_id=config["voice_id"],
                        model=config["model"],
                        video_format=config["video_format"],
                        create_shorts=config["create_shorts"],
                        enable_visualizer=config["enable_visualizer"],
                        visualizer_mode=config["visualizer_mode"],
                        use_dynamic_video=config.get("use_dynamic_video", False),
                        kids_mode=config["kids_mode"],
                        interactive_callback=None,
                        status_callback=local_status_callback
                    )
                    r.set(f"job:{job_id_loc}:status", "completed")
                    r.set(f"job:{job_id_loc}:progress", 100)
                except Exception as ex:
                    logger.error(f"Retry local task failed: {ex}")
                    r.set(f"job:{job_id_loc}:status", "failed")

            background_tasks.add_task(local_task_wrapper, new_config)

        return {"status": "success", "new_job_id": new_job_id, "message": "Job re-queued for retry."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/jobs/{job_id}")
def get_job_status(job_id: str):
    """
    Retrieve the status, progress, and last message of a specific background job from Redis.
    """
    try:
        redis_host = os.environ.get("REDIS_HOST", "localhost")
        r = redis_lib.Redis(host=redis_host, port=6379, db=0)
        status = r.get(f"job:{job_id}:status")
        progress = r.get(f"job:{job_id}:progress")
        message = r.get(f"job:{job_id}:message")

        if status:
            return {
                "job_id": job_id,
                "status": status.decode("utf-8"),
                "progress": int(progress.decode("utf-8")) if progress else 0,
                "message": message.decode("utf-8") if message else "Queued..."
            }
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
