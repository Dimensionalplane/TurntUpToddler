"""tut_utils/suno_feed.py — poll Suno API, find clips, download MP3s."""

import time
import re
import os
import requests
import logging

logger = logging.getLogger(__name__)


def get_session_token(browser_context):
    """Extract Suno __session JWT from browser cookies."""
    for c in browser_context.cookies():
        if c.get("name") == "__session":
            return c.get("value", "")
    return ""


def find_latest_clip_id(page):
    """Scrape the most recent clip ID from the Suno create page."""
    try:
        page.goto(
            "https://suno.com/create", wait_until="domcontentloaded", timeout=30000
        )
        time.sleep(5)
        clips = re.findall(r"/song/([0-9a-f-]+)", page.content())
        return clips[-1] if clips else None
    except Exception as e:
        logger.warning(f"find_latest_clip_id: {e}")
        return None


def poll_until_complete(session_token, clip_id, timeout=180):
    """Poll Suno API until a clip status is 'complete'. Returns audio_url or None."""
    if not session_token or not clip_id:
        return None
    headers = {"Authorization": f"Bearer {session_token}"}
    for i in range(timeout // 5):
        time.sleep(5)
        try:
            r = requests.get(
                f"https://studio-api.prod.suno.com/api/clip/{clip_id}/",
                headers=headers,
                timeout=10,
            )
            if r.status_code == 200 and r.json().get("status") == "complete":
                return r.json().get("audio_url", "")
        except Exception:
            pass
    return None


def download_mp3(audio_url, output_path):
    """Download an MP3 from a Suno audio URL. Returns True on success."""
    if not audio_url:
        return False
    try:
        resp = requests.get(audio_url, timeout=120, stream=True)
        if resp.status_code == 200:
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)
            size_kb = os.path.getsize(output_path) // 1024
            logger.info(f"Downloaded: {os.path.basename(output_path)} ({size_kb}KB)")
            return True
    except Exception as e:
        logger.warning(f"download_mp3: {e}")
    return False


def get_and_download(page, browser_context, output_path, timeout=180):
    """Full download pipeline: find clip → poll → download. Returns True on success."""
    session_token = get_session_token(browser_context)
    clip_id = find_latest_clip_id(page)
    if not clip_id:
        return False
    audio_url = poll_until_complete(session_token, clip_id, timeout)
    return download_mp3(audio_url, output_path)
