"""Upload 5.0x WAV with logging to find the issue."""

import os
import time
import sys
import json
import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.sync_api import sync_playwright

WAV = r"C:\Users\hyper\workspace\TurntUpToddler\hymn_remaker\rendered_wav\twinkle_twinkle_speed_5_0.wav"

with sync_playwright() as pw:
    browser = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = browser.contexts[0]
    for p in ctx.pages:
        p.close()
    page = ctx.new_page()

    page.goto("https://suno.com/create", wait_until="domcontentloaded", timeout=30000)
    time.sleep(5)
    try:
        page.evaluate(
            "document.querySelectorAll('[role=dialog]').forEach(d => d.remove())"
        )
    except:
        pass
    time.sleep(2)

    # Get cookies before upload
    cookies = ctx.cookies()
    st = ""
    for c in cookies:
        if c.get("name") == "__session":
            st = c.get("value", "")
    print(f"Session: {st[:20]}...", flush=True)

    # Click Audio
    try:
        page.evaluate(
            "document.querySelector('button[aria-label*=\"Add audio\"]')?.click()"
        )
        print("Audio clicked", flush=True)
    except Exception as e:
        print(f"Audio click failed: {e}", flush=True)

    time.sleep(3)

    # Upload
    try:
        page.locator('input[type="file"]').first.set_input_files(WAV)
        print(f"Uploaded: {os.path.getsize(WAV) // 1024}KB", flush=True)
    except Exception as e:
        print(f"Upload failed: {e}", flush=True)

    time.sleep(20)

    # Check state
    try:
        text = page.inner_text("body")
        for kw in ["describe", "uploaded", "processing", "progress", "error"]:
            if kw in text.lower():
                print(f"  Found: {kw}", flush=True)
        create_btn = page.evaluate(
            "() => { let b = Array.from(document.querySelectorAll('button')).find(b => (b.innerText || '').trim() === 'Create'); return b ? {disabled: b.hasAttribute('disabled')} : 'not found'; }"
        )
        print(f"  Create: {create_btn}", flush=True)
    except Exception as e:
        print(f"Page check failed: {e}", flush=True)

    # Try API upload as fallback
    if st:
        print("\nTrying API upload...", flush=True)
        try:
            headers = {
                "Authorization": f"Bearer {st}",
                "User-Agent": "Mozilla/5.0",
            }
            # Step 1: Get upload URL
            r = requests.post(
                "https://studio-api.prod.suno.com/api/uploads/audio/",
                json={"extension": "wav", "upload_type": "file_upload"},
                headers=headers,
                timeout=15,
            )
            print(f"Upload init: {r.status_code}", flush=True)
            if r.status_code == 200:
                info = r.json()
                print(f"  Response: {json.dumps(info, indent=2)[:300]}", flush=True)
            else:
                print(f"  Error: {r.text[:200]}", flush=True)
        except Exception as e:
            print(f"  API error: {e}", flush=True)

    page.close()
