import os
import logging
import uuid
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment
import numpy as np
import pyrubberband as pyrb
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

    def _pitch_shift(self, sound, semitones):
        """
        High fidelity pitch-shift using pyrubberband to prevent altering audio speed.
        Converts the pydub AudioSegment to numpy, shifts, and converts back.
        """
        samples = np.array(sound.get_array_of_samples())
        if sound.channels == 2:
            samples = samples.reshape((-1, 2))

        # Determine the maximum value for normalization based on sample width
        max_val = 1 << (8 * sound.sample_width - 1)

        # PyRubberband expects float32 arrays
        samples = samples.astype(np.float32) / max_val

        shifted_samples = pyrb.pitch_shift(samples, sound.frame_rate, semitones)

        # Clip to prevent audio wrap-around distortion and cast back
        shifted_samples = np.clip(shifted_samples, -1.0, 1.0)

        # Derive numpy dtype from pydub sample_width (pydub has no .array_type)
        _SAMPLE_WIDTH_TO_DTYPE = {1: np.int8, 2: np.int16, 3: np.int32, 4: np.int32}
        dtype = _SAMPLE_WIDTH_TO_DTYPE.get(sound.sample_width, np.int16)
        shifted_samples = (shifted_samples * max_val).astype(dtype)

        shifted_sound = sound._spawn(shifted_samples.tobytes())
        return shifted_sound

    @retry_request(max_retries=3, delay=2, backoff=2)
    def generate_vocals(self, lyrics, output_path, voice_id="21m00Tcm4TlvDq8ikWAM", model="eleven_multilingual_v2", **kwargs):
        """
        Generate a single synchronized vocal track from a list of lyrics and timestamps.

        Args:
            lyrics (list): List of dicts with 'text', 'start', and 'end' keys (seconds).
            output_path (str): Path to save the combined vocal track.
            voice_id (str): ID of the voice to use (default is "Rachel").
            model (str): ElevenLabs model to use.

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

        # Parse voice_ids (can be a comma-separated string)
        voice_ids = [vid.strip() for vid in voice_id.split(',')]
        primary_voice = voice_ids[0]
        harmony_voices = voice_ids[1:] if len(voice_ids) > 1 else []

        for i, line in enumerate(lyrics):
            text = line.get('text', '').strip()
            if not text:
                continue

            start_ms = int(float(line.get('start', i * 5)) * 1000)
            logger.info(f"Generating primary TTS for line {i+1}: '{text}' at {start_ms}ms using {primary_voice}")

            # Generate the audio clip for primary voice
            audio_generator = self.client.generate(
                text=text,
                voice=primary_voice,
                model=model
            )
            audio_data = b"".join(audio_generator)

            temp_filename = f"temp_tts_primary_{uuid.uuid4().hex}.mp3"
            try:
                with open(temp_filename, "wb") as f:
                    f.write(audio_data)
                line_audio = AudioSegment.from_file(temp_filename)

                # Create harmonies if secondary voices are provided
                if harmony_voices:
                    # We will create a perfect 5th (+7 semitones) or a major 3rd (+4)
                    semitone_shifts = [4, 7, -5, -12] # Up 3rd, Up 5th, Down 4th, Down Octave

                    for v_idx, h_voice in enumerate(harmony_voices):
                        logger.info(f"Generating harmony TTS for line {i+1} using {h_voice}")
                        h_generator = self.client.generate(text=text, voice=h_voice, model=model)
                        h_data = b"".join(h_generator)

                        h_temp = f"temp_tts_harm_{uuid.uuid4().hex}.mp3"
                        with open(h_temp, "wb") as hf:
                            hf.write(h_data)

                        h_audio = AudioSegment.from_file(h_temp)

                        # Apply pitch shift to create the chord
                        shift_amount = semitone_shifts[v_idx % len(semitone_shifts)]
                        h_audio = self._pitch_shift(h_audio, shift_amount)

                        # Lower the volume of harmonies so they don't overpower the melody
                        h_audio = h_audio - 6

                        # Pan harmonies slightly left and right
                        pan_amount = -0.5 if v_idx % 2 == 0 else 0.5
                        h_audio = h_audio.pan(pan_amount)

                        # Mix the harmony directly into the primary line audio block
                        line_audio = line_audio.overlay(h_audio)

                        if os.path.exists(h_temp):
                            os.remove(h_temp)

                # Overlay the final mixed (or single) line onto the master timeline
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
