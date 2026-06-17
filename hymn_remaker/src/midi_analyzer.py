import mido
import logging
import os

logger = logging.getLogger(__name__)

class MidiAnalyzer:
    @staticmethod
    def analyze_file(midi_path):
        """
        Parses a MIDI file and extracts BPM, Time Signature, and Note Density.

        Returns:
            dict: { "bpm": int, "time_signature": str, "note_density": float }
        """
        if not os.path.exists(midi_path):
            logger.error(f"MIDI file not found for analysis: {midi_path}")
            return {"bpm": 120, "time_signature": "4/4", "note_density": 0.0}

        bpm = 120
        time_signature = "4/4"
        note_count = 0
        total_duration = 0

        try:
            mid = mido.MidiFile(midi_path)
            total_duration = mid.length

            for track in mid.tracks:
                for msg in track:
                    if msg.type == 'set_tempo':
                        bpm = round(mido.tempo2bpm(msg.tempo))
                    if msg.type == 'time_signature':
                        time_signature = f"{msg.numerator}/{msg.denominator}"
                    if msg.type == 'note_on' and msg.velocity > 0:
                        note_count += 1

            note_density = note_count / total_duration if total_duration > 0 else 0
            logger.info(f"Analyzed {os.path.basename(midi_path)}: BPM={bpm}, Density={note_density:.2f}")

            return {
                "bpm": bpm,
                "time_signature": time_signature,
                "note_density": note_density
            }

        except Exception as e:
            logger.warning(f"Failed to analyze MIDI file {midi_path}: {e}")
            return {"bpm": 120, "time_signature": "4/4", "note_density": 0.0}

    @staticmethod
    def suggest_style(midi_path):
        """
        Suggests a STYLE_PRESET based on MIDI analysis.
        """
        analysis = MidiAnalyzer.analyze_file(midi_path)
        bpm = analysis["bpm"]
        density = analysis["note_density"]

        # Heuristics for style selection
        if bpm < 80:
            if density < 2.0:
                return "Ambient / Cinematic"
            return "Lullaby"
        elif bpm < 110:
            return "Lofi Hip Hop"
        elif bpm < 130:
            return "Deep House"
        else:
            if density > 5.0:
                return "Techno"
            return "Synthwave"

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(MidiAnalyzer.analyze_file(sys.argv[1]))
    else:
        print("Usage: python midi_analyzer.py <file.mid>")
