"""MilkDrop visualizer using butterchurn (JS) via Playwright."""

import os
import sys
import subprocess
import glob
import time
import base64
import json

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ["PYTHONIOENCODING"] = "utf-8"
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.abspath(__file__))
FFMPEG = os.path.join(ROOT, "hymn_remaker", "bin", "ffmpeg.exe")
GENERATED_DIR = os.path.join(ROOT, "generated")

# butterchurn CDN
BUTTERCHURN_CDN = (
    "https://cdn.jsdelivr.net/npm/butterchurn@2.6.11/lib/butterchurn.min.js"
)
PRESETS_CDN = "https://cdn.jsdelivr.net/npm/butterchurn-presets@2.5.4/lib/butterchurnPresets.min.js"


def render_milkdrop(audio_path, output_path, title, preset_name=None, preset_list=None):
    """Render a MilkDrop visualization using butterchurn in the browser."""
    audio_abs = os.path.abspath(audio_path)
    with open(audio_abs, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode()

    html = f"""<!DOCTYPE html>
<html><body style="margin:0;background:#000">
<canvas id="canvas" width="1920" height="1080"></canvas>
<audio id="audio" preload="auto"></audio>
<script src="{BUTTERCHURN_CDN}"></script>
<script src="{PRESETS_CDN}"></script>
<script>
const canvas = document.getElementById('canvas');
const audio = document.getElementById('audio');
const ctx = canvas.getContext('2d');

// Decode audio
const binary = atob({json.dumps(audio_b64)});
const bytes = new Uint8Array(binary.length);
for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
const blob = new Blob([bytes], {{type: 'audio/mpeg'}});
const url = URL.createObjectURL(blob);

audio.src = url;
audio.play();

// Initialize butterchurn
const visualizer = butterchurn.createVisualizer(ctx, canvas, {{
    width: 1920, height: 1080, meshWidth: 64, meshHeight: 48,
    pixelRatio: 1, textureRatio: 1,
}});

// Load preset
const presets = butterchurnPresets.getPresets();
const keys = Object.keys(presets);
let pn = {json.dumps(preset_name or "")};
if (!pn || !presets[pn]) pn = keys[Math.floor(Math.random() * keys.length)];
const preset = presets[pn];
visualizer.loadPreset(preset, 0.0);

// Render loop
let frame = 0;
function render() {{
    if (!audio.paused && !audio.ended) {{
        visualizer.render();
        // Store frame count for capture
        window.__frameCount = frame++;
    }}
    requestAnimationFrame(render);
}}
render();

// Report preset name and frame count periodically
setInterval(() => {{
    document.title = JSON.stringify({{preset: pn, frames: window.__frameCount || 0}});
}}, 1000);
</script></body></html>"""

    html_path = os.path.join(ROOT, "temp_video", "butterchurn.html")
    os.makedirs(os.path.dirname(html_path), exist_ok=True)
    with open(html_path, "w") as f:
        f.write(html)

    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = browser.contexts[0].pages[0]
        page.goto("file://" + html_path.replace("\\", "/"))
        print("  butterchurn loaded, playing audio...")
        page.wait_for_timeout(10000)

        # Capture frames at intervals
        frames_dir = os.path.join(ROOT, "temp_video", "frames")
        os.makedirs(frames_dir, exist_ok=True)

        duration = 120  # max
        fps = 30
        total_frames = duration * fps
        frame_interval = 1.0 / fps

        for i in range(min(total_frames, 900)):  # 30 seconds max for testing
            time.sleep(frame_interval)
            screenshot = page.screenshot(full_page=False)
            with open(os.path.join(frames_dir, f"frame_{i:05d}.png"), "wb") as f:
                f.write(screenshot)
            if i % 30 == 0:
                print(f"  Captured {i} frames...")

        # Encode to video
        subprocess.run(
            [
                FFMPEG,
                "-y",
                "-framerate",
                str(fps),
                "-i",
                os.path.join(frames_dir, "frame_%05d.png"),
                "-i",
                audio_abs,
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-pix_fmt",
                "yuv420p",
                "-shortest",
                output_path,
            ],
            capture_output=True,
            timeout=300,
        )

        import shutil

        shutil.rmtree(os.path.join(ROOT, "temp_video"), ignore_errors=True)

        if os.path.exists(output_path):
            print(f"  Video: {os.path.getsize(output_path) // 1024 // 1024}MB")
        browser.close()


if __name__ == "__main__":
    songs = sorted(glob.glob(os.path.join(GENERATED_DIR, "*_generated.mp3")))
    if not songs:
        print("No songs")
        exit()

    song = songs[0]
    name = os.path.basename(song).replace("_generated.mp3", "").replace("_", " ")
    out = os.path.join(GENERATED_DIR, f"{name.replace(' ', '_')}_butterchurn.mp4")

    print(f"Rendering MilkDrop via butterchurn: {name}")
    render_milkdrop(song, out, name)
