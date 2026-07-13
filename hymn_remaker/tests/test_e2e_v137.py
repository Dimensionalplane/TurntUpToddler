import os
import subprocess
import pytest
import shutil

@pytest.fixture
def clean_output():
    out_dir = "demo_output_e2e"
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    yield out_dir
    # Keep for inspection if needed, or cleanup
    # shutil.rmtree(out_dir)

def test_e2e_pipeline_dry_run(clean_output):
    """
    Simulates a full pipeline run with Sonic Vacuum and Quality Gates.
    We use a very short MIDI to keep tests fast.
    """
    midi_path = "test_input/short_hymn.mid"
    if not os.path.exists(midi_path):
        # Create a dummy midi if missing
        import mido
        mid = mido.MidiFile()
        track = mido.MidiTrack()
        mid.tracks.append(track)
        track.append(mido.Message('note_on', note=64, velocity=64, time=32))
        track.append(mido.Message('note_off', note=64, velocity=64, time=32))
        os.makedirs("test_input", exist_ok=True)
        mid.save(midi_path)

    cmd = [
        "python3", "hymn_remaker/main.py",
        "--input-dir", "test_input",
        "--output-dir", clean_output,
        "--sonic-vacuum",
        "--speed", "2.0",
        "--remake-priority", "local", # Use local to avoid API calls
        "--style", "Deep House, high quality, 122 BPM"
    ]

    # Run with a timeout to prevent hanging in CI
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    # Assertions
    pass

if __name__ == "__main__":
    pytest.main([__file__])
