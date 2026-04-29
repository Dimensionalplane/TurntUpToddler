import pika
import time
import os
import json
import logging
from dotenv import load_dotenv

# Import the actual pipeline logic from the shared src
from src.midi_renderer import MidiRenderer
from src.remaker import MusicRemaker
from src.content_generator import ContentGenerator
from src.video_uploader import VideoProducer
from src.tts_generator import TTSGenerator
from src.musicxml_parser import MusicXMLParser
from src.omr_processor import OMRProcessor
from src.stem_separator import StemSeparator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
RABBITMQ_QUEUE = "render_jobs"

# Initialize singletons for the worker node
renderer = MidiRenderer()
remaker = MusicRemaker()
content_gen = ContentGenerator()
video_producer = VideoProducer()
mxl_parser = MusicXMLParser()
omr_processor = OMRProcessor()
tts_generator = TTSGenerator()
stem_separator = StemSeparator()

def callback(ch, method, properties, body):
    try:
        job = json.loads(body)
        job_id = job.get('job_id')
        file_path = job.get('file_path')
        logger.info(f"Received render job: {job_id} for file: {file_path}")

        # Here we would normally execute the full process_single_midi logic.
        # For the scaffolding phase, we confirm the models are loaded and ready.
        logger.info("Executing isolated backend ML inference...")

        # Simulated heavy work
        time.sleep(3)

        logger.info(f"Completed render job: {job_id}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Error processing job: {e}")
        # Nack and requeue on failure
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def main():
    logger.info(f"Connecting to RabbitMQ at {RABBITMQ_HOST}...")

    # Retry connection loop to allow RabbitMQ to start up
    connection = None
    retries = 5
    while retries > 0:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            break
        except pika.exceptions.AMQPConnectionError:
            logger.warning("RabbitMQ not ready, retrying in 5 seconds...")
            time.sleep(5)
            retries -= 1

    if not connection:
        logger.error("Failed to connect to RabbitMQ.")
        return

    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)

    # Only dispatch one message to a worker at a time
    channel.basic_qos(prefetch_count=1)

    channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=callback)

    logger.info('Renderer microservice started. Waiting for jobs...')
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Shutting down renderer...")
        channel.stop_consuming()
    finally:
        connection.close()

if __name__ == '__main__':
    main()
