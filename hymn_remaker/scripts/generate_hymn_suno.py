"""TUT Batch: twinkle_twinkle — all 10 genres × 4 speeds × instrumental + lyrics = 80 tracks."""
import os
import time
import re
import requests
from playwright.sync_api import sync_playwright

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE, "suno_generated")
RENDER_DIR = os.path.join(BASE, "rendered_wav")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SONG = "twinkle_twinkle"
LYRICS = "Twinkle twinkle little star, how I wonder what you are. Up above the world so high, like a diamond in the sky. Twinkle twinkle little star, how I wonder what you are."
GENRES = [
    ("full-on psytrance, 145bpm, rolling bassline, euphoric melodic", "psytrance"),
    ("forest goa trance, 138bpm, dark atmospheric, nature sounds", "goa"),
    ("hardstyle, 150bpm, hard kick, orchestral sweeps, euphoric climax", "hardstyle"),
    ("happy hardcore, 170bpm, uplifting piano, pitched vocals", "happy_hardcore"),
    ("brostep dubstep, 140bpm, massive drops, growling wobbles", "brostep"),
    ("drum and bass, 174bpm, amen breaks, liquid atmospheres", "dnb"),
    ("japanese hardcore techno, 185bpm, anime melodies, fast kicks", "jcore"),
    ("berlin techno, 135bpm, minimal driving, hypnotic warehouse", "berlin"),
    ("detroit techno, 128bpm, deep analog synths, soulful stabs", "detroit"),
    ("detroit house, 125bpm, soulful grooves, deep basslines, jazzy", "house"),
]
SPEEDS = [0.5, 1.0, 2.5, 5.0]
VOCAL_MODES = ["instrumental", "lyrics"]
MAX_RETRIES = 2

with sync_playwright() as pw:
    browser = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = browser.contexts[0]
    # Close stale pages
    for p in ctx.pages[:]:
        try: p.close()
        except: pass
    page = ctx.new_page()

    # Show credits
    page.goto("https://suno.com/create", wait_until="domcontentloaded", timeout=30000)
    time.sleep(5)
    try: page.evaluate("document.querySelectorAll('[role=dialog]').forEach(d => d.remove())")
    except: pass
    try:
        body = page.inner_text("body")
        credits = re.search(r"([\d,]+)\s*Credits?", body)
        print(f"Credits: {credits.group(1) if credits else '?'}\n")
    except: pass

    count = 0
    total = len(GENRES) * len(SPEEDS) * len(VOCAL_MODES)

    for genre_prompt, genre_slug in GENRES:
        for speed in SPEEDS:
            for vocal_mode in VOCAL_MODES:
                # Build prompt
                if vocal_mode == "lyrics":
                    prompt = f"{genre_prompt} — sing these lyrics: {LYRICS}"
                else:
                    prompt = genre_prompt

                wav_file = f"{SONG}_speed_{str(speed).replace('.', '_')}.wav"
                wav_path = os.path.join(RENDER_DIR, wav_file)
                # 5.0x WAV is only ~2s — Suno rejects very short audio. Use 1.0x WAV.
                if speed == 5.0:
                    fallback = os.path.join(RENDER_DIR, f"{SONG}_speed_1_0.wav")
                    if os.path.exists(fallback):
                        wav_path = fallback
                out_mp3 = os.path.join(
                    OUTPUT_DIR,
                    f"{SONG}_{genre_slug}_speed_{str(speed).replace('.', '_')}_{vocal_mode}.mp3",
                )

                if os.path.exists(out_mp3):
                    continue
                if not os.path.exists(wav_path):
                    continue

                count += 1
                print(f"[{count}/{total}] {genre_slug:15s} @ {speed}x [{vocal_mode:12s}]", flush=True)

                for attempt in range(1, MAX_RETRIES + 1):
                    try: page.close()
                    except: pass
                    page = ctx.new_page()

                    # --- Upload flow ---
                    page.goto("https://suno.com/create", wait_until="domcontentloaded", timeout=30000)
                    time.sleep(6)
                    try: page.evaluate("document.querySelectorAll('[role=dialog]').forEach(d => d.remove())")
                    except: pass
                    time.sleep(2)

                    try: page.evaluate("document.querySelector('button[aria-label*=\"Add audio\"]')?.click()")
                    except: break
                    time.sleep(3)
                    try: page.locator('input[type="file"]').first.set_input_files(wav_path)
                    except: break
                    time.sleep(10)

                    for i in range(40):
                        time.sleep(2)
                        try: bt = page.inner_text("body").lower()
                        except: break
                        if "identify" in bt:
                            page.evaluate("""Array.from(document.querySelectorAll('button')).filter(b => b.offsetParent !== null && /full song|instrumental|cover/i.test(b.innerText || '')).forEach(b => b.click())""")
                            page.evaluate("""Array.from(document.querySelectorAll('button')).find(b => b.offsetParent !== null && (b.innerText || '').trim() === 'Continue')?.click()""")
                        elif "describe" in bt:
                            page.evaluate(f"""var tas = Array.from(document.querySelectorAll('textarea')).filter(t => t.offsetParent !== null);
                                if (tas.length > 0) {{ var ns = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                                ns.call(tas[tas.length-1], '{prompt}'); tas[tas.length-1].dispatchEvent(new Event('input', {{bubbles: true}})); }}""")
                            time.sleep(1)
                            page.evaluate("""Array.from(document.querySelectorAll('button')).find(b => b.offsetParent !== null && (b.innerText || '').trim() === 'Continue')?.click()""")
                        elif "style influence" in bt or "uploaded" in bt:
                            time.sleep(3)
                            break

                    time.sleep(3)
                    try: page.evaluate("""Array.from(document.querySelectorAll('[role=\"tab\"]')).find(t => (t.innerText || '').trim() === 'Advanced')?.click()""")
                    except: pass
                    time.sleep(2)
                    try: page.evaluate(f"""var tas = Array.from(document.querySelectorAll('textarea')).filter(t => t.offsetParent !== null);
                        if (tas.length >= 2) {{ var ns = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                        ns.call(tas[1], '{prompt}'); tas[1].dispatchEvent(new Event('input', {{bubbles: true}})); }}""")
                    except: pass
                    time.sleep(1)

                    created = "disabled"
                    for wi in range(20):
                        time.sleep(2)
                        try:
                            created = page.evaluate("""(() => { let btn = Array.from(document.querySelectorAll('button')).find(b => (b.innerText || '').includes('Create') && b.offsetParent !== null && !b.hasAttribute('disabled')); if (btn) { btn.click(); return 'clicked'; } return 'disabled'; })()""")
                            if created != "disabled": break
                        except: pass

                    if created == "disabled":
                        print(f"  retry {attempt} — Create disabled", flush=True)
                        continue

                    time.sleep(90)

                    # Download
                    st = ""
                    for c in ctx.cookies():
                        if c.get("name") == "__session": st = c.get("value", ""); break

                    try:
                        page.goto("https://suno.com/create", wait_until="domcontentloaded", timeout=30000)
                        time.sleep(5)
                        clips = re.findall(r"/song/([0-9a-f-]+)", page.content())
                        if clips and st:
                            cid = clips[-1]
                            for di in range(30):
                                try:
                                    r = requests.get(f"https://studio-api.prod.suno.com/api/clip/{cid}/", headers={"Authorization": f"Bearer {st}"}, timeout=10)
                                    if r.status_code == 200 and r.json().get("status") == "complete":
                                        url = r.json().get("audio_url", "")
                                        if url:
                                            resp = requests.get(url, timeout=120, stream=True)
                                            with open(out_mp3, "wb") as f:
                                                for chunk in resp.iter_content(chunk_size=65536): f.write(chunk)
                                            sz = os.path.getsize(out_mp3) // 1024
                                            print(f"  OK {sz}KB -> {os.path.basename(out_mp3)}", flush=True)
                                            break
                                except: pass
                                time.sleep(5)
                            break
                    except Exception as e:
                        print(f"  download error: {e}", flush=True)

                time.sleep(3)

    print(f"\nDone! {count} total generated", flush=True)
