import os
import replicate
import logging
from .utils import retry_request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MusicRemaker:
    def __init__(self, api_token=None):
        """
        Initialize the MusicRemaker with a Replicate API token.

        Args:
            api_token (str): Replicate API token. Defaults to REPLICATE_API_TOKEN env var.
        """
        self.api_token = api_token or os.environ.get("REPLICATE_API_TOKEN")
        if not self.api_token:
            logger.warning("REPLICATE_API_TOKEN not set. MusicRemaker will not function.")

        # Authenticate (though replicate client usually does this automatically from env)
        if self.api_token:
            os.environ["REPLICATE_API_TOKEN"] = self.api_token

    @retry_request(max_retries=3, delay=2, backoff=2)
    def remake(self, audio_path, prompt, duration=30):
        """
        Generate a remake of the input audio using MusicGen via Replicate.

        Args:
            audio_path (str): Path to the input audio file (WAV/MP3).
            prompt (str): Text prompt for the style (e.g. "Deep House, high quality, electronic").
            duration (int): Duration of the output in seconds.

        Returns:
            str: URL of the generated audio.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Input audio file not found: {audio_path}")

        logger.info(f"Remaking {audio_path} with prompt: '{prompt}'...")

        # Using meta/musicgen-melody which is good for conditioning on input melody
        # The model hash might change, so checking replicate's latest
        # This is musicgen-melody
        model = "meta/musicgen:671ac904629c9798ddc38d7747750e2f54e63d179aa2e84786d1a2d6cc7809a6"

        # Replicate expects a file object for input
        with open(audio_path, "rb") as audio_file:
            output = replicate.run(
                model,
                input={
                    "prompt": prompt,
                    "input_audio": audio_file,
                    "duration": duration,
                    "model_version": "melody", # Specific for melody conditioning
                    "normalization_strategy": "peak"
                }
            )

        logger.info(f"Generation complete. Output: {output}")
        return output

if __name__ == "__main__":
    if os.environ.get("REPLICATE_API_TOKEN"):
        remaker = MusicRemaker()
        import sys
        if len(sys.argv) > 2:
            print(remaker.remake(sys.argv[1], sys.argv[2]))
        else:
            print("Usage: python remaker.py <input.wav> <prompt>")
    else:
        print("REPLICATE_API_TOKEN not set. Skipping real test.")
