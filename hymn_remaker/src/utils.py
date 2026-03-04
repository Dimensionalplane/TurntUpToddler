import logging
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

def process_audio(input_path, output_path, normalize=True, fade_in_ms=0, fade_out_ms=0):
    """
    Apply advanced audio processing such as normalization and fading using pydub.

    Args:
        input_path (str): Path to input audio.
        output_path (str): Path to output audio.
        normalize (bool): Whether to normalize the audio volume.
        fade_in_ms (int): Fade-in duration in milliseconds.
        fade_out_ms (int): Fade-out duration in milliseconds.
    """
    logger.info(f"Processing audio: {input_path}")

    try:
        # Load audio (pydub supports standard formats, automatically detecting via extension or falling back to ffmpeg)
        audio = AudioSegment.from_file(input_path)

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
