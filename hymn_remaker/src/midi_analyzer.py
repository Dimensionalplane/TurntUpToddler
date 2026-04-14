import mido
import logging
import os

logger = logging.getLogger(__name__)

class MidiAnalyzer:
    @staticmethod
    def analyze_file(midi_path):
        """
        Parses a MIDI file and attempts to extract its initial Tempo (BPM) and Time Signature.

        Args:
            midi_path (str): Path to the .mid file.

        Returns:
            dict: { "bpm": int or None, "time_signature": str or None }
        """
        if not os.path.exists(midi_path):
            logger.error(f"MIDI file not found for analysis: {midi_path}")
            return {"bpm": None, "time_signature": None}

        bpm = None
        time_signature = None

        try:
            mid = mido.MidiFile(midi_path)

            # Scan through all tracks and messages looking for tempo and time_signature meta messages
            for track in mid.tracks:
                for msg in track:
                    if msg.type == 'set_tempo' and bpm is None:
                        # Convert tempo (microseconds per beat) to BPM
                        bpm = round(mido.tempo2bpm(msg.tempo))

                    if msg.type == 'time_signature' and time_signature is None:
                        time_signature = f"{msg.numerator}/{msg.denominator}"

                    # Break early if we found both to save processing time
                    if bpm is not None and time_signature is not None:
                        break
                if bpm is not None and time_signature is not None:
                    break

            logger.info(f"Analyzed {os.path.basename(midi_path)}: BPM={bpm}, Time Signature={time_signature}")

        except Exception as e:
            logger.warning(f"Failed to analyze MIDI file {midi_path}: {e}")

        # Return found values, or None if the MIDI file didn't explicitly set them
        return {
            "bpm": bpm,
            "time_signature": time_signature
        }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(MidiAnalyzer.analyze_file(sys.argv[1]))
    else:
        print("Usage: python midi_analyzer.py <file.mid>")
