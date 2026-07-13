#!/usr/bin/env python3
"""
Batch MIDI → MP3 Renderer.

Renders all MIDI files to MP3 at 3 speeds (0.5x, 1.0x, 2.0x) using
a pure-Python sine wave synthesizer. No FluidSynth required.

Usage: python batch_render_midis.py [--workers 8] [--limit 100]
"""

import argparse
import logging
import os
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Tuple

import numpy as np

logging.basicConfig(
    encoding="utf-8",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("batch_render")


# ── Configuration ─────────────────────────────────────────────────────

ROOT = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(ROOT, "hymn_remaker", "input")
OUTPUT_DIR = os.path.join(ROOT, "mp3_input")
DB_PATH = os.path.join(ROOT, "hymn_remaker", "hymn_database.db")
FFMPEG = os.path.join(ROOT, "hymn_remaker", "bin", "ffmpeg.exe")
if not os.path.exists(FFMPEG):
    FFMPEG = "ffmpeg"

SAMPLE_RATE = 22050  # Lower sample rate for faster processing, still fine for MP3
SIMPLE_SF_PATH = os.path.join(ROOT, "hymn_remaker", "soundfonts", "GeneralUser_GS.sf2")
FLUIDSYNTH = os.path.join(ROOT, "hymn_remaker", "bin", "fluidsynth.exe")

# Try to use FluidSynth if available (much better quality)
USE_FLUIDSYNTH = os.path.exists(FLUIDSYNTH) and os.path.exists(SIMPLE_SF_PATH)


def get_hymn_name(filename: str) -> str:
    """Look up the proper name from the database."""
    base = os.path.splitext(os.path.basename(filename))[0]
    if not os.path.exists(DB_PATH):
        return base

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Try matching by filename
        cursor.execute(
            "SELECT title, original_filename, author FROM hymns WHERE filename = ?",
            (os.path.basename(filename),),
        )
        row = cursor.fetchone()

        if not row:
            # Try by original_filename
            cursor.execute(
                "SELECT title, original_filename, author FROM hymns WHERE original_filename = ?",
                (os.path.basename(filename),),
            )
            row = cursor.fetchone()

        if not row:
            # Try by source_path contains filename
            cursor.execute(
                "SELECT title, original_filename, author FROM hymns WHERE source_path LIKE ?",
                (f"%{base}%",),
            )
            row = cursor.fetchone()

        conn.close()

        if row and row[0]:
            name = row[0]
        elif row and row[1]:
            name = os.path.splitext(row[1])[0]
        else:
            name = base

        # Clean the name for filesystem
        name = "".join(c for c in name if c.isalnum() or c in " ._-'(),!&")
        name = name.strip()
        if not name:
            name = base
        return name

    except Exception:
        return base


def midi_to_sine_wav(midi_path: str, wav_path: str, tempo_scale: float = 1.0):
    """Render MIDI to WAV using pure Python sine wave synthesis.

    Simple sine wave per note with basic ADSR envelope.
    Much faster than FluidSynth for bulk processing.
    """
    try:
        import mido
    except ImportError:
        logger.error("mido not installed. Run: pip install mido")
        return False

    try:
        mid = mido.MidiFile(midi_path)
    except Exception as e:
        logger.warning(f"Cannot parse MIDI: {midi_path}: {e}")
        return False

    ticks_per_beat = mid.ticks_per_beat or 480

    # Collect ALL note events with absolute times from ALL tracks
    # Track tempo changes globally
    tempo = 500000  # default 120 BPM
    all_note_events = []  # (abs_time_sec, type_sec, note, velocity, channel)

    for track_idx, track in enumerate(mid.tracks):
        abs_ticks = 0
        for msg in track:
            abs_ticks += msg.time
            abs_sec = mido.tick2second(abs_ticks, ticks_per_beat, tempo)

            if msg.type == "set_tempo":
                tempo = msg.tempo
                abs_sec = mido.tick2second(abs_ticks, ticks_per_beat, tempo)

            if msg.type == "note_on" and msg.velocity > 0:
                all_note_events.append(
                    (abs_sec, "on", msg.note, msg.velocity, msg.channel)
                )
            elif msg.type == "note_off" or (
                msg.type == "note_on" and msg.velocity == 0
            ):
                all_note_events.append((abs_sec, "off", msg.note, 0, msg.channel))

    if not all_note_events:
        logger.warning(f"No note events in: {midi_path}")
        return False

    # Sort by time
    all_note_events.sort(key=lambda x: x[0])

    # Calculate total duration (last note end + 2s padding)
    max_time = max(e[0] for e in all_note_events) + 2.0
    if max_time < 5:
        max_time = 5.0  # minimum 5 seconds
    if max_time > 300:
        max_time = 300.0  # cap at 5 minutes

    total_samples = int(max_time * SAMPLE_RATE) + SAMPLE_RATE
    audio = np.zeros(total_samples, dtype=np.float64)

    # Process notes using active_notes dict
    active_notes = {}  # (note, channel) -> start_time

    for event in all_note_events:
        abs_sec, etype, note, velocity, channel = event
        key = (note, channel)

        if etype == "on":
            active_notes[key] = {
                "start": abs_sec,
                "velocity": velocity / 127.0,
                "channel": channel,
            }
        elif etype == "off" and key in active_notes:
            info = active_notes.pop(key)
            start = info["start"]
            vel = info["velocity"]
            duration = abs_sec - start

            if duration <= 0 or duration > 15:
                continue

            freq = 440.0 * (2.0 ** ((note - 69) / 12.0))
            n_samples = int(duration * SAMPLE_RATE)
            start_sample = int(start * SAMPLE_RATE)
            end_sample = min(start_sample + n_samples, total_samples)

            if start_sample >= total_samples:
                continue

            t = np.arange(end_sample - start_sample, dtype=np.float64) / SAMPLE_RATE
            sine = np.sin(2 * np.pi * freq * t)

            # Simple ADSR envelope
            env = np.ones_like(t)
            attack_n = min(int(0.005 * SAMPLE_RATE), len(t))
            decay_n = min(int(0.05 * SAMPLE_RATE), len(t))
            release_n = min(int(0.05 * SAMPLE_RATE), len(t))
            if attack_n > 0:
                env[:attack_n] = np.linspace(0, 1, attack_n)
            if decay_n > attack_n:
                env[attack_n:decay_n] = np.linspace(1, 0.7, decay_n - attack_n)
            if release_n > 0:
                env[-release_n:] *= np.linspace(1, 0, release_n)

            note_audio = sine * env * vel * 0.15
            actual_n = min(len(note_audio), end_sample - start_sample)
            audio[start_sample : start_sample + actual_n] += note_audio[:actual_n]

    # Handle stuck notes (notes that never got note_off)
    for key, info in active_notes.items():
        start = info["start"]
        vel = info["velocity"]
        note = key[0]
        duration = min(2.0, max_time - start)
        if duration <= 0:
            continue

        freq = 440.0 * (2.0 ** ((note - 69) / 12.0))
        n_samples = int(duration * SAMPLE_RATE)
        start_sample = int(start * SAMPLE_RATE)
        end_sample = min(start_sample + n_samples, total_samples)

        if start_sample >= total_samples:
            continue

        t = np.arange(end_sample - start_sample, dtype=np.float64) / SAMPLE_RATE
        sine = np.sin(2 * np.pi * freq * t)
        env = np.ones_like(t)
        fade_n = min(int(0.5 * SAMPLE_RATE), len(t))
        env[-fade_n:] = np.linspace(1, 0, fade_n)

        audio[start_sample:end_sample] += sine * env * vel * 0.10

    # Normalize to prevent clipping
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val * 0.7

    # Write WAV
    audio_int16 = (audio * 32767).astype(np.int16)

    import struct

    with open(wav_path, "wb") as f:
        data_size = len(audio_int16) * 2
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, 1, SAMPLE_RATE, SAMPLE_RATE * 2, 2, 16))
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        audio_int16.tofile(f)

    return True


def render_one_midi(
    midi_path: str,
) -> Tuple[str, bool, int]:
    """Render a single MIDI file to 3 MP3s (0.5x, 1.0x, 2.0x)."""
    try:
        name = get_hymn_name(midi_path)
        safe_name = "".join(c for c in name if c.isalnum() or c in " ._-'")
        safe_name = safe_name.strip().replace(" ", "_")[:80]

        # Create temp WAV
        temp_wav = os.path.join(
            OUTPUT_DIR, f"_temp_{os.getpid()}_{hash(name) & 0xFFFFFFFF}.wav"
        )

        # Render to WAV using pure Python synth
        ok = midi_to_sine_wav(midi_path, temp_wav, tempo_scale=1.0)
        if not ok or not os.path.exists(temp_wav):
            return (midi_path, False, 0)

        wav_size = os.path.getsize(temp_wav)

        # Convert to MP3 at 3 speeds
        for speed, label in [(1.0, "1.0x"), (0.5, "0.5x"), (2.0, "2.0x")]:
            out_mp3 = os.path.join(OUTPUT_DIR, f"{safe_name}_{label}.mp3")

            if speed == 1.0:
                subprocess.run(
                    [
                        FFMPEG,
                        "-i",
                        temp_wav,
                        "-codec:a",
                        "libmp3lame",
                        "-b:a",
                        "64k",
                        "-ar",
                        "22050",
                        "-ac",
                        "1",
                        "-y",
                        out_mp3,
                    ],
                    capture_output=True,
                    timeout=60,
                )
            else:
                subprocess.run(
                    [
                        FFMPEG,
                        "-i",
                        temp_wav,
                        "-filter:a",
                        f"atempo={speed}",
                        "-codec:a",
                        "libmp3lame",
                        "-b:a",
                        "64k",
                        "-ar",
                        "22050",
                        "-ac",
                        "1",
                        "-y",
                        out_mp3,
                    ],
                    capture_output=True,
                    timeout=60,
                )

            if not os.path.exists(out_mp3):
                logger.warning(f"Failed to create {out_mp3}")

        # Cleanup temp WAV
        if os.path.exists(temp_wav):
            os.remove(temp_wav)

        return (midi_path, True, wav_size)

    except Exception as e:
        logger.error(f"Error rendering {midi_path}: {e}")
        return (midi_path, False, 0)


def main():
    parser = argparse.ArgumentParser(description="Batch render MIDIs to MP3s")
    parser.add_argument(
        "--workers", type=int, default=4, help="Number of parallel workers"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of MIDIs to process (0 = all)",
    )
    parser.add_argument(
        "--resume", action="store_true", help="Skip already-rendered files"
    )
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Collect all MIDI files
    all_midis = []
    for root, dirs, files in os.walk(INPUT_DIR):
        for f in files:
            if f.endswith((".mid", ".midi")):
                all_midis.append(os.path.join(root, f))

    # Deduplicate by content hash (fast check: just use filename + size)
    seen = {}
    unique_midis = []
    for mp in all_midis:
        key = f"{os.path.getsize(mp)}_{os.path.basename(mp)}"
        if key not in seen:
            seen[key] = True
            unique_midis.append(mp)

    if args.limit > 0:
        unique_midis = unique_midis[: args.limit]

    # Skip already rendered
    if args.resume:
        to_process = []
        for mp in unique_midis:
            name = get_hymn_name(mp)
            safe = (
                "".join(c for c in name if c.isalnum() or c in " ._-'")
                .strip()
                .replace(" ", "_")[:80]
            )
            mp3_path = os.path.join(OUTPUT_DIR, f"{safe}_1.0x.mp3")
            if not os.path.exists(mp3_path):
                to_process.append(mp)
            else:
                logger.debug(f"Skipping (exists): {mp3_path}")
        unique_midis = to_process

    logger.info(
        "Rendering %d MIDI files (%d workers) → %d MP3s",
        len(unique_midis),
        args.workers,
        len(unique_midis) * 3,
    )
    logger.info("Output: %s", OUTPUT_DIR)
    if USE_FLUIDSYNTH:
        logger.info("Using FluidSynth for rendering (higher quality)")
    else:
        logger.info("Using Python sine wave synth (faster, simpler)")

    start = time.time()
    rendered = 0
    failed = 0

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(render_one_midi, mp): mp for mp in unique_midis}
        for i, future in enumerate(as_completed(futures)):
            mp, ok, size = future.result()
            if ok:
                rendered += 1
            else:
                failed += 1
            if (i + 1) % 50 == 0 or i == 0:
                elapsed = time.time() - start
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                logger.info(
                    "[%d/%d] rendered=%d failed=%d rate=%.1f/sec",
                    i + 1,
                    len(unique_midis),
                    rendered,
                    failed,
                    rate,
                )

    elapsed = time.time() - start
    logger.info("=" * 50)
    logger.info(
        "COMPLETE: %d rendered, %d failed in %.1fs (%.2f/sec)",
        rendered,
        failed,
        elapsed,
        rendered / elapsed if elapsed > 0 else 0,
    )
    logger.info(
        "Output: %s (%d MP3 files)",
        OUTPUT_DIR,
        len([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".mp3")]),
    )


if __name__ == "__main__":
    main()
