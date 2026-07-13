"""
MASTER PIPELINE ORCHESTRATOR — Full End-to-End Hymn Cover Pipeline
=====================================================================

Runs the COMPLETE pipeline:
  1. Browser connectivity check
  2. Synthesize sine-wave audio for all speed variants
  3. Upload each speed variant to Suno
  4. Handle Identify/Describe modals
  5. Create v5.5 covers via More -> Remix -> Cover (ALL genres for each speed)
  6. Poll feed and download completed MP3s
  7. Render projectM MilkDrop visualizer videos
  8. Upload videos to YouTube

USAGE:
  python pipeline_master_chain_orchestrator.py --midi ../hymn_remaker/input/Thy_Word.mid
  python pipeline_master_chain_orchestrator.py --midi ../hymn_remaker/input/Thy_Word.mid --genres "gabba,psytrance" --speeds "0.5,2.0"

SEE ALSO:
  - _batch_cover_generator.py for streamlined version (no video/YouTube)
  - AGENTS.md for full architecture documentation
"""

import os
import sys
import argparse
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
GEN_DIR = os.path.join(ROOT, "..", "generated")
CF = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0


def run_orchestrated_pipeline(midi_path, genres, speeds):
    hymn_name = os.path.splitext(os.path.basename(midi_path))[0]

    from pipeline_config_central_definitions_genres_speeds import SPEED_LABEL_MAP

    # convert float-keyed map to string-keyed map for cmd line parsing
    speed_map = {str(k): v for k, v in SPEED_LABEL_MAP.items()}

    # 1. Setup connection checks
    print("Checking Edge remote debugging status...")
    check_script = os.path.join(ROOT, "suno_browser_setup_connect_debugging_port.py")
    ret = subprocess.run(
        [sys.executable, check_script], capture_output=True, creationflags=CF
    )
    if ret.returncode != 0:
        print("Suno browser port checks failed. Verify port 9222.")
        sys.exit(1)

    for speed_str in speeds:
        speed_val = float(speed_str)
        speed_lbl = speed_map.get(speed_str, f"{speed_str}x")
        print(f"\nProcessing speed: {speed_str}x ({speed_lbl})")

        mp3_name = f"{hymn_name}_sine_{speed_lbl}.mp3"
        audio_path = os.path.join(ROOT, "..", "mp3_input", mp3_name)

        # 2. Synthesize Sine Wave and Filter
        print("Synthesizing audio...")
        synth_script = os.path.join(
            ROOT, "audio_speed_variants_exporter_for_multi_tempo_runs.py"
        )
        subprocess.run(
            [
                sys.executable,
                synth_script,
                "--midi",
                midi_path,
                "--outdir",
                os.path.dirname(audio_path),
            ],
            creationflags=CF,
        )

        # 3. Suno Upload
        print("Uploading audio to Suno...")
        upload_script = os.path.join(
            ROOT, "suno_audio_uploader_file_chooser_injector.py"
        )
        ret = subprocess.run(
            [sys.executable, upload_script, "--audio", audio_path], creationflags=CF
        )
        if ret.returncode != 0:
            print("Upload failed.")
            continue

        # 4. Modal Resolution
        dismissal_script = os.path.join(
            ROOT, "suno_modal_dismissal_identify_describe_overwrite_resolver.py"
        )
        ret = subprocess.run([sys.executable, dismissal_script], creationflags=CF)
        if ret.returncode != 0:
            print("Skipping to next speed due to copyright rejection.")
            continue

        # Fetch lyrics from database
        db_path = os.path.join(ROOT, "..", "hymn_remaker", "hymn_database.db")
        lyrics = None
        if os.path.exists(db_path):
            try:
                import sqlite3

                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT lyrics FROM hymns WHERE filename = ? OR original_filename = ? OR filename LIKE ? OR original_filename LIKE ?",
                    (
                        os.path.basename(midi_path),
                        os.path.basename(midi_path),
                        f"%{hymn_name}%",
                        f"%{hymn_name}%",
                    ),
                )
                row = cursor.fetchone()
                if row and row[0]:
                    lyrics = row[0].strip()
                conn.close()
            except Exception as e:
                print(f"DB query error: {e}")

        # 5. Create Cover remix and Polling
        for genre in genres:
            runs = []
            if lyrics:
                # Vocal cover run with original lyrics
                runs.append({"suffix": "vocal_lyrics", "args": ["--lyrics", lyrics]})
                # Vocal cover run with blank/no lyrics
                runs.append({"suffix": "vocal_no_lyrics", "args": ["--lyrics", ""]})
            else:
                runs.append({"suffix": "instrumental", "args": ["--instrumental"]})

            for run in runs:
                print(f"Triggering {run['suffix']} cover generation for {genre}...")
                cover_script = os.path.join(
                    ROOT, "suno_cover_remix_options_form_style_submitter.py"
                )
                cmd = [sys.executable, cover_script, genre, speed_lbl, hymn_name] + run[
                    "args"
                ]
                proc = subprocess.run(
                    cmd, capture_output=True, text=True, creationflags=CF
                )
                if proc.returncode != 0:
                    print("Cover trigger failed.")
                    print("SUBPROCESS ERROR:")
                    print(proc.stderr)
                    continue

                clip_ids = None
                for line in proc.stdout.split("\n"):
                    if line.startswith("CLIPS:"):
                        clip_ids = line.replace("CLIPS:", "").strip().split(",")
                        break

                if not clip_ids:
                    print("No clip IDs retrieved.")
                    continue

                print("Polling status and downloading...")
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
                        speed_lbl,
                        genre,
                        "--suffix",
                        run["suffix"],
                    ],
                    creationflags=CF,
                )
                if ret.returncode != 0:
                    print("Polling failed.")
                    continue

                # 6. Render Visuals & Upload to YouTube
                for vi, clip_id in enumerate(clip_ids):
                    vlabel = ["A", "B"][vi]
                    cover_audio = os.path.join(
                        GEN_DIR,
                        f"{hymn_name}_{speed_lbl}_{genre}_{run['suffix']}_{vlabel}_cover.mp3",
                    )
                    cover_video = os.path.join(
                        GEN_DIR,
                        f"{hymn_name}_{speed_lbl}_{genre}_{run['suffix']}_{vlabel}_cover.mp4",
                    )
                    video_title = f"{genre.title()} Hymn Remix: {hymn_name} ({run['suffix']} Speed {speed_lbl})"

                    print("Rendering visualizer video...")
                    render_script = os.path.join(
                        ROOT, "visuals_video_ffmpeg_pipe_muxer.py"
                    )
                    ret = subprocess.run(
                        [
                            sys.executable,
                            render_script,
                            "--audio",
                            cover_audio,
                            "--video",
                            cover_video,
                            "--duration",
                            "120",
                        ],
                        creationflags=CF,
                    )
                    if ret.returncode != 0:
                        print("Visuals rendering failed.")
                        continue

                    print("Uploading visualizer to YouTube...")
                    youtube_script = os.path.join(
                        ROOT, "v2_youtube_oauth_uploader_with_hymn_metadata.py"
                    )
                    subprocess.run(
                        [
                            sys.executable,
                            youtube_script,
                            "--video",
                            cover_video,
                            "--title",
                            video_title,
                            "--genre",
                            genre,
                        ],
                        creationflags=CF,
                    )


def main():
    parser = argparse.ArgumentParser(
        description="Consolidated Orchestration Pipeline Chain"
    )
    parser.add_argument("--midi", required=True)
    parser.add_argument("--genres", default="gabba,psytrance")
    parser.add_argument("--speeds", default="0.5,1.0,1.5,2.0,3.0")
    args = parser.parse_args()

    genres = args.genres.split(",")
    speeds = args.speeds.split(",")

    run_orchestrated_pipeline(args.midi, genres, speeds)


if __name__ == "__main__":
    main()
