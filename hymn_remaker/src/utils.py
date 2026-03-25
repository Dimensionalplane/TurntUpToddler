import logging
import os
import time
from functools import wraps
from pydub import AudioSegment

logger = logging.getLogger(__name__)

def retry_request(max_retries=3, delay=2, backoff=2, exceptions=(Exception,)):
    """
    A decorator that retries a function if it raises an exception.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    logger.warning(f"Attempt {retries + 1} failed: {e}")
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Max retries reached for {func.__name__}")
                        raise e
                    logger.info(f"Retrying in {current_delay} seconds...")
                    time.sleep(current_delay)
                    current_delay *= backoff
            return func(*args, **kwargs)
        return wrapper
    return decorator

def mix_audio(instrumental_path, vocal_path, output_path, vocal_vol_boost=2, instrumental_vol_duck=-3):
    """
    Mixes a vocal track onto an instrumental track, applying slight volume ducking to the instrumental.

    Args:
        instrumental_path (str): Path to the base instrumental audio.
        vocal_path (str): Path to the vocal audio track.
        output_path (str): Path to save the mixed audio.
        vocal_vol_boost (int): dB boost to apply to the vocals before mixing.
        instrumental_vol_duck (int): dB reduction to apply to the instrumental before mixing.
    """
    logger.info(f"Mixing vocals ({vocal_path}) onto instrumental ({instrumental_path})...")

    try:
        instrumental = AudioSegment.from_file(instrumental_path)
        vocals = AudioSegment.from_file(vocal_path)

        # Adjust volumes
        instrumental = instrumental + instrumental_vol_duck
        vocals = vocals + vocal_vol_boost

        # Mix them (overlay)
        mixed_audio = instrumental.overlay(vocals, position=0)

        # Export
        mixed_audio.export(output_path, format="wav")
        logger.info(f"Mixed audio saved to: {output_path}")

    except Exception as e:
        logger.error(f"Failed to mix audio: {e}")
        raise e

def process_audio(input_path, output_path, normalize=True, fade_in_ms=0, fade_out_ms=0, vocal_track_path=None):
    """
    Apply advanced audio processing such as normalization, fading, and optional vocal mixing using pydub.

    Args:
        input_path (str): Path to input audio.
        output_path (str): Path to output audio.
        normalize (bool): Whether to normalize the audio volume.
        fade_in_ms (int): Fade-in duration in milliseconds.
        fade_out_ms (int): Fade-out duration in milliseconds.
        vocal_track_path (str): Optional path to a vocal track to mix in.
    """
    logger.info(f"Processing audio: {input_path}")

    try:
        # Load audio (pydub supports standard formats, automatically detecting via extension or falling back to ffmpeg)
        audio = AudioSegment.from_file(input_path)

        if vocal_track_path and os.path.exists(vocal_track_path):
            logger.info(f"Mixing vocal track from: {vocal_track_path}")
            vocals = AudioSegment.from_file(vocal_track_path)
            # Slight duck on instrumental, boost on vocals
            audio = audio - 3
            vocals = vocals + 2
            audio = audio.overlay(vocals, position=0)

        if normalize:
            logger.info("Normalizing audio volume...")
            # Pydub normalization: brings max amplitude to 0dBFS
            # We can use pydub.effects.normalize
            from pydub.effects import normalize as pydub_normalize
            audio = pydub_normalize(audio)

        if fade_in_ms > 0:
            logger.info(f"Applying fade-in of {fade_in_ms}ms...")
            audio = audio.fade_in(fade_in_ms)

        if fade_out_ms > 0:
            logger.info(f"Applying fade-out of {fade_out_ms}ms...")
            audio = audio.fade_out(fade_out_ms)

        # Export processed audio
        audio.export(output_path, format="wav")
        logger.info(f"Processed audio saved to: {output_path}")

    except Exception as e:
        logger.error(f"Failed to process audio with pydub: {e}")
        raise e
