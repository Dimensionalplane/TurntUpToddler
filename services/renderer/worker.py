import pika
import json
import redis
import time
import os
import sys
import subprocess
import logging

RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')

# Connect to Redis
r = redis.Redis(host=REDIS_HOST, port=6379, db=0)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_stem_separation(job_id, file_path, output_dir):
    try:
        logger.info(f"Running Demucs stem separation on {file_path}...")
        os.makedirs(output_dir, exist_ok=True)
        cmd = [
            "python", "-m", "demucs.separate",
            "-n", "htdemucs",
            "-o", output_dir,
            file_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        r.set(f"job:{job_id}:status", "completed")
        logger.info("Stem separation complete.")
    except Exception as e:
        logger.error(f"Demucs failed: {e}")
        r.set(f"job:{job_id}:status", "failed")
        r.set(f"job:{job_id}:error", str(e))

def handle_omr(job_id, file_path, output_dir):
    try:
        logger.info(f"Running OMR (oemer) on {file_path}...")
        cmd = ["oemer", file_path]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

        # Locate the output file. oemer typically generates a .musicxml file in the same directory as the input.
        name_no_ext = os.path.splitext(os.path.basename(file_path))[0]
        input_dir = os.path.dirname(file_path)
        expected_output = os.path.join(input_dir, f"{name_no_ext}.musicxml")

        if os.path.exists(expected_output):
            import shutil
            output_mxl_path = os.path.join(output_dir, f"{name_no_ext}.mxl")
            shutil.move(expected_output, output_mxl_path)
            r.set(f"job:{job_id}:status", "completed")
            r.set(f"job:{job_id}:result", output_mxl_path)
            logger.info("OMR successful.")
        else:
            raise FileNotFoundError("Expected OMR output not found.")
    except Exception as e:
        logger.error(f"oemer failed: {e}")
        r.set(f"job:{job_id}:status", "failed")
        r.set(f"job:{job_id}:error", str(e))

def render_job(ch, method, properties, body):
    job_data = json.loads(body)
    job_id = job_data.get('job_id')
    job_type = job_data.get('type', 'omr') # default to omr if not specified for backward compatibility
    file_path = job_data.get('file_path')
    output_dir = job_data.get('output_dir', '/app/hymn_remaker/output')

    print(f" [x] Received job {job_id} of type {job_type}")

    # Update status to processing
    if job_id:
        r.set(f"job:{job_id}:status", "processing")

    if job_type == 'stem_separation':
        handle_stem_separation(job_id, file_path, output_dir)
    else:
        # Default OMR or legacy render_jobs logic
        handle_omr(job_id, file_path, output_dir)

    print(f" [x] Finished job {job_id}")
    ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    # Wait for rabbitmq to start
    connected = False
    for _ in range(10):
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            connected = True
            break
        except Exception:
            print("Waiting for RabbitMQ...")
            time.sleep(2)

    if not connected:
        print("Failed to connect to RabbitMQ")
        sys.exit(1)

    channel = connection.channel()
    channel.queue_declare(queue='render_jobs', durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='render_jobs', on_message_callback=render_job)

    print(' [*] Waiting for ML jobs. To exit press CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
