"""tut_run.py — Proven Suno cover pipeline (repurposed from hymnmania's working flow).

Key innovations from hymnmania:
- launch_persistent_context (no CDP needed)
- Clerk.session.getToken() for auth
- file chooser upload (not hidden input)
- Feed polling for clip discovery
- Old + new feed diff for cover detection
"""
import os
import sys
import time
import requests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Config ──
ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(ROOT)
RENDERED_DIR = os.path.join(BASE, "rendered_wav")
OUTPUT_DIR = os.path.join(BASE, "suno_generated")
USER_DIR = os.path.join(os.environ["USERPROFILE"], ".edge-tut-runner")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(RENDERED_DIR, exist_ok=True)

SUNO_API = "https://studio-api.prod.suno.com"

SONG = "twinkle_twinkle"
LYRICS = "Twinkle twinkle little star, how I wonder what you are. Up above the world so high, like a diamond in the sky. Twinkle twinkle little star, how I wonder what you are."

GENRES = {
    "psytrance": "full-on psytrance, 145bpm, rolling bassline, euphoric melodic, festival energy",
    "goa": "forest goa trance, 138bpm, dark atmospheric, nature sounds, forest spirits",
    "hardstyle": "hardstyle, 150bpm, hard kick, orchestral sweeps, euphoric climax",
    "happy_hardcore": "happy hardcore, 170bpm, uplifting piano, pitched vocals, energetic",
    "brostep": "brostep dubstep, 140bpm, massive drops, growling wobbles, aggressive",
    "dnb": "drum and bass, 174bpm, amen breaks, liquid atmospheres, deep sub-bass",
    "jcore": "japanese hardcore techno, 185bpm, anime melodies, fast kicks",
    "berlin": "berlin techno, 135bpm, minimal driving, hypnotic repetition, warehouse",
    "detroit": "detroit techno, 128bpm, deep analog synths, soulful chord stabs",
    "house": "detroit house, 125bpm, soulful grooves, deep basslines, jazzy chords",
}
SPEEDS = [0.5, 1.0, 2.5, 5.0]
VOCAL_MODES = ["instrumental", "lyrics"]


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=USER_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--disable-features=TranslateUI"],
            no_viewport=True,
        )
        page = ctx.new_page()
        page.goto("https://suno.com/create")
        time.sleep(5)

        # Wait for login
        print("Waiting for login...")
        token = None
        for attempt in range(120):
            try:
                token = page.evaluate("(async function(){try{return await Clerk.session.getToken()}catch(e){return null}})()")
            except:
                pass
            if token and len(str(token)) > 100:
                print(f"Logged in! Token: {len(str(token))} chars\n")
                break
            time.sleep(3)
            if attempt == 40:
                print("  Still waiting...")
        else:
            print("TIMEOUT — not logged in")
            ctx.close()
            return

        headers = {"Authorization": f"Bearer {token}"}

        # Build job list
        jobs = []
        for genre_slug, genre_desc in GENRES.items():
            for speed in SPEEDS:
                for vocal in VOCAL_MODES:
                    out = os.path.join(OUTPUT_DIR, f"{SONG}_{genre_slug}_speed_{str(speed).replace('.', '_')}_{vocal}.mp3")
                    if not os.path.exists(out):
                        wav = os.path.join(RENDERED_DIR, f"{SONG}_speed_{str(speed).replace('.', '_')}.wav")
                        upload_wav = wav
                        if speed == 5.0:
                            fallback = os.path.join(RENDERED_DIR, f"{SONG}_speed_1_0.wav")
                            if os.path.exists(fallback):
                                upload_wav = fallback
                        jobs.append((genre_slug, genre_desc, speed, vocal, out, upload_wav))

        total = len(jobs)
        print(f"Jobs: {total} ({len(GENRES)} genres × {len(SPEEDS)} speeds × {len(VOCAL_MODES)} modes)")

        for idx, (genre_slug, genre_desc, speed, vocal, out_mp3, wav_path) in enumerate(jobs):
            print(f"\n[{idx+1}/{total}] {genre_slug} @ {speed}x [{vocal}]")

            # Step 1: Upload WAV → generate base song
            page.goto("https://suno.com/create")
            time.sleep(6)

            # Click Add Audio
            page.evaluate("""Array.from(document.querySelectorAll('button')).find(x =>
                (x.getAttribute('aria-label') || '').includes('Add audio')
            )?.click()""")
            time.sleep(3)

            # Click "Browse, upload, or record audio" text
            page.evaluate("""Array.from(document.querySelectorAll('*')).find(e =>
                e.offsetParent !== null && e.textContent.trim() === 'Browse, upload, or record audio'
            )?.click()""")
            time.sleep(2)

            # Upload via file chooser
            with page.expect_file_chooser(timeout=15000) as fc_info:
                page.evaluate("document.querySelector('input[type=file]')?.click()")
            fc_info.value.set_files(wav_path)
            time.sleep(5)
            print("  Uploaded")

            # Handle Identify/Describe modals
            upload_ok = False
            for i in range(45):
                time.sleep(2)
                try:
                    body = page.evaluate("document.body.innerText.toLowerCase().substring(0,1000)")
                except:
                    break

                if "identify" in body:
                    page.evaluate("""(() => {
                        var opts = Array.from(document.querySelectorAll('span,p,div,label,button'))
                            .filter(e => e.offsetParent !== null && /full song|instrumental/i.test(e.textContent || ''));
                        opts.forEach(e => e.click());
                        setTimeout(() => {
                            var cb = Array.from(document.querySelectorAll('button'))
                                .find(b => b.offsetParent !== null && b.textContent.trim() === 'Continue');
                            if (cb) cb.click();
                        }, 500);
                    })()""")
                    print("  Identify")
                elif "describe" in body and "identify" not in body:
                    page.evaluate(f"""(() => {{
                        var tas = Array.from(document.querySelectorAll('textarea'));
                        var ns = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set;
                        var ta = tas.find(t => t.offsetParent !== null);
                        if (ta) {{ ns.call(ta, '{SONG}'); ta.dispatchEvent(new Event('input', {{bubbles:true}})); }}
                        setTimeout(() => {{ var cb = Array.from(document.querySelectorAll('button'))
                            .find(b => b.offsetParent !== null && b.textContent.trim() === 'Continue');
                            if (cb) cb.click(); }}, 500);
                    }})()""")
                    print("  Describe")
                elif "matches an existing recording" in body or "copyright" in body:
                    print("  REJECTED (copyright)")
                    break
                else:
                    is_modal = page.evaluate("!!Array.from(document.querySelectorAll('span,p,div,label,button,h2')).find(x => /identify|describe/i.test(x.textContent || ''))")
                    if not is_modal:
                        print("  Upload complete")
                        upload_ok = True
                        break

            if not upload_ok:
                continue

            # Find uploaded clip in feed
            upload_clip_id = None
            for _ in range(15):
                time.sleep(3)
                r = requests.get(f"{SUNO_API}/api/feed/?limit=10", headers=headers)
                if r.status_code == 200:
                    clips = r.json() if isinstance(r.json(), list) else r.json().get("clips", [])
                    for c in clips:
                        if c.get("title", "").lower() in (SONG, "hymn") or "upload" in str(c.get("type","")):
                            upload_clip_id = c.get("id")
                            break
                    if upload_clip_id:
                        break

            if not upload_clip_id:
                # Fallback: use most recent clip
                r = requests.get(f"{SUNO_API}/api/feed/?limit=5", headers=headers)
                if r.status_code == 200:
                    clips = r.json() if isinstance(r.json(), list) else r.json().get("clips", [])
                    for c in clips:
                        if c.get("model_name") in (None, "chirp-upload", "chirp-chirp"):
                            upload_clip_id = c.get("id")
                            break

            if not upload_clip_id:
                print("  Could not find upload clip!")
                continue

            print(f"  Clip: {upload_clip_id[:12]}...")

            # Step 2: Create Cover
            page.goto(f"https://suno.com/song/{upload_clip_id}")
            time.sleep(6)

            # Find and click cover/remix button
            for attempt in range(15):
                time.sleep(2)
                result = page.evaluate("""(() => {
                    var btns = Array.from(document.querySelectorAll('button, [role=\"button\"], a'))
                        .filter(x => x.offsetParent !== null);
                    var pats = ['create cover', 'cover song', 'make cover', 'cover this', 'remix'];
                    for (var p of pats) {
                        var b = btns.find(x => (x.textContent || '').toLowerCase().includes(p) || (x.getAttribute('aria-label') || '').toLowerCase().includes(p));
                        if (b) { b.click(); return 'clicked:' + p; }
                    }
                    return 'not_found';
                })()""")
                if result and result.startswith("clicked:"):
                    print(f"  Cover: {result}")
                    time.sleep(4)
                    break

            # Set style with genre, v5.5 model, cover tag
            style_text = f"{genre_desc} cover of {SONG} childrens nursery rhyme v5.5 cover"
            if vocal == "lyrics":
                style_text = f"{genre_desc} cover of {SONG} — sing: {LYRICS} v5.5 cover"

            page.evaluate(f"""(() => {{
                var tas = Array.from(document.querySelectorAll('textarea'));
                var ns = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set;
                if (tas.length > 0) {{ ns.call(tas[0], '{genre_desc}'); tas[0].dispatchEvent(new Event('input',{{bubbles:true}})); }}
                if (tas.length > 1) {{ ns.call(tas[1], '{style_text}'); tas[1].dispatchEvent(new Event('input',{{bubbles:true}})); }}
            }})()""")
            time.sleep(2)
            print(f"  Style: {style_text[:80]}...")

            # Snapshot existing feed IDs
            existing_ids = set()
            r = requests.get(f"{SUNO_API}/api/feed/?limit=10", headers=headers)
            if r.status_code == 200:
                clips = r.json() if isinstance(r.json(), list) else r.json().get("clips", [])
                existing_ids = {c["id"] for c in clips}

            # Click Create
            page.evaluate("""(() => {
                var btn = Array.from(document.querySelectorAll('button'))
                    .find(x => x.offsetParent !== null && (
                        (x.getAttribute('aria-label') || '').toLowerCase().includes('create') ||
                        (x.textContent || '').toLowerCase().trim() === 'create'
                    ));
                if (btn) btn.click();
            })()""")
            print("  Create clicked")
            time.sleep(15)

            # Poll for new clips
            found = []
            for _ in range(60):
                time.sleep(3)
                r = requests.get(f"{SUNO_API}/api/feed/?limit=10", headers=headers)
                if r.status_code == 200:
                    clips = r.json() if isinstance(r.json(), list) else r.json().get("clips", [])
                    for c in clips:
                        cid = c.get("id")
                        if cid and cid not in existing_ids and cid not in [fc["id"] for fc in found]:
                            found.append(c)
                    if len(found) >= 2:
                        break

            if not found:
                print("  No new clips found!")
                continue

            # Download
            for vi, clip in enumerate(found[:2]):
                vid = clip["id"]
                label = ["A", "B"][vi]
                for i in range(80):
                    time.sleep(3)
                    r2 = requests.get(f"{SUNO_API}/api/clip/{vid}/", headers=headers)
                    if r2.status_code == 200:
                        d = r2.json()
                        if d.get("status") == "complete" and d.get("audio_url"):
                            dl = requests.get(d["audio_url"], timeout=120, stream=True)
                            with open(out_mp3, "wb") as f:
                                for chunk in dl.iter_content(65536):
                                    f.write(chunk)
                            dur = d.get("metadata", {}).get("duration", "?")
                            tags = d.get("metadata", {}).get("tags", "")
                            model = d.get("metadata", {}).get("model_version", "?")
                            sz = os.path.getsize(out_mp3) // 1024
                            print(f"  DOWNLOADED {label}: {sz}KB | {dur}s | {model} | {tags}")
                            break
                        elif d.get("status") in ("error", "failed"):
                            break

            time.sleep(2)

        ctx.close()
        print("\n=== DONE ===")


if __name__ == "__main__":
    main()
