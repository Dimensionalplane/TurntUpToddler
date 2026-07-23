import logging
import os
import pika
import json
import uuid
import time
import redis

logger = logging.getLogger(__name__)

class StemSeparator:
    def __init__(self, model="htdemucs"):
        self.model = model
        self.rabbitmq_host = os.environ.get('RABBITMQ_HOST', 'localhost')
        self.redis_host = os.environ.get('REDIS_HOST', 'localhost')
        try:
            self.r = redis.Redis(host=self.redis_host, port=6379, db=0)
        except Exception as e:
            logger.warning(f"Could not connect to Redis: {e}")
            self.r = None

    def separate(self, audio_path, output_dir):
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file to separate not found: {audio_path}")

        logger.info(f"Dispatching Demucs stem separation job to ML worker cluster...")
        job_id = str(uuid.uuid4())

        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.rabbitmq_host))
            channel = connection.channel()
            channel.queue_declare(queue='render_jobs', durable=True)

            message = {
                "job_id": job_id,
                "type": "stem_separation",
                "file_path": os.path.abspath(audio_path),
                "output_dir": os.path.abspath(output_dir)
            }

            channel.basic_publish(
                exchange='',
                routing_key='render_jobs',
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            connection.close()

            # Poll Redis for completion
            if self.r:
                self.r.set(f"job:{job_id}:status", "queued")
                logger.info(f"Waiting for ML worker to complete job {job_id}...")

            start_time = time.time()
            timeout_seconds = 1800  # 30 minutes
            while True:
                if time.time() - start_time > timeout_seconds:
                    raise TimeoutError("ML worker job timed out")
                    status = self.r.get(f"job:{job_id}:status")
                    if status:
                        status = status.decode('utf-8')
                        if status == "completed":
                            break
                        elif status == "failed":
                            err = self.r.get(f"job:{job_id}:error")
                            raise RuntimeError(f"ML Worker failed: {err.decode('utf-8') if err else 'Unknown'}")
                    time.sleep(2)
            else:
                logger.warning("No Redis connection, skipping blocking wait (async fallback).")

            filename = os.path.basename(audio_path)
            name_no_ext = os.path.splitext(filename)[0]
            stem_dir = os.path.join(output_dir, self.model, name_no_ext)

            stems = {}
            for stem_name in ["drums", "bass", "other", "vocals"]:
                expected_path = os.path.join(stem_dir, f"{stem_name}.wav")
                stems[stem_name] = expected_path

            logger.info("Stem separation cluster task complete.")
            return stems
        except Exception as e:
            logger.error(f"Failed to dispatch to ML cluster: {e}")
            raise RuntimeError(f"Stem separation failed: {e}")
