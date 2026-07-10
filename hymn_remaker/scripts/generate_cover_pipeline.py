"""
Two-step cover pipeline: upload→generate (short) → Remix→Cover (full song).
Step 1 uses the reliable upload flow.
Step 2 navigates to the song page, clicks Remix→Cover, generates, downloads via feed API.
"""

import os
import time
import re
import requests
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.sync_api import sync_playwright

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE, "suno_generated")
RENDER_DIR = os.path.join(BASE, "rendered_wav")

SONG = "twinkle_twinkle"
GENRES = [
    (
        "full-on psytrance, 145bpm, rolling bassline, euphoric melodic, festival energy",
        "psytrance",
    ),
    (
        "forest goa trance, 138bpm, dark atmospheric, nature sounds, forest spirits",
        "goa",
    ),
]
SPEEDS = [0.5, 1.0, 2.5, 5.0]
MAX_RETRIES = 3


def get_session(ctx):
    for c in ctx.cookies():
        if c.get("name") == "__session":
            return c.get("value", "")
    return ""


def step1_upload_and_generate(page, ctx, wav_path, genre_prompt):
    """Upload WAV and generate a base song. Returns clip_id or None."""
    page.goto("https://suno.com/create", wait_until="domcontentloaded", timeout=30000)
    time.sleep(6)
    try:
        page.evaluate(
            "document.querySelectorAll('[role=dialog]').forEach(d => d.remove())"
        )
    except:
        pass

    # Click Add Audio
    try:
        page.evaluate(
            "document.querySelector('button[aria-label*=\"Add audio\"]')?.click()"
        )
    except:
        return None
    time.sleep(3)

    # Upload
    try:
        page.locator('input[type="file"]').first.set_input_files(wav_path)
    except:
        return None
    time.sleep(10)

    # Handle Identify/Describe flow
    for i in range(40):
        time.sleep(2)
        try:
            bt = page.inner_text("body").lower()
        except:
            break

        if "identify" in bt:
            try:
                page.evaluate("""Array.from(document.querySelectorAll('button')).filter(b =>
                    b.offsetParent !== null && /full song|instrumental|cover/i.test(b.innerText || '')
                ).forEach(b => b.click())""")
                page.evaluate("""Array.from(document.querySelectorAll('button')).find(b =>
                    b.offsetParent !== null && (b.innerText || '').trim() === 'Continue'
                )?.click()""")
            except:
                pass
        elif "describe" in bt:
            try:
                page.evaluate(f"""
                    var tas = Array.from(document.querySelectorAll('textarea')).filter(t => t.offsetParent !== null);
                    if (tas.length > 0) {{
                        var ns = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                        ns.call(tas[tas.length-1], '{genre_prompt}');
                        tas[tas.length-1].dispatchEvent(new Event('input', {{bubbles: true}}));
                    }}
                """)
                time.sleep(1)
                page.evaluate("""Array.from(document.querySelectorAll('button')).find(b =>
                    b.offsetParent !== null && (b.innerText || '').trim() === 'Continue'
                )?.click()""")
            except:
                pass
        elif "style influence" in bt or "uploaded" in bt:
            time.sleep(3)
            break

    time.sleep(3)
    # Switch to Advanced
    try:
        page.evaluate("""Array.from(document.querySelectorAll('[role="tab"]')).find(t =>
            (t.innerText || '').trim() === 'Advanced'
        )?.click()""")
    except:
        pass
    time.sleep(2)

    # Fill style
    try:
        page.evaluate(f"""
            var tas = Array.from(document.querySelectorAll('textarea')).filter(t => t.offsetParent !== null);
            if (tas.length >= 2) {{
                var ns = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                ns.call(tas[1], '{genre_prompt}');
                tas[1].dispatchEvent(new Event('input', {{bubbles: true}}));
            }}
        """)
    except:
        pass
    time.sleep(1)

    # Try Create
    for wi in range(20):
        time.sleep(2)
        try:
            created = page.evaluate("""(() => {
                let btn = Array.from(document.querySelectorAll('button')).find(b =>
                    (b.innerText || '').includes('Create') && b.offsetParent !== null && !b.hasAttribute('disabled')
                );
                if (btn) { btn.click(); return 'clicked'; }
                return 'disabled';
            })()""")
            if created != "disabled":
                break
        except:
            pass
    else:
        return None

    # Wait for generation
    time.sleep(60)

    # Get clip ID from page
    try:
        page.goto(
            "https://suno.com/create", wait_until="domcontentloaded", timeout=30000
        )
        time.sleep(5)
        clips = re.findall(r"/song/([0-9a-f-]+)", page.content())
        if clips:
            return clips[-1]
    except:
        pass
    return None


def step2_create_cover(page, ctx, upload_clip_id, genre_prompt, out_mp3):
    """Navigate to uploaded song → Remix → Cover → Generate → Download via feed."""
    try:
        page.goto(
            f"https://suno.com/song/{upload_clip_id}",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        time.sleep(6)
        page.evaluate(
            "document.querySelectorAll('[role=dialog]').forEach(d => d.remove())"
        )
        time.sleep(2)
    except:
        return False

    # Click Remix
    try:
        page.evaluate("""Array.from(document.querySelectorAll('button')).find(b =>
            b.offsetParent !== null && (b.innerText || '').trim() === 'Remix'
        )?.click()""")
        time.sleep(3)
    except:
        return False

    # Click Cover
    try:
        page.evaluate("""Array.from(document.querySelectorAll('button')).find(b =>
            b.offsetParent !== null && (b.innerText || '').trim() === 'Cover'
        )?.click()""")
        time.sleep(3)
    except:
        return False

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
    except:
        return False

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
    except:
        return False

    # Wait for cover to generate, then poll feed to download
    st = get_session(ctx)
    if not st:
        return False

    time.sleep(20)

    for wait_min in range(10):
        time.sleep(15)
        try:
            feed = requests.get(
                "https://studio-api.prod.suno.com/api/feed/?page=1",
                headers={"Authorization": f"Bearer {st}"},
                timeout=10,
            )
            if feed.status_code == 200:
                items = feed.json()
                for item in items:
                    item_id = item.get("id", "")
                    status = item.get("status", "")
                    audio_url = item.get("audio_url", "")
                    meta = item.get("metadata", {}) or {}
                    gen_type = meta.get("type", "") if isinstance(meta, dict) else ""

                    if status == "complete" and audio_url:
                        # Download it
                        resp = requests.get(audio_url, timeout=120, stream=True)
                        with open(out_mp3, "wb") as f:
                            for chunk in resp.iter_content(chunk_size=65536):
                                f.write(chunk)
                        if os.path.getsize(out_mp3) > 100000:  # At least 100KB
                            return True
        except:
            pass

    return False


# ====== MAIN ======
with sync_playwright() as pw:
    browser = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = browser.contexts[0]

    for p in ctx.pages[:]:
        try:
            p.close()
        except:
            pass

    page = ctx.new_page()

    for genre_prompt, genre_slug in GENRES:
        for speed in SPEEDS:
            ws = f"{SONG}_speed_{str(speed).replace('.', '_')}.wav"
            wp = os.path.join(RENDER_DIR, ws)
            out = os.path.join(
                OUTPUT_DIR,
                f"{SONG}_{genre_slug}_speed_{str(speed).replace('.', '_')}.mp3",
            )

            if os.path.exists(out):
                print(f"EXISTS: {os.path.basename(out)}", flush=True)
                continue
            if not os.path.exists(wp):
                print(f"MISS: {ws}", flush=True)
                continue

            print(f"\n=== {genre_slug} @ {speed}x ===", flush=True)

            # STEP 1: Upload + generate base clip
            upload_id = None
            for attempt in range(1, MAX_RETRIES + 1):
                print(f"  Step 1 (attempt {attempt}): upload...", flush=True)
                try:
                    page.close()
                except:
                    pass
                page = ctx.new_page()

                upload_id = step1_upload_and_generate(page, ctx, wp, genre_prompt)
                if upload_id:
                    print(f"  Upload done, clip={upload_id[:12]}...", flush=True)
                    break
                print("  Upload failed, retrying...", flush=True)

            if not upload_id:
                # Fallback: use 1.0x WAV for upload, then speed output with ffmpeg
                ws_fallback = f"{SONG}_speed_1_0.wav"
                wp_fallback = os.path.join(RENDER_DIR, ws_fallback)
                if speed != 1.0 and os.path.exists(wp_fallback):
                    print("  Step 1 fallback: using 1.0x WAV for upload", flush=True)
                    for attempt in range(1, MAX_RETRIES + 1):
                        print(
                            f"  Step 1 (attempt {attempt}): upload (fallback)...",
                            flush=True,
                        )
                        try:
                            page.close()
                        except:
                            pass
                        page = ctx.new_page()
                        upload_id = step1_upload_and_generate(
                            page, ctx, wp_fallback, genre_prompt
                        )
                        if upload_id:
                            print(
                                f"  Upload fallback done, clip={upload_id[:12]}...",
                                flush=True,
                            )
                            break
                if not upload_id:
                    print(f"  FAILED after {MAX_RETRIES} attempts", flush=True)
                    continue

            # STEP 2: Create Cover
            for attempt in range(1, MAX_RETRIES + 1):
                print(f"  Step 2 (attempt {attempt}): cover...", flush=True)
                try:
                    page.close()
                except:
                    pass
                page = ctx.new_page()

                if step2_create_cover(page, ctx, upload_id, genre_prompt, out):
                    size_kb = os.path.getsize(out) // 1024
                    print(
                        f"  COVER DOWNLOADED: {os.path.basename(out)} ({size_kb}KB)",
                        flush=True,
                    )
                    break
                print("  Cover failed, retrying...", flush=True)
            else:
                print(f"  Cover FAILED after {MAX_RETRIES} attempts", flush=True)

            time.sleep(5)

    print("\nALL DONE!", flush=True)
