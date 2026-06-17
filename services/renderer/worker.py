import pika
import json
import redis
import time
import os
import sys
import logging

# Ensure project root is in path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from hymn_remaker.main import process_single_midi
from hymn_remaker.src.midi_renderer import MidiRenderer
from hymn_remaker.src.remaker import MusicRemaker
from hymn_remaker.src.suno_remaker import SunoRemaker
from hymn_remaker.src.content_generator import ContentGenerator
from hymn_remaker.src.video_uploader import VideoProducer
from hymn_remaker.src.musicxml_parser import MusicXMLParser
from hymn_remaker.src.omr_processor import OMRProcessor
from hymn_remaker.src.stem_separator import StemSeparator
from hymn_remaker.src.tts_generator import TTSGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RenderWorker")

RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')

# Global Module Initialization (Lazy)
_modules = None

def get_modules():
    global _modules
    if not _modules:
        logger.info("Initializing Pipeline Modules for Worker...")
        # Reuse existing Redis connection 'r'
        _modules = {
            "renderer": MidiRenderer(),
            "remaker": MusicRemaker(),
            "suno_remaker": SunoRemaker(),
            "content_gen": ContentGenerator(redis_client=r),
            "video_producer": VideoProducer(),
            "mxl_parser": MusicXMLParser(),
            "omr_processor": OMRProcessor(),
            "stem_separator": StemSeparator(),
            "tts_generator": TTSGenerator()
        }
    return _modules

# Connect to Redis
r = redis.Redis(host=REDIS_HOST, port=6379, db=0)

def render_job(ch, method, properties, body):
    try:
        job_data = json.loads(body)
        job_id = job_data.get('job_id')
        midi_path = job_data.get('midi_path') # Worker needs a file path

        if not midi_path or not os.path.exists(midi_path):
            logger.error(f"Job {job_id} failed: MIDI path invalid or missing: {midi_path}")
            if job_id: r.set(f"job:{job_id}:status", "failed")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        logger.info(f" [x] Received job {job_id} for {midi_path}")

        if job_id:
            r.set(f"job:{job_id}:status", "processing")

        mods = get_modules()

        # Extract parameters from job_data or use defaults
        style = job_data.get('style', "Deep House, high quality, electronic")
        output_dir = job_data.get('output_dir', "hymn_remaker/output")

        def worker_status_callback(msg, prog):
            logger.info(f"Job {job_id} Progress: {msg} ({prog}%)")
            if job_id:
                r.set(f"job:{job_id}:progress", prog)
                r.set(f"job:{job_id}:message", msg)

        def worker_interactive_callback(data):
            if not job_id: return data

            logger.info(f"Job {job_id} entering interactive review state.")
            # Store data for frontend to fetch
            r.set(f"job:{job_id}:review_data", json.dumps(data))
            # Set status to awaiting_review
            r.set(f"job:{job_id}:status", "awaiting_review")

            # Poll for approval
            while True:
                approved = r.get(f"job:{job_id}:approved")
                if approved and approved.decode('utf-8') == "true":
                    logger.info(f"Job {job_id} approved. Resuming...")
                    # Get potentially edited data
                    updated_data_raw = r.get(f"job:{job_id}:review_data")
                    # Clear flags
                    r.delete(f"job:{job_id}:approved")
                    r.delete(f"job:{job_id}:review_data")
                    # Reset status to processing
                    r.set(f"job:{job_id}:status", "processing")

                    if updated_data_raw:
                        return json.loads(updated_data_raw)
                    return data

                time.sleep(2)

        interactive_mode = job_data.get('interactive_mode', False)

        process_single_midi(
            midi_path,
            output_dir,
            style,
            skip_render=job_data.get('skip_render', False),
            skip_remake=job_data.get('skip_remake', False),
            upload=job_data.get('upload', False),
            renderer=mods["renderer"],
            remaker=mods["remaker"],
            suno_remaker=mods["suno_remaker"],
            remake_priority=job_data.get('remake_priority', "suno"),
            content_gen=mods["content_gen"],
            video_producer=mods["video_producer"],
            mxl_parser=mods["mxl_parser"],
            omr_processor=mods["omr_processor"],
            tts_generator=mods["tts_generator"],
            stem_separator=mods["stem_separator"],
            generate_vocals=job_data.get('generate_vocals', False),
            arrangement_style=job_data.get('arrangement_style', "Original"),
            video_format=job_data.get('video_format', "Standard 16:9"),
            resolution=job_data.get('resolution', "1080p"),
            kids_mode=job_data.get('kids_mode', False),
            interactive_callback=worker_interactive_callback if interactive_mode else None,
            status_callback=worker_status_callback
        )

        if job_id:
            r.set(f"job:{job_id}:status", "completed")

        logger.info(f" [x] Finished job {job_id}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        logger.error(f"Worker Error processing job: {e}")
        if 'job_id' in locals() and job_id:
            r.set(f"job:{job_id}:status", "failed")
        ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()

    channel.queue_declare(queue='render_jobs', durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='render_jobs', on_message_callback=render_job)

    logger.info(' [*] Render Worker Waiting for jobs. To exit press CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
