"""tut_cover.py — Step 4: Generate melody-faithful covers via Suno Remix→Cover flow.

Two-step process:
    1. Upload WAV → generate a short base clip on Suno
    2. Nav to that clip → Remix → Cover → set style → generate → download

Usage:
    python tut_cover.py twinkle_twinkle                  # all genres × all speeds
    python tut_cover.py twinkle_twinkle --genre goa      # one genre
    python tut_cover.py twinkle_twinkle --speed 1.0      # one speed
"""
import os
import sys
import re
import time
import argparse
import logging
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tut_pipeline.tut_config import GENRES, SPEEDS, SONGS, wav_path, mp3_path
from tut_pipeline.tut_utils.browser import connect_playwright, create_fresh_page
from tut_pipeline.tut_utils.suno_upload import upload_wav_to_suno
from tut_pipeline.tut_utils.suno_feed import get_session_token, poll_until_complete, download_mp3, find_latest_clip_id

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("tut_cover")

MAX_RETRIES = 3
WAIT_STEP1 = 60
WAIT_STEP2 = 90


def step1_upload_base(song, genre_prompt, speed, browser):
    """Upload WAV and generate a base clip. Returns clip_id or None."""
    wav = wav_path(song, speed)
    if not os.path.exists(wav):
        logger.warning(f"MISS WAV: {os.path.basename(wav)}")
        return None

    for attempt in range(1, MAX_RETRIES + 1):
        page = create_fresh_page(browser)
        if upload_wav_to_suno(page, wav, genre_prompt):
            time.sleep(WAIT_STEP1)
            clip_id = find_latest_clip_id(page)
            if clip_id:
                st = get_session_token(browser.contexts[0])
                if st:
                    poll_until_complete(st, clip_id, timeout=120)
                return clip_id
    return None


def step2_create_cover(browser, upload_clip_id, genre_prompt, out_mp3):
    """Navigate to uploaded song page, Remix → Cover → Generate → Download."""
    for attempt in range(1, MAX_RETRIES + 1):
        page = create_fresh_page(browser)
        try:
            page.goto(f"https://suno.com/song/{upload_clip_id}", wait_until="domcontentloaded", timeout=30000)
            time.sleep(6)
            page.evaluate("document.querySelectorAll('[role=dialog]').forEach(d => d.remove())")
            time.sleep(2)
        except Exception:
            continue

        # Click Remix
        try:
            page.evaluate("""Array.from(document.querySelectorAll('button')).find(b =>
                b.offsetParent !== null && (b.innerText || '').trim() === 'Remix'
            )?.click()""")
            time.sleep(3)
        except Exception:
            continue

        # Click Cover
        try:
            page.evaluate("""Array.from(document.querySelectorAll('button')).find(b =>
                b.offsetParent !== null && (b.innerText || '').trim() === 'Cover'
            )?.click()""")
            time.sleep(3)
        except Exception:
            continue

        # Fill style
        try:
            page.evaluate(f"""
                var tas = Array.from(document.querySelectorAll('textarea')).filter(t => t.offsetParent !== null);
                if (tas.length > 0) {{
                    var ns = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                    ns.call(tas[tas.length-1], '{genre_prompt}');
                    tas[tas.length-1].dispatchEvent(new Event('input', {{bubbles: true}}));
                }}
            """)
            time.sleep(2)
        except Exception:
            continue

        # Click Generate
        try:
            page.evaluate("""(() => {
                let btn = Array.from(document.querySelectorAll('button')).find(b =>
                    b.offsetParent !== null && !b.hasAttribute('disabled') &&
                    (b.innerText || '').match(/Create|Generate|Cover/i) &&
                    !['Home','Explore','Create','Studio','Library','Notifications',
                      'Earn Credits','Labs','Terms & Policies','More'
                     ].includes((b.innerText || '').trim())
                );
                if (btn) { btn.click(); return 'ok'; }
                return 'no';
            })()""")
        except Exception:
            continue

        time.sleep(WAIT_STEP2)

        # Download via feed polling
        st = get_session_token(browser.contexts[0])
        if st:
            for m in range(8):
                time.sleep(15)
                try:
                    feed = requests.get(
                        "https://studio-api.prod.suno.com/api/feed/?page=1",
                        headers={"Authorization": f"Bearer {st}"},
                        timeout=10,
                    )
                    if feed.status_code == 200 and feed.json():
                        for item in feed.json():
                            if item.get("status") == "complete" and item.get("audio_url"):
                                if download_mp3(item["audio_url"], out_mp3):
                                    return True
                except Exception:
                    pass

        # Fallback: scrape cover clips from song page
        try:
            page.goto(f"https://suno.com/song/{upload_clip_id}", wait_until="domcontentloaded", timeout=30000)
            time.sleep(5)
            all_clips = re.findall(r"/song/([0-9a-f-]+)", page.content())
            remix_clips = [c for c in all_clips if c != upload_clip_id]
            if remix_clips and st:
                audio_url = poll_until_complete(st, remix_clips[-1], timeout=120)
                if audio_url and download_mp3(audio_url, out_mp3):
                    return True
        except Exception:
            pass

    return False


def cover_one(song, genre_prompt, genre_slug, speed, browser):
    """Generate one melody-faithful cover. Returns output path or None."""
    out = mp3_path(song, genre_slug, speed)
    if os.path.exists(out):
        logger.info(f"SKIP: {os.path.basename(out)}")
        return out

    logger.info(f"  {song}/{genre_slug}/{speed}x")
    upload_id = step1_upload_base(song, genre_prompt, speed, browser)
    if not upload_id:
        logger.warning("  Step 1 failed — upload base clip")
        return None

    logger.info(f"  Base clip: {upload_id[:12]}...")
    if step2_create_cover(browser, upload_id, genre_prompt, out):
        size_kb = os.path.getsize(out) // 1024
        logger.info(f"  COVER: {os.path.basename(out)} ({size_kb}KB)")
        return out

    logger.warning("  Step 2 failed — cover generation")
    return None


def main():
    parser = argparse.ArgumentParser(description="TUT Cover: melody-faithful Suno covers")
    parser.add_argument("song", nargs="?", help="Song name (e.g. twinkle_twinkle)")
    parser.add_argument("--genre", help="Genre slug (e.g. goa)")
    parser.add_argument("--speed", type=float, help="Single speed (e.g. 1.0)")
    parser.add_argument("--all", action="store_true", help="Cover all songs")
    args = parser.parse_args()

    songs = SONGS if args.all else [args.song] if args.song else None
    if not songs:
        logger.error("Specify a song name or --all")
        return

    genres = [g for g in GENRES if not args.genre or g[1] == args.genre]
    speeds = [args.speed] if args.speed else SPEEDS

    pw, browser = connect_playwright()
    try:
        covered = 0
        for song in songs:
            for genre_prompt, genre_slug in genres:
                for speed in speeds:
                    result = cover_one(song, genre_prompt, genre_slug, speed, browser)
                    if result:
                        covered += 1
        logger.info(f"Done: {covered} covers generated")
    finally:
        pw.stop()


if __name__ == "__main__":
    main()
