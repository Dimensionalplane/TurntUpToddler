"""tut_render.py — Step 2: Render MIDI to sine-wave WAV at multiple speeds.

Usage:
    python tut_render.py twinkle_twinkle              # render at all speeds
    python tut_render.py twinkle_twinkle --speed 1.0  # render at one speed
    python tut_render.py --all                         # render all songs
"""

import os
import sys
import struct
import math
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tut_pipeline.tut_config import SONGS, SPEEDS, wav_path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("tut_render")

SAMPLE_RATE = 44100

# ── Sine-wave MIDI note data ──
# pitch: (midi_note, duration_ticks)
SONG_DATA = {
    "twinkle_twinkle": [
        (60, 1),
        (60, 1),
        (67, 1),
        (67, 1),
        (69, 1),
        (69, 1),
        (67, 2),
        (65, 1),
        (65, 1),
        (64, 1),
        (64, 1),
        (62, 1),
        (62, 1),
        (60, 2),
        (67, 1),
        (67, 1),
        (65, 1),
        (65, 1),
        (64, 1),
        (64, 1),
        (62, 2),
        (67, 1),
        (67, 1),
        (65, 1),
        (65, 1),
        (64, 1),
        (64, 1),
        (62, 2),
        (60, 1),
        (60, 1),
        (67, 1),
        (67, 1),
        (69, 1),
        (69, 1),
        (67, 2),
        (65, 1),
        (65, 1),
        (64, 1),
        (64, 1),
        (62, 1),
        (62, 1),
        (60, 2),
    ],
}


def midi_to_freq(note):
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


def render_song(song, speed=1.0):
    """Render a single song at a given speed multiplier. Returns output path."""
    if song not in SONG_DATA:
        logger.warning(f"No note data for '{song}'")
        return None

    out = wav_path(song, speed)
    os.makedirs(os.path.dirname(out), exist_ok=True)

    notes = SONG_DATA[song]
    tick_duration = 0.3 / speed  # seconds per tick, adjusted
    samples_per_tick = int(SAMPLE_RATE * tick_duration)
    total_samples = sum(dur * samples_per_tick for _, dur in notes)
    total_sec = total_samples / SAMPLE_RATE

    data = bytearray()
    for note, dur in notes:
        freq = midi_to_freq(note)
        n_samples = dur * samples_per_tick
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            val = int(16000.0 * math.sin(2.0 * math.pi * freq * t))
            val = max(-32767, min(32767, val))
            data.extend(struct.pack("<hh", val, val))

    # Write WAV header
    with open(out, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + len(data)))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, 2, SAMPLE_RATE, SAMPLE_RATE * 4, 4, 16))
        f.write(b"data")
        f.write(struct.pack("<I", len(data)))
        f.write(data)

    size_kb = os.path.getsize(out) // 1024
    logger.info(
        f"  {song} @ {speed}x → {os.path.basename(out)} ({size_kb}KB, {total_sec:.1f}s)"
    )
    return out


def main():
    parser = argparse.ArgumentParser(
        description="TUT Render: MIDI → WAV at multiple speeds"
    )
    parser.add_argument("song", nargs="?", help="Song name (e.g. twinkle_twinkle)")
    parser.add_argument("--speed", type=float, help="Single speed to render")
    parser.add_argument("--all", action="store_true", help="Render all songs")
    args = parser.parse_args()

    speeds = [args.speed] if args.speed else SPEEDS
    songs = SONGS if args.all else [args.song] if args.song else list(SONG_DATA.keys())

    rendered = []
    for song in songs:
        for speed in speeds:
            out = wav_path(song, speed)
            if os.path.exists(out):
                logger.info(f"SKIP: {os.path.basename(out)}")
                continue
            path = render_song(song, speed)
            if path:
                rendered.append(path)

    logger.info(f"Done: {len(rendered)} rendered")
    return rendered


if __name__ == "__main__":
    main()
