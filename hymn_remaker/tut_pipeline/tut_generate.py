"""tut_generate.py — Step 3: Upload WAV to Suno and generate EDM tracks.

Usage:
    python tut_generate.py twinkle_twinkle                  # all genres × all speeds
    python tut_generate.py twinkle_twinkle --genre goa      # one genre
    python tut_generate.py twinkle_twinkle --speed 1.0      # one speed
"""
import os
import sys
import time
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tut_pipeline.tut_config import GENRES, SPEEDS, SONGS, wav_path, mp3_path
from tut_pipeline.tut_utils.browser import connect_playwright, create_fresh_page
from tut_pipeline.tut_utils.suno_upload import upload_wav_to_suno
from tut_pipeline.tut_utils.suno_feed import get_and_download

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("tut_generate")

MAX_RETRIES = 3
WAIT_AFTER_CREATE = 90  # seconds for Suno to generate


def generate_one(song, genre_prompt, genre_slug, speed, pw, browser):
    """Generate one Suno track. Returns output path or None."""
    out = mp3_path(song, genre_slug, speed)
    if os.path.exists(out):
        logger.info(f"SKIP: {os.path.basename(out)}")
        return out

    wav = wav_path(song, speed)
    if not os.path.exists(wav):
        logger.warning(f"MISS WAV: {os.path.basename(wav)} -> run tut_render.py first")
        return None

    for attempt in range(1, MAX_RETRIES + 1):
        logger.info(f"  {song}/{genre_slug}/{speed}x (attempt {attempt})")
        page = create_fresh_page(browser)

        if upload_wav_to_suno(page, wav, genre_prompt):
            logger.info("  Create clicked")
            time.sleep(WAIT_AFTER_CREATE)

            if get_and_download(page, browser.contexts[0], out):
                size_kb = os.path.getsize(out) // 1024
                logger.info(f"  DONE: {os.path.basename(out)} ({size_kb}KB)")
                return out
            else:
                logger.warning("  Download failed, retrying...")
        else:
            logger.warning("  Create disabled, retrying...")

    logger.error(f"  FAILED after {MAX_RETRIES} retries")
    return None


def main():
    parser = argparse.ArgumentParser(description="TUT Generate: Suno EDM track creation")
    parser.add_argument("song", nargs="?", help="Song name (e.g. twinkle_twinkle)")
    parser.add_argument("--genre", help="Genre slug (e.g. goa, psytrance)")
    parser.add_argument("--speed", type=float, help="Single speed (e.g. 1.0)")
    parser.add_argument("--all", action="store_true", help="Generate all songs")
    args = parser.parse_args()

    songs = SONGS if args.all else [args.song] if args.song else None
    if not songs:
        logger.error("Specify a song name, --all, or use tut_cover.py for covers")
        return

    genres = [g for g in GENRES if not args.genre or g[1] == args.genre]
    speeds = [args.speed] if args.speed else SPEEDS

    pw, browser = connect_playwright()
    try:
        generated = 0
        for song in songs:
            for genre_prompt, genre_slug in genres:
                for speed in speeds:
                    result = generate_one(song, genre_prompt, genre_slug, speed, pw, browser)
                    if result:
                        generated += 1
        logger.info(f"Done: {generated} tracks generated")
    finally:
        pw.stop()


if __name__ == "__main__":
    main()
