"""
SUNO COVER GENERATOR — THE WORKING v5.5 COVER FLOW
====================================================

This is the CORRECT and PROVEN approach for creating v5.5 covers on Suno.

FLOW (pure browser UI via CDP websocket):
  1. Get Clerk auth token from the active browser session
  2. Find the upload clip in feed (model_name="chirp-chirp", title contains "sine_{speed}")
  3. Navigate to https://suno.com/song/{upload_clip_id}
  4. Click "More menu contents" button
  5. Click "Remix" menu item
  6. Click "Cover" sub-menu item
     -> THIS opens Suno's native Cover creation form which SUPPORTS v5.5!
  7. Fill the form: genre description, title, v5.5 model, instrumental/vocal mode
  8. Click "Create"
  9. Poll /api/feed/ for new clip IDs (diff against snapshot)
 10. Output CLIPS:id1,id2 on stdout for the downstream downloader

WHY THIS WORKS (and the API doesn't):
  - POST /api/generate/v2-web/ with mv:"chirp-fenix" -> returns HTTP 400
  - POST /api/generate/v2-web/ with mv:"v5.5" -> returns 400 "model isn't valid"
  - The Suno API only supports chirp-v2, chirp-auk-turbo, chirp-auk (v2, v4.5)
  - ONLY the browser UI cover form accepts v5.5 (chirp-fenix)

USAGE:
  python suno_cover_remix_options_form_style_submitter.py <genre> <speed_lbl> <hymn_name> --instrumental
  python suno_cover_remix_options_form_style_submitter.py psytrance 05x Thy_Word --instrumental

PREREQUISITES:
  - Edge/Chrome with remote debugging on port 9222
  - User logged into suno.com
  - Upload clip must exist in feed (from suno_audio_uploader_file_chooser_injector.py)
"""

import sys
import time
import json
import requests
import urllib.request
import websocket

SUNO_BASE = "https://studio-api-prod.suno.com"

from pipeline_config_central_definitions_genres_speeds import GENRES


def get_ws_url():
    pages = json.load(urllib.request.urlopen("http://127.0.0.1:9222/json"))
    for p in pages:
        if "suno.com" in p.get("url", "") and "stripe" not in p.get("url", ""):
            return p["webSocketDebuggerUrl"].replace("localhost", "127.0.0.1")
    return pages[0]["webSocketDebuggerUrl"].replace("localhost", "127.0.0.1")


def js(ws_url, expr):
    try:
        ws = websocket.create_connection(ws_url, suppress_origin=True, timeout=5)
        ws.send(
            json.dumps(
                {
                    "id": 2,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": expr,
                        "returnByValue": True,
                        "awaitPromise": True,
                    },
                }
            )
        )
        for _ in range(15):
            r = ws.recv()
            d = json.loads(r)
            if d.get("id") == 2:
                val = d.get("result", {}).get("result", {}).get("value")
                ws.close()
                return val
        ws.close()
    except Exception:
        pass
    return None


def trigger_cover(
    genre_name, speed_lbl, hymn_name, make_instrumental=True, lyrics=None
):
    ws_url = get_ws_url()
    genre_desc = GENRES.get(genre_name, genre_name)

    token = js(
        ws_url,
        "async function t(){try{return await Clerk.session.getToken()}catch(e){return null}};t()",
    )
    if not token:
        print("Error: Could not retrieve authentication token.")
        return None

    hdr = {"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0"}

    print("Locating upload clip ID from Suno feed...")
    upload_clip_id = None
    for _ in range(15):
        time.sleep(3)
        r = requests.get(f"{SUNO_BASE}/api/feed/?limit=10", headers=hdr)
        if r.status_code == 200:
            clips = (
                r.json() if isinstance(r.json(), list) else r.json().get("clips", [])
            )
            for c in clips:
                title = c.get("title", "")
                # Precise check: must contain sine_{speed_lbl} and be an upload (chirp-chirp/chirp-upload)
                if f"sine_{speed_lbl}" in title.lower() and c.get("model_name") in (
                    None,
                    "chirp-chirp",
                    "chirp-upload",
                ):
                    upload_clip_id = c.get("id")
                    break
            if upload_clip_id:
                break

    if not upload_clip_id:
        print("Error: Upload track ID not found in feed list.", flush=True)
        return None
    print(f"Track ID found: {upload_clip_id}", flush=True)

    song_url = f"https://suno.com/song/{upload_clip_id}"
    print(f"Navigating to details view: {song_url}", flush=True)
    js(ws_url, f'window.location.href="{song_url}"')
    time.sleep(6)
    ws_url = get_ws_url()

    print("Opening More menu...", flush=True)
    js(
        ws_url,
        """(() => {
        var moreBtn = document.querySelector('button[aria-label="More menu contents"]');
        if (moreBtn) moreBtn.click();
    })()""",
    )
    time.sleep(2)

    print("Hovering/Clicking Remix menu item...", flush=True)
    js(
        ws_url,
        """(() => {
        var items = Array.from(document.querySelectorAll('button, [role="menuitem"]'));
        var remixItem = items.find(el => (el.textContent || '').trim() === "Remix");
        if (remixItem) remixItem.click();
    })()""",
    )
    time.sleep(2)

    print("Clicking Cover sub-menu item...", flush=True)
    js(
        ws_url,
        """(() => {
        var items = Array.from(document.querySelectorAll('button, [role="menuitem"], span'));
        var coverItem = items.find(el => (el.textContent || '').trim() === "Cover");
        if (coverItem) coverItem.click();
    })()""",
    )
    time.sleep(5)
    ws_url = get_ws_url()

    print("Filling details form...")
    instrumental_val = "true" if make_instrumental else "false"
    lyrics_escaped = (lyrics or "").replace('"', '\\"').replace("\n", "\\n")

    js(
        ws_url,
        f"""(()=>{{
        var tabs = Array.from(document.querySelectorAll("button, span, div, role[tab]")).filter(el => el.offsetParent !== null);
        var advTab = tabs.find(el => el.innerText.trim() === "Advanced" || el.getAttribute("aria-label") === "Advanced");
        if (advTab) advTab.click();

        var ns = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
        var ns_input = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;

        var modeButtons = Array.from(document.querySelectorAll("button")).filter(el => el.offsetParent !== null);
        
        if ({instrumental_val}) {{
            var instBtn = modeButtons.find(el => /instrumental/i.test(el.textContent || el.getAttribute("aria-label") || ''));
            if (instBtn) instBtn.click();
        }} else {{
            var lyrBtn = modeButtons.find(el => /add your own lyrics|lyrics/i.test(el.getAttribute("aria-label") || el.textContent || ''));
            if (lyrBtn) lyrBtn.click();
        }}

        // Small delay to let textareas render
        setTimeout(() => {{
            var tas = Array.from(document.querySelectorAll("textarea"));
            
            // Style description: maxLength === 1000
            var styleArea = tas.find(t => t.maxLength === 1000);
            if (styleArea) {{
                ns.call(styleArea, "{genre_desc}");
                styleArea.dispatchEvent(new Event("input", {{bubbles:true}}));
                styleArea.dispatchEvent(new Event("change", {{bubbles:true}}));
            }}

            // Lyrics: maxLength > 2000
            var lyrArea = tas.find(t => t.maxLength > 2000);
            if (lyrArea) {{
                if (!{instrumental_val} && "{lyrics_escaped}") {{
                    ns.call(lyrArea, "{lyrics_escaped}");
                }} else {{
                    ns.call(lyrArea, "");
                }}
                lyrArea.dispatchEvent(new Event("input", {{bubbles:true}}));
                lyrArea.dispatchEvent(new Event("change", {{bubbles:true}}));
            }}

            // Title input field
            var titleInput = document.querySelector('input[placeholder*="Title"], input[placeholder*="title"]');
            if (titleInput) {{
                ns_input.call(titleInput, "{genre_name}");
                titleInput.dispatchEvent(new Event("input", {{bubbles:true}}));
                titleInput.dispatchEvent(new Event("change", {{bubbles:true}}));
            }}

            var buttons = Array.from(document.querySelectorAll("button"));
            var v55 = buttons.find(b => b.offsetParent !== null && /v5\\.5/i.test(b.textContent || ''));
            if (v55) v55.click();
        }}, 500);
    }})()""",
    )
    time.sleep(2)

    js(
        ws_url,
        "Array.from(document.querySelectorAll('[data-base-ui-portal]')).forEach(el=>el.remove())",
    )
    time.sleep(1)

    existing_ids = set()
    r = requests.get(f"{SUNO_BASE}/api/feed/?limit=10", headers=hdr)
    if r.status_code == 200:
        clips = r.json() if isinstance(r.json(), list) else r.json().get("clips", [])
        existing_ids = {c["id"] for c in clips}

    print("Clicking Create button...", flush=True)
    js(
        ws_url,
        """(() => {
        var btn = Array.from(document.querySelectorAll("button"))
            .find(x => x.offsetParent !== null && (
                (x.getAttribute("aria-label") || "").toLowerCase().includes("create") ||
                (x.textContent || "").toLowerCase().trim() === "create" ||
                (x.textContent || "").toLowerCase().includes("create song")
            ));
        if (btn) btn.click();
    })()""",
    )
    time.sleep(15)

    print("Waiting for generation task clip IDs to appear...", flush=True)
    found = []
    for wait_loop in range(60):
        time.sleep(3)
        r = requests.get(f"{SUNO_BASE}/api/feed/?limit=10", headers=hdr)
        if r.status_code == 200:
            clips = (
                r.json() if isinstance(r.json(), list) else r.json().get("clips", [])
            )
            for c in clips:
                cid = c.get("id")
                if (
                    cid
                    and cid not in existing_ids
                    and cid not in [fc["id"] for fc in found]
                ):
                    found.append(c)
            if len(found) >= 2:
                break

    if found:
        print(
            f"Covers triggered successfully: {json.dumps([c['id'] for c in found])}",
            flush=True,
        )
        return [c["id"] for c in found]
    else:
        print("Error: Cover tracks did not appear in feed.", flush=True)
        return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("genre")
    parser.add_argument("speed_lbl")
    parser.add_argument("hymn_name")
    parser.add_argument("--lyrics", default=None)
    parser.add_argument("--instrumental", action="store_true")
    args = parser.parse_args()

    clips = trigger_cover(
        args.genre,
        args.speed_lbl,
        args.hymn_name,
        make_instrumental=args.instrumental,
        lyrics=args.lyrics,
    )
    if clips:
        print(f"CLIPS:{','.join(clips)}")
        sys.exit(0)
    sys.exit(1)
