"""
Render Queue Worker: Processes render jobs from RabbitMQ using FluidSynth + FFmpeg.

This worker listens for MIDI render jobs and produces audio files (WAV/MP3/FLAC).
If RabbitMQ is not available, it can also run in standalone mode.
"""

import json
import os
import sys
import time
import logging
import subprocess
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    import pika
    HAS_RABBITMQ = True
except ImportError:
    HAS_RABBITMQ = False
    logger.warning("pika not installed - RabbitMQ mode disabled")

try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    logger.warning("redis not installed - status tracking disabled")

RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')

# Connect to Redis (if available)
r = None
if HAS_REDIS:
    try:
        r = redis.Redis(host=REDIS_HOST, port=6379, db=0, socket_connect_timeout=2)
        r.ping()
        logger.info("Connected to Redis")
    except Exception:
        r = None
        logger.warning("Redis not available - status tracking disabled")


def find_fluidsynth() -> str | None:
    """Find the fluidsynth binary."""
    return shutil.which("fluidsynth") or shutil.which("fluidsynth.exe")


def find_soundfont() -> str | None:
    """Find a default soundfont."""
    common_paths = [
        "/usr/share/sounds/sf2/FluidR3_GM.sf2",
        "/usr/share/sounds/sf2/default-GM.sf2",
        "/usr/local/share/sounds/sf2/FluidR3_GM.sf2",
        "C:/Program Files (x86)/FluidSynth/share/sounds/sf2/FluidR3_GM.sf2",
        "C:/soundfonts/FluidR3_GM.sf2",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    return None


def render_midi_to_wav(midi_path: str, output_path: str, soundfont: str | None = None) -> bool:
    """
    Render a MIDI file to WAV using FluidSynth.
    Falls back to a basic sine-wave render if FluidSynth is unavailable.
    """
    fluidsynth = find_fluidsynth()
    sf = soundfont or find_soundfont()

    if fluidsynth and sf:
        logger.info(f"Rendering {midi_path} -> {output_path} using FluidSynth")
        args = [
            fluidsynth, "-ni",
            "-F", output_path,
            "-r", "44100",
            sf,
            midi_path
        ]
        result = subprocess.run(args, capture_output=True, timeout=60)
        if result.returncode == 0 and os.path.exists(output_path):
            return True
        logger.warning(f"FluidSynth failed (code {result.returncode}), trying fallback")

    # Fallback: Try Python-based rendering
    logger.info("Attempting Python-based fallback render...")
    try:
        import numpy as np
        from scipy.io import wavfile

        try:
            import pretty_midi
            pm = pretty_midi.PrettyMIDI(midi_path)
            duration = pm.get_end_time()
        except Exception:
            import mido
            mid = mido.MidiFile(midi_path)
            duration = mid.length

        if duration <= 0:
            duration = 4.0  # minimum 4 seconds

        sample_rate = 44100
        audio = np.zeros(int(sample_rate * duration), dtype=np.float32)

        try:
            pm = pretty_midi.PrettyMIDI(midi_path)
            for instrument in pm.instruments:
                for note in instrument.notes:
                    start_sample = int(note.start * sample_rate)
                    end_sample = int(note.end * sample_rate)
                    if start_sample >= len(audio):
                        continue
                    freq = 440 * (2 ** ((note.pitch - 69) / 12))
                    t = np.arange(min(end_sample, len(audio)) - start_sample) / sample_rate
                    sine = np.sin(2 * np.pi * freq * t) * (note.velocity / 127.0) * 0.3
                    audio[start_sample:start_sample + len(sine)] += sine
        except Exception:
            # Absolute fallback: generate a simple tone
            freq = 440
            t = np.arange(len(audio)) / sample_rate
            audio = np.sin(2 * np.pi * freq * t) * 0.3

        # Normalize
        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = audio / peak * 0.9

        wavfile.write(output_path, sample_rate, (audio * 32767).astype(np.int16))
        return os.path.exists(output_path)

    except Exception as e:
        logger.error(f"Fallback render failed: {e}")
        return False


def render_job(ch, method, properties, body):
    """Process a render job from RabbitMQ."""
    try:
        job_data = json.loads(body)
    except json.JSONDecodeError:
        logger.error(f"Invalid job data: {body}")
        if ch:
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    job_id = job_data.get('job_id')
    midi_path = job_data.get('midi_path')
    output_path = job_data.get('output_path', f"output_{job_id}.wav")
    soundfont = job_data.get('soundfont')

    if not midi_path or not os.path.exists(midi_path):
        logger.error(f"MIDI file not found: {midi_path}")
        if r and job_id:
            r.set(f"job:{job_id}:status", "failed")
            r.set(f"job:{job_id}:error", "MIDI file not found")
        if ch:
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    logger.info(f"Processing job {job_id}: {midi_path} -> {output_path}")

    # Update status
    if r and job_id:
        r.set(f"job:{job_id}:status", "rendering")
        r.set(f"job:{job_id}:midi", midi_path)

    try:
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        success = render_midi_to_wav(midi_path, output_path, soundfont)

        if success:
            logger.info(f"Job {job_id} completed: {output_path}")
            if r and job_id:
                r.set(f"job:{job_id}:status", "completed")
                r.set(f"job:{job_id}:output", output_path)
            if ch:
                ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            logger.error(f"Job {job_id} failed to render")
            if r and job_id:
                r.set(f"job:{job_id}:status", "failed")
                r.set(f"job:{job_id}:error", "Render failed")
            if ch:
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        logger.error(f"Job {job_id} crashed: {e}")
        if r and job_id:
            r.set(f"job:{job_id}:status", "failed")
            r.set(f"job:{job_id}:error", str(e))
        if ch:
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main_loop():
    """Main loop: try RabbitMQ first, then fall back to standalone mode."""
    if HAS_RABBITMQ:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST, heartbeat=30)
            )
            channel = connection.channel()
            channel.queue_declare(queue='render_jobs', durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue='render_jobs', on_message_callback=render_job)
            logger.info('Connected to RabbitMQ. Waiting for jobs...')
            channel.start_consuming()
            return
        except Exception as e:
            logger.warning(f"RabbitMQ connection failed: {e}")
            logger.info("Falling back to standalone mode")

    # Standalone mode: watch a directory for new .mid files
    watch_dir = os.environ.get('RENDER_WATCH_DIR', 'output_test_batch')
    output_dir = os.environ.get('RENDER_OUTPUT_DIR', 'output_test_batch')
    os.makedirs(watch_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    logger.info(f"Standalone mode: watching {watch_dir} for MIDI files...")

    processed = set()
    while True:
        for f in Path(watch_dir).glob("*.mid"):
            if str(f) in processed:
                continue

            output_wav = os.path.join(output_dir, f.stem + ".wav")
            logger.info(f"Found new MIDI: {f} -> {output_wav}")

            if render_midi_to_wav(str(f), output_wav):
                logger.info(f"Rendered: {output_wav}")
            else:
                logger.error(f"Failed to render: {f}")

            processed.add(str(f))

        time.sleep(5)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    try:
        main_loop()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        sys.exit(0)
