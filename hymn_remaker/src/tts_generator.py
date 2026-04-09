import os
import logging
import uuid
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment
from .utils import retry_request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TTSGenerator:
    def __init__(self, api_key=None):
        """
        Initialize the TTS Generator with an ElevenLabs API key.

        Args:
            api_key (str): ElevenLabs API key. Defaults to ELEVENLABS_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        if not self.api_key:
            logger.warning("ELEVENLABS_API_KEY not set. TTSGenerator will not function.")

        if self.api_key:
            self.client = ElevenLabs(api_key=self.api_key)

    @retry_request(max_retries=3, delay=2, backoff=2)
    def generate_vocals(self, lyrics, output_path, voice_id="21m00Tcm4TlvDq8ikWAM", model="eleven_multilingual_v2", status_callback=None):
        """
        Generate a single synchronized vocal track from a list of lyrics and timestamps.

        Args:
            lyrics (list): List of dicts with 'text', 'start', and 'end' keys (seconds).
            output_path (str): Path to save the combined vocal track.
            voice_id (str): ID of the voice to use (default is "Rachel").
            model (str): ElevenLabs model to use.
            status_callback (func): Optional callback taking a string and a float to report progress.

        Returns:
            str: Path to the generated audio file.
        """
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY is required to generate vocals.")

        logger.info(f"Generating vocal track for {len(lyrics)} lines...")

        # Create an empty, silent audio segment to hold our combined vocals.
        # We need to find the maximum timestamp to size the track correctly.
        max_time_sec = 0
        if lyrics:
            # Look at the last lyric's end time. Default to 30s if none.
            max_time_sec = max([float(line.get('end', 0)) for line in lyrics] + [30])

        combined_audio = AudioSegment.silent(duration=int(max_time_sec * 1000) + 5000) # add 5s padding

        total_lines = len(lyrics)

        for i, line in enumerate(lyrics):
            text = line.get('text', '').strip()
            if not text:
                continue

            start_ms = int(float(line.get('start', i * 5)) * 1000)

            if status_callback:
                # We scale the progress bar from 70% to 80% dynamically as lines are generated
                # to provide extremely granular visual feedback to the user.
                progress_step = 70 + int(((i + 1) / total_lines) * 10)
                status_callback(f"Synthesizing Vocal Line {i+1}/{total_lines}: '{text}'", progress_step)
            else:
                logger.info(f"Generating TTS for line {i+1}: '{text}' at {start_ms}ms")

            # Generate the audio clip
            audio_generator = self.client.generate(
                text=text,
                voice=voice_id,
                model=model
            )

            # Reconstruct the audio data from the generator
            audio_data = b"".join(audio_generator)

            # Save temporary file because pydub reads files best
            temp_filename = f"temp_tts_{uuid.uuid4().hex}.mp3"
            try:
                with open(temp_filename, "wb") as f:
                    f.write(audio_data)

                line_audio = AudioSegment.from_file(temp_filename)

                # Overlay this line onto the combined track at the correct start time
                combined_audio = combined_audio.overlay(line_audio, position=start_ms)

            finally:
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

        # Export the final combined track
        logger.info(f"Exporting combined vocal track to {output_path}")
        combined_audio.export(output_path, format="wav")
        return output_path

if __name__ == "__main__":
    import sys
    if os.environ.get("ELEVENLABS_API_KEY"):
        generator = TTSGenerator()
        if len(sys.argv) > 1:
            test_lyrics = [
                {"text": "Amazing grace how sweet the sound", "start": 2.0, "end": 5.0},
                {"text": "That saved a wretch like me", "start": 6.0, "end": 9.0}
            ]
            generator.generate_vocals(test_lyrics, sys.argv[1])
            print(f"Test vocals saved to {sys.argv[1]}")
        else:
            print("Usage: python tts_generator.py <output.wav>")
    else:
        print("ELEVENLABS_API_KEY not set. Skipping test.")
