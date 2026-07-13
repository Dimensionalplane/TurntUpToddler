"""QUICK PIPELINE - connects to Edge on port 9222, renders Thy Word, generates all covers."""
from playwright.sync_api import sync_playwright
import os, sys, time, json, mido, numpy as np, requests as req, subprocess as sp
from scipy.io import wavfile

ROOT = os.path.dirname(os.path.abspath(__file__))
MIDI = os.path.join(ROOT, "hymn_remaker", "input", "Thy_Word.mid")
FFMPEG = "ffmpeg"
GENRES = ["psytrance", "deep_house", "drum_and_bass", "gabba", "dubstep"]
SPEEDS = [(0.5, "05x"), (1.0, "10x"), (1.5, "15x"), (2.0, "20x"), (3.0, "30x")]
SUNO_BASE = "https://studio-api.prod.suno.com"
CF = sp.CREATE_NO_WINDOW if hasattr(sp, "CREATE_NO_WINDOW") else 0
hymn_name = os.path.splitext(os.path.basename(MIDI))[0]
os.makedirs(os.path.join(ROOT, "generated"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "mp3_input"), exist_ok=True)

def render_midi(midi_path, mp3_path, speed):
    if os.path.exists(mp3_path):
        return
    mid = mido.MidiFile(midi_path)
    events = []
    ct = 0.0
    for msg in mid:
        ct += msg.time / speed
        if msg.type == "note_on" and msg.velocity > 0:
            events.append({"t": "on", "n": msg.note, "v": msg.velocity, "tm": ct})
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            events.append({"t": "off", "n": msg.note, "tm": ct})
    notes = []
    active = {}
    for ev in events:
        n = ev["n"]
        if ev["t"] == "on":
            if n in active:
                notes.append({"n": n, "s": active[n]["tm"], "e": ev["tm"], "v": active[n]["v"]})
            active[n] = ev
        elif n in active:
            s = active.pop(n)
            notes.append({"n": n, "s": s["tm"], "e": ev["tm"], "v": s["v"]})
    for n, s in active.items():
        notes.append({"n": n, "s": s["tm"], "e": ct, "v": s["v"]})
    if not notes:
        raise ValueError("No notes")
    mt = max(n["e"] for n in notes) + 0.5
    sr = 44100
    audio = np.zeros(int(mt * sr), dtype=np.float32)
    for n in notes:
        freq = 440.0 * (2.0 ** ((n["n"] - 69) / 12.0))
        s0 = int(n["s"] * sr)
        s1 = int(n["e"] * sr)
        dur = s1 - s0
        if dur <= 0:
            continue
        t = np.arange(dur) / sr
        amp = (n["v"] / 127.0) * 0.15
        env = np.ones(dur, dtype=np.float32)
        fl = min(int(0.01 * sr), dur // 2)
        if fl > 0:
            env[:fl] = np.linspace(0, 1, fl)
            env[-fl:] = np.linspace(1, 0, fl)
        audio[s0:s1] += amp * np.sin(2.0 * np.pi * freq * t) * env
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.9
    wav = mp3_path.replace(".mp3", "_t.wav")
    wavfile.write(wav, sr, (audio * 32767).astype(np.int16))
    pf = {0.5: {"r": 0.8909, "t": 1.1225}, 1.0: {"r": 1.0595, "t": 0.9439},
          1.5: {"r": 0.9439, "t": 1.0595}, 2.0: {"r": 1.1225, "t": 0.8909},
          3.0: {"r": 1.1892, "t": 0.8409}}
    p = pf.get(speed, {"r": 1.0595, "t": 0.9439})
    cmd = [FFMPEG, "-y", "-i", wav, "-af",
           f"asetrate=44100*{p['r']},atempo={p['t']},aresample=44100,lowpass=f=3500,highpass=f=120,adelay=400|400",
           "-codec:a", "libmp3lame", "-b:a", "128k", mp3_path]
    sp.run(cmd, capture_output=True, text=True, timeout=60, creationflags=CF)
    if os.path.exists(wav):
        os.unlink(wav)
    print(f"  Rendered MP3: {os.path.getsize(mp3_path)//1024}KB")

print("Connecting to Edge on port 9222...")
with sync_playwright() as pw:
    b = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
    suno = [pg for pg in b.contexts[0].pages if "suno.com" in pg.url][0]
    token = suno.evaluate(
        "(async function(){try{return await Clerk.session.getToken()}catch(e){return null}})()"
    )
    print(f"Token: {len(str(token))} chars")
    hdr = {"Authorization": f"Bearer {token}"}

    for speed_val, speed_lbl in SPEEDS:
        print(f"\n=== Speed {speed_val}x ===")
        mp3_path = os.path.join(ROOT, "mp3_input", f"{hymn_name}_sine_{speed_lbl}.mp3")
        render_midi(MIDI, mp3_path, speed_val)

        # Upload
        suno.goto("https://suno.com/create")
        suno.wait_for_timeout(8000)
        suno.evaluate(
            'Array.from(document.querySelectorAll("button")).find(x=>(x.getAttribute("aria-label")||"").includes("Add audio"))?.click()'
        )
        suno.wait_for_timeout(3000)
        suno.evaluate(
            'Array.from(document.querySelectorAll("*")).find(e=>e.offsetParent!==null&&e.textContent.trim()==="Browse, upload, or record audio")?.click()'
        )
        suno.wait_for_timeout(2000)

        with suno.expect_file_chooser(timeout=15000) as fc:
            suno.evaluate("document.querySelector('input[type=file]')?.click()")
        fc.value.set_files(os.path.abspath(mp3_path))
        suno.wait_for_timeout(5000)
        print("  Uploaded")

        # Handle modals
        upload_ok = False
        for i in range(45):
            suno.wait_for_timeout(2000)
            body = suno.evaluate("document.body.innerText.toLowerCase().substring(0,1000)")
            if "identify" in body:
                suno.evaluate(
                    """(()=>{var options=Array.from(document.querySelectorAll('span,p,div,label,button')).filter(el=>el.offsetParent!==null&&/full song|instrumental/i.test(el.textContent||''));options.forEach(el=>el.click());setTimeout(()=>{var cb=Array.from(document.querySelectorAll('button')).find(b=>b.offsetParent!==null&&b.textContent.trim()==='Continue');if(cb)cb.click()},500)})()"""
                )
                print("  Identify handled")
            elif "describe" in body and "identify" not in body:
                suno.evaluate(
                    """(()=>{var tas=Array.from(document.querySelectorAll('textarea'));var ns=Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set;var ta=tas.find(t=>t.offsetParent!==null);if(ta){ns.call(ta,'hymn');ta.dispatchEvent(new Event('input',{bubbles:true}))}setTimeout(()=>{var cb=Array.from(document.querySelectorAll('button')).find(b=>b.offsetParent!==null&&b.textContent.trim()==='Continue');if(cb)cb.click()},500)})()"""
                )
                print("  Describe handled")
            elif "matches an existing recording" in body or "copyright" in body:
                print("  REJECTED - copyright")
                break
            else:
                is_modal = suno.evaluate(
                    "!!Array.from(document.querySelectorAll('span,p,div,label,button,h2')).find(x=>(/identify|describe/i.test(x.textContent||'')))"
                )
                if not is_modal:
                    upload_ok = True
                    print("  Upload COMPLETE!")
                    break

        if not upload_ok:
            continue

        # Find uploaded clip
        upload_cid = None
        for _ in range(15):
            time.sleep(3)
            r = req.get(f"{SUNO_BASE}/api/feed/?limit=10", headers=hdr)
            if r.status_code == 200:
                clips = r.json() if isinstance(r.json(), list) else r.json().get("clips", [])
                for c in clips:
                    if f"sine_{speed_lbl}" in c.get("title", "").lower() or c.get("title") == "hymn":
                        upload_cid = c.get("id")
                        break
                if upload_cid:
                    break
        if not upload_cid:
            r = req.get(f"{SUNO_BASE}/api/feed/?limit=5", headers=hdr)
            if r.status_code == 200:
                clips = r.json() if isinstance(r.json(), list) else r.json().get("clips", [])
                for c in clips:
                    if c.get("model_name") in (None, "chirp-chirp", "chirp-upload"):
                        upload_cid = c.get("id")
                        break

        if not upload_cid:
            print("  No clip ID found!")
            continue
        print(f"  Uploaded clip: {upload_cid[:24]}...")

        # Generate covers for each genre
        for genre in GENRES:
            print(f"\n  --- {genre} ---")
            suno.goto(f"https://suno.com/song/{upload_cid}")
            suno.wait_for_timeout(6000)

            # Find cover button
            for a in range(15):
                suno.wait_for_timeout(2000)
                r = suno.evaluate(
                    """(()=>{var btns=Array.from(document.querySelectorAll('button,[role="button"],a')).filter(x=>x.offsetParent!==null);var patterns=['create cover','cover song','make cover','cover this','use as cover','remix'];for(var p of patterns){var b=btns.find(x=>(x.textContent||'').toLowerCase().includes(p)||(x.getAttribute('aria-label')||'').toLowerCase().includes(p));if(b){b.click();return'clicked:'+p}}var more=btns.find(x=>(x.getAttribute('aria-label')||'').toLowerCase().includes('more'));if(more){more.click();return'opened_menu'}return'not_found'})()"""
                )
                if r and r.startswith("clicked:"):
                    print(f"    {r}")
                    suno.wait_for_timeout(4000)
                    break
                elif r == "opened_menu":
                    time.sleep(1)
                    r2 = suno.evaluate(
                        """(()=>{var items=Array.from(document.querySelectorAll('[role="menuitem"],li')).filter(x=>x.offsetParent!==null);var b=items.find(x=>/cover|remix/i.test(x.textContent||''));if(b){b.click();return'menu_ok'}return'menu_no'})()"""
                    )
                    if r2 == "menu_ok":
                        print("    Cover from menu")
                        suno.wait_for_timeout(4000)
                        break

            # Fill textareas
            suno.evaluate(
                f"""(function(){{var tas=Array.from(document.querySelectorAll('textarea'));var ns=Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set;if(tas.length>0){{ns.call(tas[0],'{genre}');tas[0].dispatchEvent(new Event('input',{{bubbles:true}}))}}if(tas.length>1){{ns.call(tas[1],'{genre} cover of {hymn_name}');tas[1].dispatchEvent(new Event('input',{{bubbles:true}}))}}}})()"""
            )
            suno.wait_for_timeout(2000)

            # Snapshot existing
            existing_ids = set()
            r = req.get(f"{SUNO_BASE}/api/feed/?limit=10", headers=hdr)
            if r.status_code == 200:
                clips = r.json() if isinstance(r.json(), list) else r.json().get("clips", [])
                existing_ids = {c["id"] for c in clips}

            # Click Create
            suno.evaluate(
                """(()=>{var btn=Array.from(document.querySelectorAll('button')).find(x=>x.offsetParent!==null&&((x.getAttribute('aria-label')||'').toLowerCase().includes('create')||(x.textContent||'').toLowerCase().trim()==='create'));if(btn)btn.click()})()"""
            )
            print("    Create clicked")
            suno.wait_for_timeout(15000)

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

            # Download
            for vi, clip in enumerate(found[:2]):
                vid = clip["id"]
                label = ["A", "B"][vi]
                for i in range(80):
                    time.sleep(3)
                    r2 = req.get(f"{SUNO_BASE}/api/clip/{vid}/", headers=hdr)
                    if r2.status_code == 200:
                        d = r2.json()
                        st = d.get("status", "")
                        url = d.get("audio_url", "")
                        if st == "complete" and url:
                            dl = req.get(url, timeout=120, stream=True)
                            if dl.status_code == 200:
                                out = os.path.join(
                                    ROOT, "generated",
                                    f"{hymn_name}_{speed_lbl}_{genre}_{label}_cover.mp3"
                                )
                                with open(out, "wb") as f:
                                    for chunk in dl.iter_content(65536):
                                        f.write(chunk)
                                dur = d.get("metadata", {}).get("duration", "?")
                                tags = d.get("metadata", {}).get("tags", "")
                                model = d.get("metadata", {}).get("model_version", "?")
                                print(f"    DOWNLOADED {label}: {os.path.getsize(out)//1024}KB | {dur}s | {model} | {tags}")
                            break
                        elif st in ("error", "failed"):
                            print(f"    Clip {vid[:8]} failed")
                            break

    b.close()
    print("\n=== PIPELINE COMPLETE ===")
