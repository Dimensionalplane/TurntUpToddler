import logging
import os
import pika
import json
import uuid
import time
import redis

logger = logging.getLogger(__name__)

class OMRProcessor:
    def __init__(self):
        self.rabbitmq_host = os.environ.get('RABBITMQ_HOST', 'localhost')
        self.redis_host = os.environ.get('REDIS_HOST', 'localhost')
        try:
            self.r = redis.Redis(host=self.redis_host, port=6379, db=0)
        except Exception as e:
            logger.warning(f"Could not connect to Redis: {e}")
            self.r = None

    def is_available(self):
        return True # Handled by cluster now

    def process(self, image_path, output_dir):
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"OMR input file not found: {image_path}")

        logger.info(f"Dispatching OMR job to ML worker cluster...")
        job_id = str(uuid.uuid4())

        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.rabbitmq_host))
            channel = connection.channel()
            channel.queue_declare(queue='render_jobs', durable=True)

            message = {
                "job_id": job_id,
                "type": "omr",
                "file_path": os.path.abspath(image_path),
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
                logger.info(f"Waiting for ML worker to complete OMR job {job_id}...")

            start_time = time.time()
            timeout_seconds = 1800  # 30 minutes
            while True:
                if time.time() - start_time > timeout_seconds:
                    raise TimeoutError("ML worker job timed out")
                    status = self.r.get(f"job:{job_id}:status")
                    if status:
                        status = status.decode('utf-8')
                        if status == "completed":
                            result = self.r.get(f"job:{job_id}:result")
                            if result:
                                return result.decode('utf-8')
                            break
                        elif status == "failed":
                            err = self.r.get(f"job:{job_id}:error")
                            raise RuntimeError(f"ML Worker failed: {err.decode('utf-8') if err else 'Unknown'}")
                    time.sleep(2)

            # Fallback path if redis doesn't return result
            filename = os.path.basename(image_path)
            name_no_ext = os.path.splitext(filename)[0]
            output_mxl_path = os.path.join(output_dir, f"{name_no_ext}.mxl")
            return output_mxl_path
        except Exception as e:
            logger.error(f"Failed to dispatch OMR to ML cluster: {e}")
            raise RuntimeError(f"OMR failed: {e}")
