"""tut_batch.py — Run: one song, all genres, all speeds, lyrics + instrumental.

Usage:
    python tut_batch.py twinkle_twinkle
    python tut_batch.py twinkle_twinkle --mode instrumental   # instrumental only
    python tut_batch.py twinkle_twinkle --mode lyrics          # lyrics only
    python tut_batch.py twinkle_twinkle --dry-run              # show what would run
"""

import os
import sys
import time
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tut_pipeline.tut_config import (
    GENRES,
    SPEEDS,
    wav_path,
    mp3_path,
    has_lyrics,
    lyrics_for,
)
from tut_pipeline.tut_utils.browser import connect_playwright, create_fresh_page
from tut_pipeline.tut_utils.suno_upload import upload_wav_to_suno
from tut_pipeline.tut_utils.suno_feed import get_and_download

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("tut_batch")

MAX_RETRIES = 2
WAIT_AFTER_CREATE = 90

TOTAL_SLOTS = len(GENRES) * len(SPEEDS) * 2  # 10 × 4 × 2 = 80


def generate_one(
    song,
    genre_prompt,
    genre_slug,
    speed,
    vocal_mode="instrumental",
    pw=None,
    browser=None,
):
    """Generate one track. Returns output path or None."""
    out = mp3_path(song, genre_slug, speed, vocal_mode)
    if os.path.exists(out):
        logger.info(f"  SKIP: {os.path.basename(out)}")
        return out

    wav = wav_path(song, speed)
    if not os.path.exists(wav):
        logger.warning(f"  MISS WAV: {os.path.basename(wav)}")
        return None

    # Build prompt with optional lyrics
    if vocal_mode == "lyrics" and has_lyrics(song):
        prompt = f"{genre_prompt} — sing these lyrics: {lyrics_for(song)}"
    else:
        prompt = genre_prompt

    for attempt in range(1, MAX_RETRIES + 1):
        page = create_fresh_page(browser)
        if upload_wav_to_suno(page, wav, prompt):
            time.sleep(WAIT_AFTER_CREATE)
            if get_and_download(page, browser.contexts[0], out):
                size_kb = os.path.getsize(out) // 1024
                logger.info(
                    f"  DONE {vocal_mode}: {os.path.basename(out)} ({size_kb}KB)"
                )
                return out
            else:
                logger.warning(f"  Download failed, retry {attempt}")
        else:
            logger.warning(f"  Create disabled, retry {attempt}")
    return None


def main():
    parser = argparse.ArgumentParser(
        description="TUT Batch: all genres × speeds × vocal modes"
    )
    parser.add_argument("song", help="Song name (e.g. twinkle_twinkle)")
    parser.add_argument(
        "--mode", choices=["instrumental", "lyrics", "both"], default="both"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show jobs without running"
    )
    args = parser.parse_args()

    song = args.song.lower().replace(" ", "_")

    # Build job list
    jobs = []
    for genre_prompt, genre_slug in GENRES:
        for speed in SPEEDS:
            if args.mode in ("both", "instrumental"):
                jobs.append((genre_prompt, genre_slug, speed, "instrumental"))
            if args.mode in ("both", "lyrics") and has_lyrics(song):
                jobs.append((genre_prompt, genre_slug, speed, "lyrics"))

    logger.info(
        f"Song: {song} | Genres: {len(GENRES)} | Speeds: {len(SPEEDS)} | Vocal modes: {args.mode}"
    )
    logger.info(f"Total jobs: {len(jobs)}")

    # Check what's already done
    done = sum(
        1 for gp, gs, sp, vm in jobs if os.path.exists(mp3_path(song, gs, sp, vm))
    )
    todo = len(jobs) - done
    logger.info(f"Already done: {done} | Remaining: {todo}")

    if args.dry_run:
        for gp, gs, sp, vm in jobs:
            out = mp3_path(song, gs, sp, vm)
            exists = "SKIP" if os.path.exists(out) else "NEW "
            print(f"  {exists} {gs:15s} @ {sp}x [{vm:12s}] -> {os.path.basename(out)}")
        return

    if todo == 0:
        logger.info("All jobs already done!")
        return

    pw, browser = connect_playwright()
    try:
        count = 0
        for i, (genre_prompt, genre_slug, speed, vocal_mode) in enumerate(jobs):
            logger.info(
                f"\n[{i + 1}/{len(jobs)}] {genre_slug} @ {speed}x [{vocal_mode}]"
            )
            result = generate_one(
                song, genre_prompt, genre_slug, speed, vocal_mode, pw, browser
            )
            if result:
                count += 1
            time.sleep(5)  # brief cooldown between generations
        logger.info(f"\nDone: {count}/{todo} generated")
    finally:
        pw.stop()


if __name__ == "__main__":
    main()
