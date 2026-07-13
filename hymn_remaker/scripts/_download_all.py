"""Download all recent complete chirp-fenix clips from Suno feed."""

import os
import sys
import json
import requests
import urllib.request
import websocket as ws

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Get token
pages = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json").read())
tab = next(
    p
    for p in pages
    if "suno.com" in p.get("url", "") and "stripe" not in p.get("url", "")
)
wsu = tab["webSocketDebuggerUrl"].replace("localhost", "127.0.0.1")
w = ws.create_connection(wsu, suppress_origin=True, timeout=10)
w.send(
    json.dumps(
        {
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {
                "expression": "async function t(){try{return await Clerk.session.getToken()}catch(e){return null}};t()",
                "returnByValue": True,
                "awaitPromise": True,
            },
        }
    )
)
token = None
for _ in range(10):
    r = w.recv()
    d = json.loads(r)
    if d.get("id") == 1:
        token = d.get("result", {}).get("result", {}).get("value")
        break
w.close()
if not token:
    sys.exit("No token")

H = {"Authorization": f"Bearer {token}"}
BASE = "https://studio-api-prod.suno.com"
GEN = (
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "generated")
    if os.path.basename(os.getcwd()) == "scripts"
    else "generated"
)
os.makedirs(GEN, exist_ok=True)

# Get many pages of the feed
all_clips = []
for page in range(1, 20):
    r = requests.get(f"{BASE}/api/feed/?limit=50&page={page}", headers=H, timeout=15)
    if r.status_code != 200:
        break
    data = r.json() if isinstance(r.json(), list) else r.json().get("clips", [])
    if not data:
        break
    all_clips.extend(data)
print(f"Feed: {len(all_clips)} clips")

# Show uploads
uploads = [
    c
    for c in all_clips
    if c.get("model_name") == "chirp-chirp"
    or ("sine" in (c.get("title", "") or "").lower())
]
print(f"Upload clips: {len(uploads)}")
for u in uploads:
    t = (u.get("title", "") or "")[:40]
    print(f'  {u["id"][:16]} "{t}" {u.get("status", "?")}')

# Download fenix clips
covers = [
    c
    for c in all_clips
    if c.get("model_name") == "chirp-fenix"
    and c.get("status") == "complete"
    and c.get("audio_url")
]
print(f"\nDownloadable covers: {len(covers)}")

downloaded = 0
for ci, c in enumerate(covers):
    au = c.get("audio_url", "")
    title = (c.get("title", "") or "untitled").replace(" ", "_").replace("/", "-")[:40]
    fname = f"cover_{ci:04d}_{title}.mp3"
    fpath = os.path.join(GEN, fname)
    if os.path.exists(fpath):
        sz = os.path.getsize(fpath)
        print(f"  SKIP {fname} ({sz // 1024}KB)")
        continue
    try:
        dl = requests.get(au, timeout=90, stream=True)
        if dl.status_code == 200:
            with open(fpath, "wb") as f:
                for chunk in dl.iter_content(chunk_size=65536):
                    f.write(chunk)
            sz = os.path.getsize(fpath)
            print(f"  OK  {fname} ({sz // 1024}KB)")
            downloaded += 1
        else:
            print(f"  ERR {fname} HTTP {dl.status_code}")
    except Exception as e:
        print(f"  ERR {fname}: {e}")

print(f"\nDownloaded: {downloaded}")
