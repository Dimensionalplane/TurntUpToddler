#!/usr/bin/env python
"""
Full Suno Pipeline: MIDI → WAV → Speed Variants → MP3 → Suno Upload → Download

Usage:
    python scripts/full_suno_pipeline.py <midi_path> [--lyrics <lyrics.txt>] [--prompt "my style prompt"]

Requires:
    - Edge running with --remote-debugging-port=9222
    - Suno.com open and logged in
"""

import os
import sys
import json
import time
import logging
import argparse
import subprocess
from pathlib import Path

# Ensure root is in path
sys.path.insert(0, os.getcwd())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("SunoPipeline")


def check_edge_debugging():
    """Check if Edge is running with remote debugging on port 9222."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(("127.0.0.1", 9222))
    sock.close()
    if result != 0:
        logger.error(
            "Edge with CDP 9222 not found!\n"
            "Please launch Edge with:\n"
            '  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" --remote-debugging-port=9222\n'
            "Then navigate to suno.com/create and log in."
        )
        return False
    logger.info("Edge debugging port 9222: OPEN")
    return True


def check_suno_tab():
    """Check if Suno.com tab is open in Edge."""
    import requests
    try:
        res = requests.get("http://127.0.0.1:9222/json", timeout=3)
        targets = res.json()
        for t in targets:
            if t.get("type") == "page" and "suno.com" in t.get("url", "").lower():
                logger.info(f"Suno tab found: {t.get('url')}")
                return True
        logger.warning("No Suno tab found. Open suno.com/create in Edge and log in.")
        return False
    except Exception as e:
        logger.error(f"Cannot connect to Edge: {e}")
        return False


def step1_render_midi(midi_path, output_wav):
    """Render MIDI to WAV using Python fallback (pretty_midi + numpy + scipy)."""
    logger.info(f"Step 1: Rendering MIDI -> WAV: {midi_path}")

    import numpy as np
    from scipy.io import wavfile

    try:
        import pretty_midi
        pm = pretty_midi.PrettyMIDI(str(midi_path))
        duration = pm.get_end_time()
        logger.info(f"  Duration: {duration:.2f}s, Instruments: {len(pm.instruments)}")
    except Exception:
        import mido
        mid = mido.MidiFile(str(midi_path))
        duration = mid.length
        logger.warning(f"  Using mido fallback. Duration: {duration:.2f}s")
        # Create a dummy pretty_midi-compatible structure
        pm = pretty_midi.PrettyMIDI(initial_tempo=120.0)
        for i, track in enumerate(mid.tracks):
            inst = pretty_midi.Instrument(program=0, name=f"Track {i}")
            tick_time = 0
            for msg in track:
                tick_time += msg.time
                if msg.type == 'note_on' and msg.velocity > 0:
                    note = pretty_midi.Note(
                        velocity=msg.velocity,
                        pitch=msg.note,
                        start=mid.tick_to_time(tick_time),
                        end=mid.tick_to_time(tick_time + 120),
                    )
                    inst.notes.append(note)
            if inst.notes:
                pm.instruments.append(inst)

    if duration <= 0:
        duration = 4.0

    sample_rate = 44100
    audio = np.zeros(int(sample_rate * duration), dtype=np.float32)

    for inst in pm.instruments:
        for note in inst.notes:
            start = int(note.start * sample_rate)
            end = int(note.end * sample_rate)
            if start >= len(audio):
                continue
            freq = 440 * (2 ** ((note.pitch - 69) / 12))
            t = np.arange(min(end, len(audio)) - start) / sample_rate
            env = np.exp(-5 * t)  # gentle decay for natural sound
            sine = np.sin(2 * np.pi * freq * t) * (note.velocity / 127.0) * 0.3 * env
            audio[start:start + len(sine)] += sine

    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.9

    os.makedirs(os.path.dirname(output_wav) or '.', exist_ok=True)
    wavfile.write(output_wav, sample_rate, (audio * 32767).astype(np.int16))
    size_kb = os.path.getsize(output_wav) / 1024
    logger.info(f"  Rendered: {output_wav} ({size_kb:.0f} KB)")
    return audio, sample_rate


def step2_speed_variants(audio, sample_rate, output_base):
    """Export 0.5x, 1x, 2x, 4x speed variants."""
    logger.info(f"Step 2: Exporting speed variants to {output_base}...")

    import numpy as np
    from scipy.io import wavfile

    paths = {}

    # 1.0x Base
    p = f"{output_base}_1x.wav"
    wavfile.write(p, sample_rate, (audio * 32767).astype(np.int16))
    paths["1x"] = p

    # 0.5x
    indices = np.arange(0, len(audio), 0.5)
    indices = np.clip(indices, 0, len(audio) - 1).astype(np.int64)
    audio_05 = audio[indices]
    p = f"{output_base}_05x.wav"
    wavfile.write(p, sample_rate, (audio_05 * 32767).astype(np.int16))
    paths["05x"] = p

    # 2.0x
    audio_20 = audio[::2]
    p = f"{output_base}_2x.wav"
    wavfile.write(p, sample_rate, (audio_20 * 32767).astype(np.int16))
    paths["2x"] = p

    # 4.0x
    audio_40 = audio[::4]
    p = f"{output_base}_4x.wav"
    wavfile.write(p, sample_rate, (audio_40 * 32767).astype(np.int16))
    paths["4x"] = p

    for name, path in paths.items():
        size_kb = os.path.getsize(path) / 1024
        logger.info(f"  {name}: {path} ({size_kb:.0f} KB)")

    return paths


def step3_convert_to_mp3(wav_path):
    """Convert WAV to MP3 using ffmpeg."""
    mp3_path = wav_path.rsplit(".wav", 1)[0] + ".mp3"
    if os.path.exists(mp3_path):
        logger.info(f"  MP3 already exists: {mp3_path}")
        return mp3_path

    logger.info(f"  Converting to MP3: {wav_path} -> {mp3_path}")
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-b:a", "192k", mp3_path],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[:200]}")
    size_kb = os.path.getsize(mp3_path) / 1024
    logger.info(f"  MP3: {mp3_path} ({size_kb:.0f} KB)")
    return mp3_path


def step4_upload_to_suno(mp3_path, lyrics=None, prompt=None, hymn_name="Hymn"):
    """
    Step 4: Connect to Edge CDP and upload MP3 as audio inspiration to Suno.
    Uses the browser automation module.
    """
    logger.info(f"Step 4: Uploading {mp3_path} to Suno via CDP...")

    from hymn_remaker.src.suno_browser_automation import SunoBrowserAutomation

    sba = SunoBrowserAutomation(port=9222)

    # Build the prompt
    full_prompt = prompt or (
        f"Create a deep house version inspired by this hymn melody. "
        f"Transform it into a club-ready track with "
        f"four-on-the-floor kick, deep bass, atmospheric pads, "
        f"and subtle references to the original hymn's melody."
    )

    # Trigger generation with the audio as inspiration
    logger.info(f"  Prompt: {full_prompt[:80]}...")
    logger.info(f"  Lyrics: {'yes (' + str(len(lyrics)) + ' chars)' if lyrics else 'none (instrumental)'}")
    logger.info(f"  Audio: {os.path.basename(mp3_path)}")

    success = sba.trigger_generation(
        prompt=full_prompt,
        audio_path=mp3_path,
        make_instrumental=(lyrics is None),
        lyrics=lyrics,
    )

    if success:
        logger.info("✅ Generation triggered! Now waiting for completion...")
        return True
    else:
        logger.error("❌ Failed to trigger generation")
        return False


def step5_wait_and_download(timeout=400):
    """Wait for Suno generation to complete and download the track."""
    logger.info(f"Step 5: Waiting for completion (timeout={timeout}s)...")
    from hymn_remaker.src.suno_browser_automation import SunoBrowserAutomation
    sba = SunoBrowserAutomation(port=9222)
    return sba.wait_for_completion_and_download(timeout=timeout)


def load_lyrics(filepath):
    """Load lyrics from a text file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read().strip()


def main():
    parser = argparse.ArgumentParser(description="Full Suno Pipeline: MIDI → Suno generation")
    parser.add_argument("midi", help="Path to input MIDI file")
    parser.add_argument("--lyrics", "-l", help="Path to lyrics text file")
    parser.add_argument("--prompt", "-p", help="Style prompt for Suno")
    parser.add_argument("--output-dir", "-o", default="output_suno", help="Output directory")
    parser.add_argument("--no-suno", action="store_true", help="Skip Suno upload (render only)")
    parser.add_argument("--skip-wait", action="store_true", help="Skip waiting for download")
    parser.add_argument("--variant", choices=["05x", "1x", "2x", "4x", "all"], default="1x",
                        help="Which speed variant to upload (default: 1x)")
    args = parser.parse_args()

    midi_path = Path(args.midi)
    if not midi_path.exists():
        logger.error(f"MIDI file not found: {midi_path}")
        sys.exit(1)

    hymn_name = midi_path.stem
    output_dir = Path(args.output_dir) / hymn_name
    os.makedirs(output_dir, exist_ok=True)

    # Load lyrics if provided
    lyrics = None
    if args.lyrics:
        lyrics = load_lyrics(args.lyrics)
        logger.info(f"Loaded lyrics: {len(lyrics)} chars")

    # === STEP 1: Render MIDI to WAV ===
    base_wav = str(output_dir / f"{hymn_name}_base.wav")
    audio, sr = step1_render_midi(midi_path, base_wav)

    # === STEP 2: Export speed variants ===
    variant_base = str(output_dir / hymn_name)
    variant_paths = step2_speed_variants(audio, sr, variant_base)

    # === STEP 3: Convert selected variant to MP3 ===
    if args.variant == "all":
        mp3_paths = {}
        for name, wav_path in variant_paths.items():
            mp3_paths[name] = step3_convert_to_mp3(wav_path)
        # Use 1x for Suno upload by default
        upload_mp3 = mp3_paths.get("1x", list(mp3_paths.values())[0])
    else:
        wav_to_upload = variant_paths[args.variant]
        upload_mp3 = step3_convert_to_mp3(wav_to_upload)

    logger.info(f"\n{'='*60}")
    logger.info("Rendered files in: %s", output_dir)
    for name, path in variant_paths.items():
        size = os.path.getsize(path) / 1024
        logger.info("  %s: %s (%.0f KB)", name, path, size)
    logger.info("  MP3: %s (%.0f KB)", upload_mp3, os.path.getsize(upload_mp3)/1024)
    logger.info("%s\n", '='*60)

    # === STEP 4: Upload to Suno ===
    if args.no_suno:
        logger.info("Skipping Suno upload (--no-suno)")
        return

    logger.info("\n=== Checking Edge/Suno setup ===")
    if not check_edge_debugging():
        logger.info("Attempting to launch Edge with CDP on port 9222...")
        import subprocess
        try:
            subprocess.run(
                [sys.executable, "scripts/launch_edge_suno.py"],
                capture_output=False, timeout=60
            )
            time.sleep(5)
        except Exception as e:
            logger.warning(f"Auto-launch failed: {e}")
        
        if not check_edge_debugging():
            logger.error(
                "\nCould not connect to Edge CDP. Please launch manually:\n"
                '  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" --remote-debugging-port=9222\n'
                "Then open suno.com/create and log in.\n"
                "Then run this script again."
            )
            sys.exit(1)

    if not check_suno_tab():
        logger.warning("No Suno tab found. Opening suno.com/create...")
        import requests
        try:
            # Find any page target and navigate it to Suno
            res = requests.get("http://127.0.0.1:9222/json", timeout=3)
            targets = res.json()
            for t in targets:
                if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                    import websocket
                    ws = websocket.create_connection(
                        t["webSocketDebuggerUrl"].replace("localhost", "127.0.0.1"),
                        suppress_origin=True, timeout=10
                    )
                    ws.send(json.dumps({
                        "id": 1, "method": "Page.navigate",
                        "params": {"url": "https://suno.com/create"}
                    }))
                    ws.recv()
                    ws.close()
                    logger.info("  Navigated to suno.com/create")
                    break
        except Exception as e:
            logger.error(f"  Could not navigate: {e}")
            sys.exit(1)

    logger.info("\n=== STEP 4: Uploading to Suno ===")
    success = step4_upload_to_suno(upload_mp3, lyrics=lyrics, prompt=args.prompt, hymn_name=hymn_name)

    if not success:
        logger.error("Suno generation failed to trigger")
        sys.exit(1)

    # === STEP 5: Wait and Download ===
    if args.skip_wait:
        logger.info("Skipping wait (--skip-wait). Check Suno tab manually.")
    else:
        logger.info("\n=== STEP 5: Waiting for completion and downloading ===")
        downloaded = step5_wait_and_download(timeout=400)
        if downloaded:
            logger.info(f"✅ Download completed for {hymn_name}!")
        else:
            logger.warning("Download may not have completed. Check Suno tab manually.")

    logger.info("\n=== Pipeline Complete ===")
    logger.info(f"All files in: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
