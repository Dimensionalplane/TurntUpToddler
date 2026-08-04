"""Quick render missing songs as WAVs."""
import os
import sys
import subprocess
import numpy as np
from scipy.io import wavfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT = os.path.join(BASE, "input")
OUTPUT = os.path.join(BASE, "rendered_wav")
os.makedirs(OUTPUT, exist_ok=True)

# MIDI note numbers (C4 = 60)
def note(name):
    notes = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    base = notes[name[0]]
    octave = int(name[1]) if len(name) > 1 else 4
    return base + (octave + 1) * 12

# Row Row Row Your Boat
# C C C D E | E D E F G | C C C G G G E E E C C C | G F E D C
row_row = [
    ("C4", 0.25), ("C4", 0.25), ("C4", 0.25), ("D4", 0.25), ("E4", 0.5),
    ("E4", 0.25), ("D4", 0.25), ("E4", 0.25), ("F4", 0.25), ("G4", 1.0),
    ("C5", 0.125), ("C5", 0.125), ("C5", 0.125), ("G4", 0.125),
    ("G4", 0.125), ("G4", 0.125), ("E4", 0.125), ("E4", 0.125),
    ("E4", 0.125), ("C4", 0.125), ("C4", 0.125), ("C4", 0.125),
    ("G4", 0.25), ("F4", 0.25), ("E4", 0.25), ("D4", 0.25), ("C4", 1.0),
]

# Itsy Bitsy Spider
# G C C C D E E | E D C D E C | E E F G | G F E F G E | C C D E E D C D E C
itsy_bitsy = [
    ("G4", 0.5), ("C5", 0.25), ("C5", 0.25), ("C5", 0.25),
    ("D5", 0.25), ("E5", 0.5), ("E5", 0.5),
    ("E5", 0.25), ("D5", 0.25), ("C5", 0.25),
    ("D5", 0.25), ("E5", 0.5), ("C5", 1.0),
    ("E5", 0.5), ("E5", 0.25), ("F5", 0.25), ("G5", 0.5),
    ("G5", 0.25), ("F5", 0.25), ("E5", 0.25),
    ("F5", 0.25), ("G5", 0.5), ("E5", 1.0),
    ("C5", 0.5), ("C5", 0.25), ("D5", 0.25), ("E5", 0.5),
    ("E5", 0.25), ("D5", 0.25), ("C5", 0.25),
    ("D5", 0.25), ("E5", 0.5), ("C5", 1.0),
]

SPEEDS = [0.5, 1.0, 2.5, 5.0]
SR = 44100

def render_melody(melody, out_base, speed=1.0):
    """Render a melody as WAV using sine waves."""
    total_dur = sum(d for _, d in melody) / speed
    total_samples = int(total_dur * SR) + SR // 10
    audio = np.zeros(total_samples, dtype=np.float64)

    pos = 0
    for n, dur in melody:
        freq = 440.0 * (2.0 ** ((note(n) - 69) / 12.0))
        dur_samples = int(dur / speed * SR)
        t = np.arange(dur_samples) / SR
        env = np.exp(-t * 3.0)  # gentle decay
        amp = 0.3
        audio[pos:pos + dur_samples] += amp * np.sin(2.0 * np.pi * freq * t) * env
        pos += dur_samples

    # Normalize
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.9

    # Pitch/tempo adjust for speed
    pitch_factors = {
        0.5: {"rate": 0.8909, "tempo": 1.1225},
        1.0: {"rate": 1.0595, "tempo": 0.9439},
        2.5: {"rate": 0.9439, "tempo": 1.0595},
        5.0: {"rate": 1.1225, "tempo": 0.8909},
    }
    pf = pitch_factors.get(speed, {"rate": 1.0595, "tempo": 0.9439})

    tmp = out_base + "_tmp.wav"
    wavfile.write(tmp, SR, (audio * 32767).astype(np.int16))

    speed_str = str(speed).replace(".", "_")
    out_path = f"{out_base}_speed_{speed_str}.wav"

    cmd = [
        "ffmpeg", "-y", "-i", tmp,
        "-af", f"asetrate=44100*{pf['rate']},atempo={pf['tempo']},aresample=44100,"
               f"lowpass=f=3500,highpass=f=120,adelay=400|400",
        out_path,
    ]
    subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                   creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
    if os.path.exists(tmp):
        os.unlink(tmp)
    print(f"  {os.path.basename(out_path)} ({os.path.getsize(out_path)//1024}KB)")
    return out_path


def main():
    for song_name, melody in [("row_row_boat", row_row), ("itsy_bitsy", itsy_bitsy)]:
        out_base = os.path.join(OUTPUT, song_name)
        for speed in SPEEDS:
            if not os.path.exists(f"{out_base}_speed_{str(speed).replace('.', '_')}.wav"):
                print(f"Rendering {song_name} @ {speed}x...")
                render_melody(melody, out_base, speed)
            else:
                print(f"SKIP {song_name} @ {speed}x (exists)")


if __name__ == "__main__":
    main()
