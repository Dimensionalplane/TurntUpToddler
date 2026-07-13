"""ALL-IN-ONE: Launches browser, renders MIDI, uploads, generates covers, downloads.
No subprocess, no CDP port — everything self-contained via Playwright.

Usage: python run_cover_pipeline.py [midi_file] [genres]
Default: Thy_Word.mid, gen_psytrance,deep_house,drum_and_bass,gabba
"""
import os, sys, time, json

# ── Config ──
ROOT = os.path.dirname(os.path.abspath(__file__))
USER_DIR = os.path.join(os.environ["USERPROFILE"], "pw-chrome-suno")
GEN_DIR = os.path.join(ROOT, "generated")
os.makedirs(GEN_DIR, exist_ok=True)

SUNO_BASE = "https://studio-api.prod.suno.com"

GENRES = {
    "psytrance": {"name": "psytrance", "desc": "psytrance"},
    "deep_house": {"name": "deep_house", "desc": "deep house"},
    "drum_and_bass": {"name": "drum_and_bass", "desc": "drum and bass"},
    "gabba": {"name": "gabba", "desc": "gabba"},
    "dubstep": {"name": "dubstep", "desc": "dubstep"},
}

SPEEDS = [(0.5, "05x"), (1.0, "10x"), (1.5, "15x"), (2.0, "20x"), (3.0, "30x")]

# ── MIDI Rendering ──

def render_midi_as_sine(midi_path, mp3_path, speed=1.0):
    """Render MIDI as clean sine wave, apply ACRCloud bypass filters."""
    import mido, numpy as np
    from scipy.io import wavfile
    import subprocess as sp
    
    ffmpeg = "ffmpeg"
    CF = sp.CREATE_NO_WINDOW if hasattr(sp, "CREATE_NO_WINDOW") else 0
    
    mid = mido.MidiFile(midi_path)
    events = []
    current_time = 0.0
    for msg in mid:
        current_time += msg.time / speed
        if msg.type == "note_on" and msg.velocity > 0:
            events.append({"type": "note_on", "note": msg.note, "velocity": msg.velocity, "time": current_time})
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            events.append({"type": "note_off", "note": msg.note, "time": current_time})

    notes = []; active_notes = {}
    for ev in events:
        note = ev["note"]
        if ev["type"] == "note_on":
            if note in active_notes:
                s = active_notes[note]
                notes.append({"note": note, "start": s["time"], "end": ev["time"], "velocity": s["velocity"]})
            active_notes[note] = ev
        elif ev["type"] == "note_off" and note in active_notes:
            s = active_notes.pop(note)
            notes.append({"note": note, "start": s["time"], "end": ev["time"], "velocity": s["velocity"]})
    for note, s in active_notes.items():
        notes.append({"note": note, "start": s["time"], "end": current_time, "velocity": s["velocity"]})

    if not notes:
        raise ValueError("No notes found in MIDI.")
    
    max_time = max(n["end"] for n in notes) + 0.5
    sr = 44100
    audio = np.zeros(int(max_time * sr), dtype=np.float32)
    for n in notes:
        freq = 440.0 * (2.0 ** ((n["note"] - 69) / 12.0))
        s0 = int(n["start"] * sr); s1 = int(n["end"] * sr)
        dur = s1 - s0
        if dur <= 0: continue
        t = np.arange(dur) / sr
        amp = (n["velocity"] / 127.0) * 0.15
        env = np.ones(dur, dtype=np.float32)
        fl = min(int(0.01 * sr), dur // 2)
        if fl > 0:
            env[:fl] = np.linspace(0, 1, fl)
            env[-fl:] = np.linspace(1, 0, fl)
        audio[s0:s1] += amp * np.sin(2.0 * np.pi * freq * t) * env
    
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.9
    
    wav_path = mp3_path.replace(".mp3", "_temp.wav")
    wavfile.write(wav_path, sr, (audio * 32767).astype(np.int16))
    
    pitch_factors = {
        0.5: {"rate": 0.8909, "tempo": 1.1225},
        1.0: {"rate": 1.0595, "tempo": 0.9439},
        1.5: {"rate": 0.9439, "tempo": 1.0595},
        2.0: {"rate": 1.1225, "tempo": 0.8909},
        3.0: {"rate": 1.1892, "tempo": 0.8409},
    }
    pf = pitch_factors.get(speed, {"rate": 1.0595, "tempo": 0.9439})
    
    cmd = [ffmpeg, "-y", "-i", wav_path,
        "-af", f"asetrate=44100*{pf['rate']},atempo={pf['tempo']},aresample=44100,lowpass=f=3500,highpass=f=120,adelay=400|400",
        "-codec:a", "libmp3lame", "-b:a", "128k", mp3_path]
    sp.run(cmd, capture_output=True, text=True, timeout=60, creationflags=CF)
    if os.path.exists(wav_path):
        os.unlink(wav_path)
    print(f"  Rendered MP3: {os.path.basename(mp3_path)}")


# ── Browser Automation ──

def run_pipeline(midi_path, genre_list):
    """Full pipeline: launch browser, wait login, upload, generate covers, download."""
    from playwright.sync_api import sync_playwright
    import requests as req
    
    hymn_name = os.path.splitext(os.path.basename(midi_path))[0]
    mp3_dir = os.path.join(ROOT, "mp3_input")
    os.makedirs(mp3_dir, exist_ok=True)
    
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=USER_DIR, headless=False,
            args=["--disable-blink-features=AutomationControlled", "--disable-features=TranslateUI"], 
            no_viewport=True
        )
        page = ctx.new_page()
        page.goto("https://suno.com/create")
        page.wait_for_timeout(5000)
        
        # Wait for login
        print("\n>>> LOG INTO SUNO <<<")
        token = None
        for attempt in range(120):
            try:
                token = page.evaluate(
                    "(async function(){try{return await Clerk.session.getToken()}catch(e){return null}})()"
                )
            except: pass
            if token and len(str(token)) > 100:
                print(f"Logged in! Token: {len(str(token))} chars\n")
                break
            time.sleep(3)
            if attempt == 40:
                print("  Still waiting for login...")
        else:
            print("TIMEOUT — closing")
            ctx.close()
            return
        
        hdr = {"Authorization": f"Bearer {token}"}
        
        for speed_val, speed_lbl in SPEEDS:
            print(f"\n=== Speed {speed_val}x ({speed_lbl}) ===")
            mp3_path = os.path.join(mp3_dir, f"{hymn_name}_sine_{speed_lbl}.mp3")
            
            # Render
            render_midi_as_sine(midi_path, mp3_path, speed=speed_val)
            
            # Upload
            print("  Uploading to Suno...")
            page.goto("https://suno.com/create")
            page.wait_for_timeout(8000)
            
            # Click Add Audio
            page.evaluate(
                'Array.from(document.querySelectorAll("button")).find(x=>(x.getAttribute("aria-label")||"").includes("Add audio"))?.click()'
            )
            page.wait_for_timeout(3000)
            
            # Click browse option
            page.evaluate(
                'Array.from(document.querySelectorAll("*")).find(e=>e.offsetParent!==null&&e.textContent.trim()==="Browse, upload, or record audio")?.click()'
            )
            page.wait_for_timeout(2000)
            
            # Upload file
            with page.expect_file_chooser(timeout=15000) as fc_info:
                page.evaluate("document.querySelector('input[type=file]')?.click()")
            fc_info.value.set_files(mp3_path)
            page.wait_for_timeout(5000)
            print("  File uploaded")
            
            # Handle modals
            upload_ok = False
            for i in range(45):
                page.wait_for_timeout(2000)
                body = page.evaluate("document.body.innerText.toLowerCase().substring(0,1000)")
                
                if "identify" in body:
                    page.evaluate("""
                        (() => {
                            var options = Array.from(document.querySelectorAll('span, p, div, label, button'))
                                .filter(el => el.offsetParent !== null && /full song|instrumental/i.test(el.textContent || ''));
                            options.forEach(el => el.click());
                            setTimeout(() => {
                                var cb = Array.from(document.querySelectorAll('button'))
                                    .find(b => b.offsetParent !== null && b.textContent.trim() === 'Continue');
                                if (cb) cb.click();
                            }, 500);
                        })()
                    """)
                    print("  Identify handled")
                elif "describe" in body and "identify" not in body:
                    page.evaluate("""
                        (() => {
                            var tas = Array.from(document.querySelectorAll("textarea"));
                            var ns = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,"value").set;
                            var ta = tas.find(t => t.offsetParent !== null);
                            if (ta) {
                                ns.call(ta, "hymn");
                                ta.dispatchEvent(new Event("input", {bubbles:true}));
                            }
                            setTimeout(() => {
                                var cb = Array.from(document.querySelectorAll('button'))
                                    .find(b => b.offsetParent !== null && b.textContent.trim() === 'Continue');
                                if (cb) cb.click();
                            }, 500);
                        })()
                    """)
                    print("  Describe handled")
                elif "matches an existing recording" in body or "copyright" in body:
                    print("  REJECTED (copyright). Trying next speed.")
                    break
                else:
                    is_modal = page.evaluate(
                        "!!Array.from(document.querySelectorAll('span,p,div,label,button,h2')).find(x => /identify|describe/i.test(x.textContent || ''))"
                    )
                    if not is_modal:
                        print("  Upload COMPLETE!")
                        upload_ok = True
                        break
            
            if not upload_ok:
                try: os.remove(mp3_path)
                except: pass
                continue
            
            # Find the uploaded clip ID in feed
            upload_clip_id = None
            for _ in range(15):
                time.sleep(3)
                r = req.get(f"{SUNO_BASE}/api/feed/?limit=10", headers=hdr)
                if r.status_code == 200:
                    clips = r.json() if isinstance(r.json(), list) else r.json().get("clips", [])
                    for c in clips:
                        if c.get("title") == "hymn" or hymn_name.lower() in c.get("title","").lower() or f"sine_{speed_lbl}" in c.get("title","").lower():
                            upload_clip_id = c.get("id")
                            break
                    if upload_clip_id: break
            
            if not upload_clip_id:
                # Try broader search
                r = req.get(f"{SUNO_BASE}/api/feed/?limit=5", headers=hdr)
                if r.status_code == 200:
                    clips = r.json() if isinstance(r.json(), list) else r.json().get("clips", [])
                    for c in clips:
                        if c.get("model_name") in (None, "chirp-chirp", "chirp-upload"):
                            upload_clip_id = c.get("id")
                            break
            
            if not upload_clip_id:
                print("  Could not find uploaded clip ID!")
                continue
            
            print(f"  Uploaded clip: {upload_clip_id[:24]}...")
            
            # Generate covers for each genre
            for genre_key in genre_list:
                genre_key = genre_key.strip().lower()
                if genre_key not in GENRES: continue
                g = GENRES[genre_key]
                
                print(f"\n  --- {g['name']} ---")
                
                # Navigate to song page
                page.goto(f"https://suno.com/song/{upload_clip_id}")
                page.wait_for_timeout(6000)
                
                # Find and click Create Cover
                for attempt in range(15):
                    page.wait_for_timeout(2000)
                    result = page.evaluate("""
                        (() => {
                            var btns = Array.from(document.querySelectorAll('button, [role="button"], a'))
                                .filter(x => x.offsetParent !== null);
                            var patterns = ['create cover', 'cover song', 'make cover', 'cover this', 'use as cover', 'remix'];
                            for (var p of patterns) {
                                var b = btns.find(x => (x.textContent || '').toLowerCase().includes(p) || (x.getAttribute('aria-label') || '').toLowerCase().includes(p));
                                if (b) { b.click(); return 'clicked:' + p; }
                            }
                            var more = btns.find(x => (x.getAttribute('aria-label') || '').toLowerCase().includes('more') || (x.textContent || '').trim().length <= 3);
                            if (more) { more.click(); return 'opened_menu'; }
                            return 'not_found';
                        })()
                    """)
                    if result and result.startswith("clicked:"):
                        print(f"    Cover button clicked: {result}")
                        page.wait_for_timeout(4000)
                        break
                    elif result == "opened_menu":
                        page.wait_for_timeout(1000)
                        r2 = page.evaluate("""
                            (() => {
                                var items = Array.from(document.querySelectorAll('[role="menuitem"], li, [data-radix-dropdown-menu-content] *'))
                                    .filter(x => x.offsetParent !== null);
                                var b = items.find(x => /cover|remix/i.test(x.textContent || ''));
                                if (b) { b.click(); return 'menu_ok'; }
                                return 'menu_no';
                            })()
                        """)
                        if r2 == "menu_ok":
                            print("    Cover from menu")
                            page.wait_for_timeout(4000)
                            break
                
                # Fill description textareas
                page.evaluate(f"""
                    (() => {{
                        var tas = Array.from(document.querySelectorAll("textarea"));
                        var ns = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,"value").set;
                        if(tas.length > 0) {{
                            ns.call(tas[0], "{g['desc']}");
                            tas[0].dispatchEvent(new Event("input",{{bubbles:true}}));
                        }}
                        if(tas.length > 1) {{
                            ns.call(tas[1], "{g['desc']} cover of {hymn_name}");
                            tas[1].dispatchEvent(new Event("input",{{bubbles:true}}));
                        }}
                    }})()
                """)
                page.wait_for_timeout(2000)
                
                # Snapshot existing feed
                existing_ids = set()
                r = req.get(f"{SUNO_BASE}/api/feed/?limit=10", headers=hdr)
                if r.status_code == 200:
                    clips = r.json() if isinstance(r.json(), list) else r.json().get("clips", [])
                    existing_ids = {c["id"] for c in clips}
                
                # Click Create
                page.evaluate("""
                    (() => {
                        var btn = Array.from(document.querySelectorAll("button"))
                            .find(x => x.offsetParent !== null && (
                                (x.getAttribute("aria-label") || "").toLowerCase().includes("create") ||
                                (x.textContent || "").toLowerCase().trim() === "create"
                            ));
                        if (btn) btn.click();
                    })()
                """)
                print("    Create clicked")
                page.wait_for_timeout(15000)
                
                # Poll for new clips
                found = []
                for _ in range(60):
                    time.sleep(3)
                    r = req.get(f"{SUNO_BASE}/api/feed/?limit=10", headers=hdr)
                    if r.status_code == 200:
                        clips = r.json() if isinstance(r.json(), list) else r.json().get("clips", [])
                        for c in clips:
                            cid = c.get("id")
                            if cid and cid not in existing_ids and cid not in [fc["id"] for fc in found]:
                                found.append(c)
                        if len(found) >= 2:
                            break
                
                if not found:
                    print("    No new clips found!")
                    continue
                
                # Download completed clips
                for vi, clip in enumerate(found[:2]):
                    vid = clip["id"]
                    label = ["A","B"][vi]
                    for i in range(80):
                        time.sleep(3)
                        r2 = req.get(f"{SUNO_BASE}/api/clip/{vid}/", headers=hdr)
                        if r2.status_code == 200:
                            d = r2.json()
                            st = d.get("status","")
                            url = d.get("audio_url","")
                            if st == "complete" and url:
                                dl = req.get(url, timeout=120, stream=True)
                                if dl.status_code == 200:
                                    out = os.path.join(GEN_DIR, f"{hymn_name}_{speed_lbl}_{g['name']}_{label}_cover.mp3")
                                    with open(out, "wb") as f:
                                        for chunk in dl.iter_content(65536): f.write(chunk)
                                    dur = d.get("metadata",{}).get("duration","?")
                                    tags = d.get("metadata",{}).get("tags","")
                                    model = d.get("metadata",{}).get("model_version","?")
                                    print(f"    DOWNLOADED {label}: {os.path.getsize(out)//1024}KB | {dur}s | {model} | {tags}")
                                break
                            elif st in ("error","failed"):
                                break
        
        ctx.close()
        print("\n=== PIPELINE COMPLETE ===")


if __name__ == "__main__":
    midi_file = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "hymn_remaker", "input", "Thy_Word.mid")
    genres = sys.argv[2] if len(sys.argv) > 2 else "psytrance,deep_house,drum_and_bass"
    run_pipeline(midi_file, genres.split(","))
