import os
import sys
import logging
import soundfile as sf
import numpy as np
import mido
import math
import time

from hymn_remaker import settings

# Ensure the root directory is in sys.path so we can import hymn_player_ext
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    import hymn_player_ext
    NATIVE_ENGINE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Native HymnPlayer engine not found. Falling back to midi2audio. ({e})")
    NATIVE_ENGINE_AVAILABLE = False

from midi2audio import FluidSynth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MidiRenderer:
    def __init__(self, soundfont_path=None):
        """
        Initialize the MidiRenderer with a soundfont.

        Args:
            soundfont_path (str): Path to the .sf2 soundfont file.
                Defaults to searching SOUNDFONT_PATH env var, then
                settings.DEFAULT_SOUNDFONT_PATHS, then bundled soundfonts.
        """
        if soundfont_path:
            self.soundfont_path = soundfont_path
        else:
            # Check SOUNDFONT_PATH env var first
            env_path = os.environ.get('SOUNDFONT_PATH')
            if env_path and os.path.exists(env_path):
                self.soundfont_path = env_path
            else:
                # Try to find a default soundfont from settings
                for path in settings.DEFAULT_SOUNDFONT_PATHS:
                    if os.path.exists(path):
                        self.soundfont_path = path
                        break
                else:
                    raise FileNotFoundError(
                        "No default soundfont found. Please provide a path to a valid .sf2 file. "
                        "Download one to hymn_remaker/soundfonts/ or set SOUNDFONT_PATH env var."
                    )

        logger.info(f"Using SoundFont: {self.soundfont_path}")
        if not NATIVE_ENGINE_AVAILABLE:
            self.fs = FluidSynth(self.soundfont_path)

    def _get_midi_duration(self, midi_path):
        try:
            mid = mido.MidiFile(midi_path)
            return mid.length
        except Exception as e:
            logger.warning(f"Failed to calculate MIDI duration: {e}. Defaulting to 120 seconds.")
            return 120.0

    def get_midi_bpm(self, midi_path):
        """
        Extract the initial BPM from a MIDI file.
        """
        try:
            mid = mido.MidiFile(midi_path)
            for track in mid.tracks:
                for msg in track:
                    if msg.type == 'set_tempo':
                        return mido.tempo2bpm(msg.tempo)
            return 120.0  # Default if no tempo found
        except Exception as e:
            logger.warning(f"Failed to extract BPM from MIDI: {e}. Defaulting to 120 BPM.")
            return 120.0

    def render(self, midi_path, output_path):
        """
        Render a MIDI file to audio (WAV/MP3/FLAC depending on extension).

        Args:
            midi_path (str): Path to the input MIDI file.
            output_path (str): Path to the output audio file.
        """
        if not os.path.exists(midi_path):
            raise FileNotFoundError(f"MIDI file not found: {midi_path}")

        logger.info(f"Rendering {midi_path} to {output_path}...")

        try:
            if NATIVE_ENGINE_AVAILABLE:
                logger.info("Using Native C++ Engine for rendering.")
                # Instantiate player locally per thread to ensure thread-safety
                player = hymn_player_ext.HymnPlayer(self.soundfont_path)

                # Load the MIDI file
                success = player.load(midi_path)
                if not success:
                    raise RuntimeError("Failed to load MIDI file into native engine.")

                # Calculate duration to know how many frames to render
                duration_sec = self._get_midi_duration(midi_path)
                sample_rate = settings.SAMPLE_RATE
                total_frames = math.ceil((duration_sec + settings.REVERB_TAIL_SECONDS) * sample_rate)

                player.play()

                # Render in chunks
                chunk_size = settings.SAMPLE_RATE  # 1 second chunks
                frames_rendered = 0
                all_audio = []

                while frames_rendered < total_frames and player.is_playing():
                    audio_chunk = player.render_audio(chunk_size)
                    all_audio.append(audio_chunk)
                    frames_rendered += chunk_size

                player.stop()

                if not all_audio:
                    raise RuntimeError("Native engine rendered zero audio frames.")

                # Concatenate all chunks and reshape
                # audio_chunk is a 1D interleaved array of shape (N*2,)
                final_audio = np.concatenate(all_audio)

                # Reshape from interleaved 1D to (Frames, Channels)
                final_audio = final_audio.reshape(-1, 2)

                # sf.write expects float32 in range [-1.0, 1.0] by default,
                # but depending on FluidSynth's output scale we might need to normalize.
                # Usually it's roughly in standard bounds but can clip.
                max_val = np.max(np.abs(final_audio))
                if max_val > 1.0:
                    final_audio = final_audio / max_val

                sf.write(output_path, final_audio, sample_rate)
                logger.info("Native rendering complete.")

            else:
                logger.info("Using fallback midi2audio for rendering.")
                self.fs.midi_to_audio(midi_path, output_path)
                logger.info("Fallback rendering complete.")

        except Exception as e:
            logger.error(f"Failed to render MIDI: {e}")
            raise


if __name__ == "__main__":
    # Test execution
    import sys
    if len(sys.argv) > 2:
        renderer = MidiRenderer()
        renderer.render(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python midi_renderer.py <input.mid> <output.wav>")
