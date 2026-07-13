"""
BATCH COVER GENERATOR — Streamlined Pipeline (No Video/YouTube)
================================================================

Runs the full generation pipeline for ALL genres × ALL speeds:
  1. Synthesize sine-wave audio variants (via audio_speed_variants_exporter)
  2. Upload each speed variant to Suno (via suno_audio_uploader_file_chooser_injector)
  3. Handle Identify/Describe modals (via suno_modal_dismissal)
  4. For each genre: create v5.5 covers via More → Remix → Cover
  5. Download completed MP3s

CONFIGURATION:
  - Genres and speeds defined in pipeline_config_central_definitions_genres_speeds.py
  - 11 genres × 5 speeds = 55 cover generations (110 clips)
  - Output files: generated/{hymn}_{speed}_{genre}_instrumental_{A/B}_cover.mp3

USAGE:
  python _batch_cover_generator.py --midi ../hymn_remaker/input/Thy_Word.mid

PREREQUISITES:
  - Edge/Chrome on port 9222, logged into suno.com
  - Audio variants pre-synthesized (or they will be synthesized on-the-fly)
"""

import os
import sys
import subprocess
import argparse

ROOT = os.path.dirname(os.path.abspath(__file__))
GEN_DIR = os.path.join(ROOT, "..", "generated")
CF = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0

from pipeline_config_central_definitions_genres_speeds import (
    GENRES,
    SPEEDS,
    SPEED_LABEL_MAP,
)


def run_streamlined(midi_path):
    hymn_name = os.path.splitext(os.path.basename(midi_path))[0]
    os.makedirs(GEN_DIR, exist_ok=True)

    # Verify browser
    print("Checking Edge remote debugging...")
    check_script = os.path.join(ROOT, "suno_browser_setup_connect_debugging_port.py")
    ret = subprocess.run(
        [sys.executable, check_script], capture_output=True, creationflags=CF
    )
    if ret.returncode != 0:
        print("Browser not connected on port 9222.")
        sys.exit(1)
    print("Browser OK.\n")

    total = 0
    for speed in SPEEDS:
        label = speed_map = SPEED_LABEL_MAP[speed]
        mp3_name = f"{hymn_name}_sine_{label}.mp3"
        audio_path = os.path.join(ROOT, "..", "mp3_input", mp3_name)

        if not os.path.exists(audio_path):
            print(f"Missing audio: {audio_path}, synthesizing...")
            synth = os.path.join(
                ROOT, "audio_speed_variants_exporter_for_multi_tempo_runs.py"
            )
            subprocess.run(
                [
                    sys.executable,
                    synth,
                    "--midi",
                    midi_path,
                    "--outdir",
                    os.path.dirname(audio_path),
                ],
                creationflags=CF,
            )

        # Upload
        print(f"\n{'=' * 60}")
        print(f"SPEED: {label} ({speed}x) - Uploading...")
        upload_script = os.path.join(
            ROOT, "suno_audio_uploader_file_chooser_injector.py"
        )
        ret = subprocess.run(
            [sys.executable, upload_script, "--audio", audio_path], creationflags=CF
        )
        if ret.returncode != 0:
            print("Upload failed, skipping speed.")
            continue

        # Modal
        dismissal = os.path.join(
            ROOT, "suno_modal_dismissal_identify_describe_overwrite_resolver.py"
        )
        ret = subprocess.run([sys.executable, dismissal], creationflags=CF)
        if ret.returncode != 0:
            print("Modal/copyright rejection, skipping speed.")
            continue

        # For each genre: Create cover + Download
        for genre_name, genre_desc in GENRES.items():
            print(f"\n  GENRE: {genre_name} ({genre_desc})")
            total += 1

            # Cover creation
            cover_script = os.path.join(
                ROOT, "suno_cover_remix_options_form_style_submitter.py"
            )
            proc = subprocess.run(
                [
                    sys.executable,
                    cover_script,
                    genre_name,
                    label,
                    hymn_name,
                    "--instrumental",
                ],
                capture_output=True,
                text=True,
                creationflags=CF,
            )
            if proc.returncode != 0:
                print(f"  Cover trigger failed: {proc.stderr[:200]}")
                continue

            clip_ids = None
            for line in proc.stdout.split("\n"):
                if line.startswith("CLIPS:"):
                    clip_ids = line.replace("CLIPS:", "").strip().split(",")
                    break

            if not clip_ids:
                print("  No clip IDs from cover trigger.")
                continue

            print(f"  Clips: {clip_ids}")

            # Poll + Download
            poll_script = os.path.join(
                ROOT, "suno_feed_polling_status_monitor_downloader.py"
            )
            ret = subprocess.run(
                [
                    sys.executable,
                    poll_script,
                    ",".join(clip_ids),
                    GEN_DIR,
                    hymn_name,
                    label,
                    genre_name,
                    "--suffix",
                    "instrumental",
                ],
                creationflags=CF,
            )
            if ret.returncode == 0:
                print(f"  ✅ Downloaded {genre_name}")

        print(f"\n  Completed all genres for speed {label}")

    print(f"\n{'=' * 60}")
    print(f"Total cover generations triggered: {total}")
    print(f"Check {GEN_DIR} for results.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--midi", required=True)
    args = parser.parse_args()
    run_streamlined(args.midi)
