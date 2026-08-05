"""tut_run.py — CDP-based Suno cover pipeline for top 5 children's songs.

Connects to YOUR already-logged-in Edge at http://127.0.0.1:9222.
Start Edge with: msedge.exe --remote-debugging-port=9222

Flow per track:
  1. Upload rendered WAV → generate base upload clip
  2. Navigate to song page → Create Cover
  3. Poll feed for new clips (diff against snapshot)
  4. Download completed MP3
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
os.makedirs(OUTPUT_DIR, exist_ok=True)

SUNO_API = "https://studio-api.prod.suno.com"
CDP_URL = "http://127.0.0.1:9222"

# Top 5 children's songs with full lyrics
SONGS = {
    "twinkle_twinkle": (
        "Twinkle twinkle little star, how I wonder what you are. "
        "Up above the world so high, like a diamond in the sky. "
        "Twinkle twinkle little star, how I wonder what you are."
    ),
    "mary_had_lamb": (
        "Mary had a little lamb, little lamb, little lamb. "
        "Mary had a little lamb, its fleece was white as snow. "
        "And everywhere that Mary went, Mary went, Mary went. "
        "Everywhere that Mary went, the lamb was sure to go."
    ),
    "row_row_boat": (
        "Row row row your boat, gently down the stream. "
        "Merrily merrily merrily merrily, life is but a dream. "
        "Row row row your boat, gently down the stream. "
        "If you see a crocodile, don't forget to scream."
    ),
    "itsy_bitsy": (
        "The itsy bitsy spider climbed up the water spout. "
        "Down came the rain and washed the spider out. "
        "Out came the sun and dried up all the rain. "
        "And the itsy bitsy spider climbed up the spout again."
    ),
    "old_macdonald": (
        "Old MacDonald had a farm, E-I-E-I-O. "
        "And on his farm he had a cow, E-I-E-I-O. "
        "With a moo moo here and a moo moo there, "
        "here a moo, there a moo, everywhere a moo moo. "
        "Old MacDonald had a farm, E-I-E-I-O."
    ),
}

GENRES = {
    "psytrance": "full-on psytrance, 145bpm, rolling bassline, euphoric melodic, festival energy",
    "goa": "forest goa trance, 138bpm, dark atmospheric, nature sounds, tribal drums, forest spirits",
    "hardstyle": "hardstyle, 150bpm, hard kick, screeches, orchestral sweeps, euphoric climax",
    "happy_hardcore": "happy hardcore, 170bpm, uplifting piano, pitched vocals, energetic kicks, euphoric",
    "brostep": "brostep dubstep, 140bpm, massive drops, growling wobbles, aggressive bass",
    "dnb": "drum and bass, 174bpm, amen breaks, liquid atmospheres, rolling bass, deep sub-bass",
    "jcore": "japanese hardcore techno, 185bpm, anime melodies, fast kicks, energetic",
    "berlin": "berlin techno, 135bpm, minimal driving, hypnotic repetition, warehouse reverb",
    "detroit": "detroit techno, 128bpm, deep analog synths, soulful chord stabs, machine soul",
    "house": "detroit house, 125bpm, soulful grooves, deep basslines, jazzy chords, warm pads",
}
SPEEDS = [0.5, 1.0, 2.5, 5.0]
VOCAL_MODES = ["instrumental", "lyrics"]

# Naming convention: {song}_{genre}_speed_{speed}_{vocal}.mp3
# Example: twinkle_twinkle_psytrance_speed_2_5_lyrics.mp3


def get_clerk_token(page):
    """Extract Clerk session token from logged-in page. Waits up to 10 min."""
    print("  Waiting for login... (check the Edge browser window!)")
    for attempt in range(300):
        try:
            token = page.evaluate(
                "(async ()=>{try{return await Clerk.session.getToken()}catch(e){return null}})()"
            )
            if token and len(str(token)) > 100:
                return token
        except Exception:
            pass
        time.sleep(2)
        if attempt == 15:
            print("  Still waiting... (are you logged in on suno.com/create?)")
        elif attempt == 50:
            print("  Still waiting...")
        elif attempt == 150:
            return None
    return None


def get_suno_cookie(page):
    """Extract Suno session cookie from CDP page."""
    try:
        token = page.evaluate(
            "(async ()=>{try{return await Clerk.session.getToken()}catch(e){return null}})()"
        )
        return token
    except:
        return None


def handle_identify_modal(page):
    """Handle the 'identify' modal: select full song + instrumental, click Continue."""
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


def handle_describe_modal(page, song_name):
    """Fill the describe textarea and click Continue."""
    page.evaluate(f"""(() => {{
        var tas = Array.from(document.querySelectorAll('textarea'));
        var ns = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set;
        var ta = tas.find(t => t.offsetParent !== null);
        if (ta) {{ ns.call(ta, '{song_name}'); ta.dispatchEvent(new Event('input', {{bubbles:true}})); }}
        setTimeout(() => {{ var cb = Array.from(document.querySelectorAll('button'))
            .find(b => b.offsetParent !== null && b.textContent.trim() === 'Continue');
            if (cb) cb.click(); }}, 500);
    }})()""")


def wait_for_upload_done(page, timeout=180, song_name="childrens song"):
    """Wait for Suno upload modal, handle it, return True when done.
    THE MODAL IS IN A REACT PORTAL. Use querySelectorAll, NOT innerText."""
    for i in range(timeout // 2):
        time.sleep(2)
        try:
            # Check modal via element queries (React portal — invisible to innerText)
            uploading = page.evaluate(
                "!!Array.from(document.querySelectorAll('*')).find(e => e.offsetParent !== null && /Uploading Clip/i.test(e.textContent || ''))"
            )
            has_opts = page.evaluate(
                "!!Array.from(document.querySelectorAll('*')).find(e => e.offsetParent !== null && /Describes the contents|Full Song.*Song Demo|Song Demo.*Voice/i.test(e.textContent || ''))"
            )
        except Exception:
            continue

        if i == 0:
            print(f"  Modal: uploading={uploading} options={has_opts}")

        # Handle type options modal AS SOON as it appears (before timeout)
        if has_opts:
            print("  Handling upload modal...")
            # Click Full Song
            page.evaluate("""Array.from(document.querySelectorAll('span,p,div,label,button,[role=radio]')).filter(e=>e.offsetParent!==null&&/full song/i.test(e.textContent||"")).forEach(e=>e.click())""")
            time.sleep(1)
            # Fill description
            page.evaluate(f"""(()=>{{var tas=Array.from(document.querySelectorAll('textarea'));var ns=Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set;var ta=tas.find(t=>t.offsetParent!==null);if(ta){{ns.call(ta,'{song_name}');ta.dispatchEvent(new Event('input',{{bubbles:true}}));}}}})()""")
            time.sleep(1)
            # Click Continue
            page.evaluate("""Array.from(document.querySelectorAll('button')).find(b=>b.offsetParent!==null&&/continue/i.test(b.textContent.trim()))?.click()""")
            print("  Modal handled")
            time.sleep(5)
            return True

        if not uploading and not has_opts:
            # No upload in progress, no modal — probably back on create page
            try:
                body = page.evaluate("document.body.innerText.substring(0,1000).toLowerCase()")
            except Exception:
                body = ""
            if "song description" in body or "add audio" in body:
                return True
            if "matches an existing recording" in body or "copyright" in body:
                print("  REJECTED")
                return False

        if i == 30 and uploading:
            print(f"  Upload taking a while... ({i*2}s)")

    return False


def find_upload_clip(headers, song_name):
    """Find the most recent upload clip for a song in the feed."""
    for _ in range(15):
        time.sleep(3)
        try:
            r = requests.get(
                f"{SUNO_API}/api/feed/?limit=20", headers=headers, timeout=15
            )
            if r.status_code == 200:
                data = (
                    r.json()
                    if isinstance(r.json(), list)
                    else r.json().get("clips", [])
                )
                for c in data:
                    title = (c.get("title") or "").lower()
                    if song_name.lower() in title or "childrens song" in title:
                        return c.get("id")
        except:
            pass
    return None


def find_cover_button(page):
    """Find and click any cover/remix button on the song page. Returns True if clicked."""
    for attempt in range(15):
        time.sleep(2)
        result = page.evaluate("""(() => {
            var btns = Array.from(document.querySelectorAll('button, [role="button"], a'))
                .filter(x => x.offsetParent !== null);
            var pats = ['create cover', 'cover song', 'make cover', 'cover this', 'remix'];
            for (var p of pats) {
                var b = btns.find(x => (x.textContent || '').toLowerCase().includes(p) ||
                    (x.getAttribute('aria-label') || '').toLowerCase().includes(p));
                if (b) { b.click(); return 'clicked:' + p; }
            }
            return 'not_found';
        })()""")
        if result and result.startswith("clicked:"):
            print(f"  Cover: {result}")
            time.sleep(4)
            return True
    return False


def fill_cover_style(page, genre_desc, style_text):
    """Fill the style/prompt textareas in the cover dialog."""
    page.evaluate(f"""(() => {{
        var tas = Array.from(document.querySelectorAll('textarea'));
        var ns = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set;
        if (tas.length > 0) {{ ns.call(tas[0], '{genre_desc}');
            tas[0].dispatchEvent(new Event('input',{{bubbles:true}})); }}
        if (tas.length > 1) {{ ns.call(tas[1], '{style_text}');
            tas[1].dispatchEvent(new Event('input',{{bubbles:true}})); }}
    }})()""")


def click_create(page):
    """Click the Create button to submit the cover."""
    page.evaluate("""(() => {
        var btn = Array.from(document.querySelectorAll('button'))
            .find(x => x.offsetParent !== null && (
                (x.getAttribute('aria-label') || '').toLowerCase().includes('create') ||
                (x.textContent || '').toLowerCase().trim() === 'create'
            ));
        if (btn) btn.click();
    })()""")


def poll_new_clips(headers, existing_ids, max_wait=180):
    """Poll feed for new clip IDs not in existing_ids. Returns list of new clips."""
    found = []
    for _ in range(max_wait // 3):
        time.sleep(3)
        try:
            r = requests.get(
                f"{SUNO_API}/api/feed/?limit=20", headers=headers, timeout=15
            )
            if r.status_code == 200:
                data = (
                    r.json()
                    if isinstance(r.json(), list)
                    else r.json().get("clips", [])
                )
                for c in data:
                    cid = c.get("id")
                    if (
                        cid
                        and cid not in existing_ids
                        and cid not in [fc["id"] for fc in found]
                    ):
                        found.append(c)
                if len(found) >= 2:
                    return found
        except:
            pass
    return found if found else None


def download_clip(headers, vid, out_mp3):
    """Poll clip status and download when complete. Returns True on success."""
    for _ in range(80):
        time.sleep(3)
        try:
            r = requests.get(f"{SUNO_API}/api/clip/{vid}/", headers=headers, timeout=15)
            if r.status_code == 200:
                d = r.json()
                if d.get("status") == "complete" and d.get("audio_url"):
                    dl = requests.get(d["audio_url"], timeout=120, stream=True)
                    with open(out_mp3, "wb") as f:
                        for chunk in dl.iter_content(65536):
                            f.write(chunk)
                    dur = d.get("metadata", {}).get("duration", "?")
                    tags = d.get("metadata", {}).get("tags", "")
                    model = d.get("metadata", {}).get("model_version", "?")
                    sz = os.path.getsize(out_mp3) // 1024
                    print(f"  DOWNLOADED: {sz}KB | {dur}s | {model} | {tags}")
                    return True
                elif d.get("status") in ("error", "failed"):
                    return False
        except:
            pass
    return False


def main():
    from playwright.sync_api import sync_playwright
    import logging

    logging.basicConfig(level=logging.WARNING)

    print("Connecting to Edge CDP at", CDP_URL)
    print("Make sure Edge is running with: --remote-debugging-port=9222\n")

    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(CDP_URL)
        page = browser.contexts[0].pages[0]
        print(f"Connected to: {page.url[:60]}...")

        # Extract auth token
        page.goto("https://suno.com/create")
        time.sleep(5)

        print("Getting auth token...")
        token = get_clerk_token(page)
        if not token:
            print("FAILED: No Clerk token. Are you logged into Suno?")
            browser.close()
            return
        print(f"Token OK: {len(str(token))} chars\n")
        headers = {"Authorization": f"Bearer {token}"}

        # Build job queue
        jobs = []
        for song_name, lyrics in SONGS.items():
            for genre_slug, genre_desc in GENRES.items():
                for speed in SPEEDS:
                    for vocal in VOCAL_MODES:
                        speed_str = str(speed).replace(".", "_")
                        out_mp3 = os.path.join(
                            OUTPUT_DIR,
                            f"{song_name}_{genre_slug}_speed_{speed_str}_{vocal}.mp3",
                        )
                        if os.path.exists(out_mp3):
                            continue
                        wav_path = os.path.join(
                            RENDERED_DIR, f"{song_name}_speed_{speed_str}.wav"
                        )
                        if not os.path.exists(wav_path):
                            # Fallback: use 1.0x speed WAV for 5.0x renders
                            if speed == 5.0:
                                wav_path = os.path.join(
                                    RENDERED_DIR, f"{song_name}_speed_1_0.wav"
                                )
                            if not os.path.exists(wav_path):
                                continue
                        jobs.append(
                            (
                                song_name,
                                lyrics,
                                genre_slug,
                                genre_desc,
                                speed,
                                vocal,
                                out_mp3,
                                wav_path,
                            )
                        )

        total = len(jobs)
        print(f"Jobs: {total}")
        print(
            f"  {len(SONGS)} songs × {len(GENRES)} genres × {len(SPEEDS)} speeds × {len(VOCAL_MODES)} modes"
        )
        print(
            f"  Already done: {len(SONGS) * len(GENRES) * len(SPEEDS) * len(VOCAL_MODES) - total}\n"
        )

        if not jobs:
            print("All tracks already generated!")
            browser.close()
            return

        for idx, (
            song,
            lyrics,
            genre_slug,
            genre_desc,
            speed,
            vocal,
            out_mp3,
            wav,
        ) in enumerate(jobs):
            print(f"\n[{idx + 1}/{total}] {song} | {genre_slug} | {speed}x | {vocal}")

            # ── Step 1: Upload WAV ──
            try:
                page.goto("https://suno.com/create", timeout=30000)
            except Exception:
                print("  Navigation timeout, retrying...")
                time.sleep(5)
                try:
                    page.goto("https://suno.com/create", timeout=30000)
                except Exception:
                    print("  Navigation failed twice, skipping...")
                    continue
            time.sleep(6)

            # Click "Add Audio" button
            page.evaluate("""Array.from(document.querySelectorAll('button')).find(x =>
                (x.getAttribute('aria-label') || '').includes('Add audio'))?.click()""")
            time.sleep(3)

            # Click "Browse" option in the upload dropdown (new Suno UI)
            page.evaluate("""Array.from(document.querySelectorAll('*')).find(e =>
                e.offsetParent !== null && e.textContent.trim() === 'Browse'
                && !e.querySelector('*'))?.click()""")
            time.sleep(2)

            # File chooser
            try:
                with page.expect_file_chooser(timeout=15000) as fc_info:
                    page.evaluate("document.querySelector('input[type=file]')?.click()")
                fc_info.value.set_files(wav)
            except Exception as e:
                print(f"  Upload FAILED: {e}")
                continue
            time.sleep(5)
            print("  Uploaded WAV")

            # Wait for modals to clear
            if not wait_for_upload_done(page):
                print("  Upload did not complete, skipping...")
                continue
            print("  Upload complete")

            # Find the uploaded clip ID
            upload_clip_id = find_upload_clip(headers, song)
            if not upload_clip_id:
                # Fallback: get most recent clip
                try:
                    r = requests.get(
                        f"{SUNO_API}/api/feed/?limit=5", headers=headers, timeout=15
                    )
                    if r.status_code == 200:
                        data = (
                            r.json()
                            if isinstance(r.json(), list)
                            else r.json().get("clips", [])
                        )
                        for c in data:
                            if c.get("model_name") in (
                                None,
                                "chirp-upload",
                                "chirp-chirp",
                            ):
                                upload_clip_id = c.get("id")
                                break
                except:
                    pass

            if not upload_clip_id:
                print("  Could not find upload clip ID!")
                continue

            print(f"  Upload clip: {upload_clip_id[:12]}...")

            # ── Step 2: Create Cover ──
            try:
                page.goto(f"https://suno.com/song/{upload_clip_id}", timeout=30000)
            except Exception:
                print("  Cover nav timeout, retrying...")
                time.sleep(5)
                try:
                    page.goto(f"https://suno.com/song/{upload_clip_id}", timeout=30000)
                except Exception:
                    print("  Cover nav failed, skipping...")
                    continue
            time.sleep(6)

            if not find_cover_button(page):
                print("  Cover button not found!")
                continue

            # Build style prompt
            song_title = song.replace("_", " ").title()
            style_text = (
                f"{genre_desc} cover of {song_title} childrens nursery rhyme v5.5 cover"
            )
            if vocal == "lyrics":
                style_text = (
                    f"{genre_desc} cover of {song_title} — sing: {lyrics} v5.5 cover"
                )

            fill_cover_style(page, genre_desc, style_text)
            time.sleep(2)
            print(f"  Style: {style_text[:80]}...")

            # Snapshot existing feed IDs before creating
            existing_ids = set()
            try:
                r = requests.get(
                    f"{SUNO_API}/api/feed/?limit=20", headers=headers, timeout=15
                )
                if r.status_code == 200:
                    data = (
                        r.json()
                        if isinstance(r.json(), list)
                        else r.json().get("clips", [])
                    )
                    existing_ids = {c["id"] for c in data}
            except:
                pass

            click_create(page)
            print("  Create clicked")
            time.sleep(15)

            # Poll for new clips
            new_clips = poll_new_clips(headers, existing_ids)
            if not new_clips:
                print("  No new clips found!")
                continue

            # Download first complete clip
            for vi, clip in enumerate(new_clips[:2]):
                vid = clip["id"]
                label = ["A", "B"][vi]
                print(f"  Polling {label}: {vid[:12]}...")
                if download_clip(headers, vid, out_mp3):
                    break
            else:
                print("  All clips timed out")

            time.sleep(2)

        print("\n=== PIPELINE COMPLETE ===")


if __name__ == "__main__":
    main()
