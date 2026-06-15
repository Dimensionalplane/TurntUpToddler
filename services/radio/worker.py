import redis
import time
import os
import sys
import json
import logging
from threading import Event

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from hymn_remaker.src.radio_streamer import RadioStreamer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RadioWorker")

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
r = redis.Redis(host=REDIS_HOST, port=6379, db=0)

def main():
    logger.info("Radio Worker starting...")
    pubsub = r.pubsub()
    pubsub.subscribe('radio_commands')

    streamer = None

    while True:
        # Check for commands
        message = pubsub.get_message()
        if message and message['type'] == 'message':
            command_data = json.loads(message['data'])
            cmd = command_data.get('command')

            if cmd == 'START':
                url = command_data.get('stream_url')
                input_dir = command_data.get('input_dir', 'hymn_remaker/output')
                if streamer and streamer.is_streaming:
                    logger.warning("Radio already running.")
                else:
                    logger.info(f"Starting radio to {url}")
                    streamer = RadioStreamer(url, input_dir=input_dir)
                    streamer.start()

            elif cmd == 'STOP':
                if streamer:
                    logger.info("Stopping radio.")
                    streamer.stop()
                    streamer = None

            elif cmd == 'SKIP':
                if streamer and streamer.is_streaming:
                    logger.info("Skipping track.")
                    streamer.skip_track()

        # Update status in Redis
        status = {
            "is_streaming": streamer.is_streaming if streamer else False,
            "current_track": streamer.current_track if streamer else None
        }
        r.set('radio:status', json.dumps(status))

        time.sleep(1)

if __name__ == '__main__':
    main()
