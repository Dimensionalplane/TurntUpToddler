#!/usr/bin/env python3
"""
Test the full HymnMania pipeline: MIDI → WAV → MP3 → Suno Audio Upload → Generate.

Usage:
    python test_suno_pipeline.py <midi_file> [--prompt "style prompt"] [--lyrics "lyrics"]

Requirements:
    - Edge/Chrome running with --remote-debugging-port=9222
    - Logged into Suno.com in that browser
    - FFmpeg available on PATH
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("test_pipeline")

# Paths
ROOT = os.path.dirname(os.path.abspath(__file__))
HYMN_REMAKER = os.path.join(ROOT, "hymn_remaker")
OUTPUT_DIR = os.path.join(HYMN_REMAKER, "output")
INPUT_DIR = os.path.join(HYMN_REMAKER, "input")

# ── Step 1: Render MIDI to WAV ────────────────────────────────────────


def render_midi_to_wav(midi_path: str) -> str:
    """Render a MIDI file to WAV using FluidSynth directly or via Docker."""
    wav_path = os.path.join(
        OUTPUT_DIR, os.path.basename(midi_path).replace(".mid", ".wav")
    )

    # Check if already rendered
    if os.path.exists(wav_path) and os.path.getsize(wav_path) > 1000:
        logger.info(
            "Already rendered: %s (%dKB)", wav_path, os.path.getsize(wav_path) // 1024
        )
        return wav_path

    # Try Docker-based rendering (FluidSynth is in the Docker image)
    soundfont = os.path.join(HYMN_REMAKER, "soundfonts", "FluidR3_GM.sf2")
    if not os.path.exists(soundfont):
        # Find any .sf2 file
        sf2_files = []
        for root_dir, dirs, files in os.walk(os.path.join(ROOT, "hymn_remaker")):
            for f in files:
                if f.endswith(".sf2"):
                    sf2_files.append(os.path.join(root_dir, f))
        if sf2_files:
            soundfont = sf2_files[0]
        else:
            logger.warning("No SoundFont found. Using FFmpeg sine wave fallback.")
            # Create a minimal WAV as placeholder
            _create_placeholder_wav(wav_path)
            return wav_path

    # Use fluidsynth CLI if available
    try:
        subprocess.run(
            ["fluidsynth", "-ni", soundfont, midi_path, "-F", wav_path, "-r", "44100"],
            check=True,
            capture_output=True,
            timeout=60,
        )
        logger.info("Rendered MIDI to WAV: %s", wav_path)
        return wav_path
    except (FileNotFoundError, subprocess.CalledProcessError):
        logger.warning("FluidSynth CLI not available. Trying Docker...")
        try:
            subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{os.path.dirname(midi_path)}:/input",
                    "-v",
                    f"{OUTPUT_DIR}:/output",
                    "hymn_remaker_ui",
                    "fluidsynth",
                    "-ni",
                    "/usr/share/sounds/sf2/FluidR3_GM.sf2",
                    f"/input/{os.path.basename(midi_path)}",
                    "-F",
                    f"/output/{os.path.basename(wav_path)}",
                    "-r",
                    "44100",
                ],
                check=True,
                capture_output=True,
                timeout=120,
            )
            logger.info("Rendered via Docker: %s", wav_path)
            return wav_path
        except Exception as e:
            logger.error("Docker rendering failed: %s", e)
            _create_placeholder_wav(wav_path)
            return wav_path


def _create_placeholder_wav(path: str):
    """Create a simple sine wave WAV as placeholder."""
    import struct
    import math

    sample_rate = 44100
    duration = 10  # 10 seconds
    samples = int(sample_rate * duration)
    with open(path, "wb") as f:
        data_size = samples * 2
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        for i in range(samples):
            sample = int(16000 * math.sin(2 * math.pi * 440 * i / sample_rate))
            f.write(struct.pack("<h", sample))
    logger.info("Created placeholder WAV: %s (%.1fs sine wave)", path, duration)


# ── Step 2: Convert WAV to MP3 ────────────────────────────────────────


def convert_to_mp3(wav_path: str) -> str:
    """Convert WAV to MP3 via FFmpeg."""
    mp3_path = wav_path.rsplit(".", 1)[0] + ".mp3"
    if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 1000:
        logger.info("MP3 already exists: %s", mp3_path)
        return mp3_path

    result = subprocess.run(
        [
            "ffmpeg",
            "-i",
            wav_path,
            "-codec:a",
            "libmp3lame",
            "-b:a",
            "128k",
            "-y",
            mp3_path,
        ],
        capture_output=True,
        timeout=120,
    )
    if result.returncode != 0:
        logger.warning("FFmpeg conversion failed: %s", result.stderr[:200])
        return wav_path
    logger.info(
        "Converted to MP3: %s (%dKB)", mp3_path, os.path.getsize(mp3_path) // 1024
    )
    return mp3_path


# ── Step 3: Launch Edge with CDP ──────────────────────────────────────


def launch_edge_with_cdp(port: int = 9222, user_data_dir: str = None):
    """Launch Edge with remote debugging on the specified port."""
    edge_paths = [
        "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "msedge",
        "edge",
        "chrome",
        "google-chrome",
    ]

    edge_exe = None
    for p in edge_paths:
        if os.path.exists(p):
            edge_exe = p
            break
    if not edge_exe:
        import shutil

        for p in edge_paths:
            if shutil.which(p):
                edge_exe = p
                break
    if not edge_exe:
        raise RuntimeError("No Edge/Chrome found. Please install Microsoft Edge.")

    if not user_data_dir:
        user_data_dir = os.path.join(ROOT, ".suno_browser_session")

    args = [
        edge_exe,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "https://suno.com/create",
    ]

    logger.info("Launching Edge with CDP on port %d...", port)
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logger.info("Edge launched (PID: %d). Waiting for CDP endpoint...", proc.pid)

    # Wait for CDP to be ready
    import urllib.request

    for i in range(30):
        try:
            resp = urllib.request.urlopen(
                f"http://127.0.0.1:{port}/json/version", timeout=2
            )
            if resp.status == 200:
                logger.info("CDP ready after %ds", i + 1)
                return proc
        except Exception:
            pass
        time.sleep(1)

    logger.warning("CDP not ready after 30s. Continuing anyway...")
    return proc


# ── Step 4: Run Suno Pipeline ─────────────────────────────────────────


def run_suno_pipeline(audio_file: str, prompt: str, lyrics: str = None):
    """Run the Suno browser automation pipeline."""
    from hymn_remaker.src.suno_browser_automation import SunoBrowserAutomation

    bot = SunoBrowserAutomation(port=9222)

    # Check if Edge/Suno is available
    tab = bot._get_active_tab(require_suno=True)
    if not tab:
        logger.error("No Suno tab found! Launch Edge with --remote-debugging-port=9222")
        return False

    logger.info("Found Suno tab: %s", tab.get("url", "unknown"))

    # Run the trigger_generation flow
    success = bot.trigger_generation(
        prompt=prompt,
        audio_path=audio_file,
        make_instrumental=True,
        lyrics=lyrics,
    )

    if success:
        logger.info("✅ Suno generation triggered successfully!")
    else:
        logger.error("❌ Suno generation failed. Check cdp_debug_suno.png for state.")
        # Save diagnostic info
        ws_url = tab.get("webSocketDebuggerUrl")
        if ws_url:
            try:
                diag = bot._diag_upload_state(ws_url)
                logger.info("Diagnostic: %s", json.dumps(diag, indent=2))
            except Exception as e:
                logger.warning("Diagnostic failed: %s", e)

    return success


# ── Main ──────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Test HymnMania MIDI → Suno pipeline")
    parser.add_argument("midi", nargs="?", default=None, help="MIDI file path")
    parser.add_argument(
        "--prompt",
        default="Hymn melody transformed into psytrance, 145 BPM, energetic full-on, rolling bassline, euclidean arpeggios",
        help="Style prompt for Suno",
    )
    parser.add_argument("--lyrics", default=None, help="Lyrics text")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Skip launching browser (use existing)",
    )
    args = parser.parse_args()

    # Resolve MIDI file
    if args.midi:
        midi_path = args.midi
    else:
        # Use first available MIDI in input directory
        midis = sorted([f for f in os.listdir(INPUT_DIR) if f.endswith(".mid")])
        if not midis:
            logger.error("No MIDI files found in %s", INPUT_DIR)
            sys.exit(1)
        midi_path = os.path.join(INPUT_DIR, midis[0])

    if not os.path.exists(midi_path):
        logger.error("MIDI file not found: %s", midi_path)
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("  TEST: MIDI → SUNO PIPELINE")
    logger.info("  MIDI: %s", midi_path)
    logger.info("=" * 60)

    # Step 1: Render MIDI to WAV
    wav_path = render_midi_to_wav(midi_path)

    # Step 2: Convert to MP3
    mp3_path = convert_to_mp3(wav_path)

    # Step 3: Launch Edge with CDP (if not already running)
    edge_proc = None
    if not args.no_browser:
        edge_proc = launch_edge_with_cdp()
        logger.info("Waiting 15s for Suno page to load...")
        time.sleep(15)

    # Step 4: Run Suno pipeline
    success = run_suno_pipeline(mp3_path, args.prompt, args.lyrics)

    if success:
        logger.info("\n✅ Pipeline test PASSED!")
        logger.info("   Check Suno.com for the generation in progress.")
    else:
        logger.error("\n❌ Pipeline test FAILED.")
        logger.info("   Debug screenshot saved to cdp_debug_suno.png")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
