"""tut_kling.py — Kling AI free tier video generator for TurntUpToddler.

Kling free tier: 66 credits/month, generates videos from text or image+text.
API base: https://api.klingai.com (v1)

Set KLING_API_KEY in .env. Sign up at https://klingai.com
"""
import os
import sys
import time
import requests
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("tut_kling")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO_DIR = os.path.join(BASE, "videos")
MP3_DIR = os.path.join(BASE, "suno_generated")

KLING_API = "https://api.klingai.com/v1"
KLING_KEY = os.environ.get("KLING_API_KEY", "")


def kling_headers():
    return {
        "Authorization": f"Bearer {KLING_KEY}",
        "Content-Type": "application/json",
    }


def create_text_to_video(prompt, duration="5", model="kling-v1"):
    """Create a video from text prompt. Returns task_id."""
    resp = requests.post(
        f"{KLING_API}/videos/text2video",
        json={
            "model_name": model,
            "prompt": prompt,
            "duration": duration,
            "mode": "std",
        },
        headers=kling_headers(),
        timeout=30,
    )
    if resp.status_code == 200:
        data = resp.json()
        return data.get("data", {}).get("task_id")
    logger.warning(f"Kling create error: {resp.status_code} {resp.text[:200]}")
    return None


def poll_task(task_id, timeout_minutes=15):
    """Poll Kling task until complete. Returns video_url or None."""
    for i in range(timeout_minutes * 6):
        time.sleep(10)
        resp = requests.get(
            f"{KLING_API}/videos/text2video/{task_id}",
            headers=kling_headers(),
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("data", {}).get("task_status", "")
            if status == "succeed":
                videos = data.get("data", {}).get("task_result", {}).get("videos", [])
                if videos:
                    return videos[0].get("url")
            elif status == "failed":
                logger.warning(f"Kling task failed: {data.get('data',{}).get('task_status_msg','')}")
                return None
            logger.info(f"  Kling status: {status} ({(i+1)*10}s)")
    return None


def download_video(video_url, output_path):
    """Download a video from URL."""
    resp = requests.get(video_url, timeout=120, stream=True)
    if resp.status_code == 200:
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        return True
    return False


def generate_video_for_song(mp3_path, song, genre_slug, speed, vocal_mode):
    """Generate a Kling video for a specific song/MP3."""
    if not KLING_KEY:
        logger.error("Set KLING_API_KEY in .env")
        return None

    song_title = song.replace("_", " ").title()
    genre_name = genre_slug.replace("_", " ")

    video_name = os.path.basename(mp3_path).replace(".mp3", ".mp4")
    video_path = os.path.join(VIDEO_DIR, video_name)
    if os.path.exists(video_path):
        logger.info(f"SKIP: {video_name}")
        return video_path

    # Build prompt from metadata
    prompt = (
        f"Colorful animated music video for children: "
        f"{song_title} nursery rhyme as {genre_name} dance music. "
        f"Fun 3D cartoon characters, bright colors, magical sparkles, "
        f"dancing animals, rainbow lights, musical notes floating, "
        f"playful and energetic, suitable for toddlers and kids, "
        f"high quality animation, Pixar-style rendering"
    )

    logger.info(f"  Kling: {song}/{genre_slug}/{speed}x [{vocal_mode}]")
    task_id = create_text_to_video(prompt)
    if not task_id:
        return None

    logger.info(f"  Task: {task_id}")
    video_url = poll_task(task_id)
    if video_url and download_video(video_url, video_path):
        logger.info(f"  Video: {video_name} ({os.path.getsize(video_path)//1024}KB)")
        return video_path
    return None


def main():
    parser = argparse.ArgumentParser(description="TUT Kling Video Generator")
    parser.add_argument("--song", help="Song name (e.g. twinkle_twinkle)")
    parser.add_argument("--all", action="store_true", help="Generate videos for all MP3s")
    args = parser.parse_args()

    if not KLING_KEY:
        logger.error("Set KLING_API_KEY environment variable")
        return

    os.makedirs(VIDEO_DIR, exist_ok=True)

    if args.all:
        mp3s = sorted([f for f in os.listdir(MP3_DIR) if f.endswith(".mp3")])
        logger.info(f"Found {len(mp3s)} MP3s for video generation")
        for mp3 in mp3s:
            mp3_path = os.path.join(MP3_DIR, mp3)
            # Parse song_genre_speed_vocal from filename
            base = mp3.replace(".mp3", "")
            parts = base.split("_")
            if "speed" in base:
                sp_idx = [i for i, p in enumerate(parts) if p == "speed"]
                if sp_idx:
                    song = "_".join(parts[: sp_idx[0] - 1])
                    genre = parts[sp_idx[0] - 1]
                    speed = float(parts[sp_idx[0] + 1])
                    vocal = parts[-1] if len(parts) > sp_idx[0] + 1 else "instrumental"
                    generate_video_for_song(mp3_path, song, genre, speed, vocal)
    elif args.song:
        # Generate for all MP3s matching song
        for f in os.listdir(MP3_DIR):
            if f.startswith(args.song) and f.endswith(".mp3"):
                mp3_path = os.path.join(MP3_DIR, f)
                base = f.replace(".mp3", "")
                parts = base.split("_")
                if "speed" in base:
                    sp_idx = [i for i, p in enumerate(parts) if p == "speed"]
                    if sp_idx:
                        song = "_".join(parts[: sp_idx[0] - 1])
                        genre = parts[sp_idx[0] - 1]
                        speed = float(parts[sp_idx[0] + 1])
                        vocal = parts[-1] if len(parts) > sp_idx[0] + 1 else "instrumental"
                        generate_video_for_song(mp3_path, song, genre, speed, vocal)
    else:
        print("Usage: python tut_kling.py --song twinkle_twinkle  OR  --all")


if __name__ == "__main__":
    main()
