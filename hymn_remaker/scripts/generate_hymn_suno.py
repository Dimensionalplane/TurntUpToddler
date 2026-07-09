"""Generate songs via Suno CDP — with retries when Create is disabled."""

import os
import time
import requests
import re
from playwright.sync_api import sync_playwright

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "suno_generated"
)
RENDER_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rendered_wav"
)
os.makedirs(OUTPUT_DIR, exist_ok=True)

SONG = "amazing_grace"
GENRES = [
    ("full-on psytrance, 145bpm, rolling bassline, euphoric melodic", "psytrance"),
    ("forest goa trance, 138bpm, dark atmospheric, nature sounds", "goa"),
]
SPEEDS = [0.5, 1.0, 2.5, 5.0]
MAX_RETRIES = 3

with sync_playwright() as pw:
    browser = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
    context = browser.contexts[0]

    # Close stale Suno pages so we start fresh
    for p in context.pages[:]:
        if "suno" in p.url:
            try:
                p.close()
            except Exception:
                pass

    page = context.new_page()

    def dismiss_dialogs():
        page.evaluate("""(() => {
            let dialogs = document.querySelectorAll('[role=dialog], [class*="consent"], [class*="cookie"], [class*="privacy"], [id*="onetrust"], [id*="cookie"]');
            dialogs.forEach(d => d.remove());
            document.querySelectorAll('div[style*="fixed"], div[class*="overlay"]').forEach(d => {
                if (d.offsetParent !== null) d.remove();
            });
        })()""")

    def try_create(genre_prompt, wav_path):
        """Upload WAV, fill style, try Create. Returns True if clicked."""
        page.goto(
            "https://suno.com/create", wait_until="domcontentloaded", timeout=30000
        )
        time.sleep(6)
        try:
            dismiss_dialogs()
        except Exception:
            pass
        time.sleep(2)

        # Click Add Audio
        page.evaluate(
            "document.querySelector('button[aria-label*=\"Add audio\"]')?.click()"
        )
        time.sleep(3)

        # Upload file — works on the hidden input directly
        page.locator('input[type="file"]').first.set_input_files(wav_path)
        time.sleep(10)

        # Handle Identify / Describe / Upload flow
        for i in range(40):
            time.sleep(2)
            bt = page.inner_text("body").lower()

            if "identify" in bt:
                page.evaluate("""Array.from(document.querySelectorAll('button')).filter(b =>
                    b.offsetParent !== null && /full song|instrumental|cover/i.test(b.innerText || '')
                ).forEach(b => b.click())""")
                page.evaluate("""Array.from(document.querySelectorAll('button')).find(b =>
                    b.offsetParent !== null && (b.innerText || '').trim() === 'Continue'
                )?.click()""")
            elif "describe" in bt:
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
            elif "style influence" in bt or "uploaded" in bt:
                time.sleep(3)
                break

        time.sleep(3)

        # Switch to Advanced tab
        page.evaluate("""Array.from(document.querySelectorAll('[role="tab"]')).find(t =>
            (t.innerText || '').trim() === 'Advanced'
        )?.click()""")
        time.sleep(2)

        # Fill style in second textarea
        page.evaluate(f"""
            var tas = Array.from(document.querySelectorAll('textarea')).filter(t => t.offsetParent !== null);
            if (tas.length >= 2) {{
                var ns = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                ns.call(tas[1], '{genre_prompt}');
                tas[1].dispatchEvent(new Event('input', {{bubbles: true}}));
            }}
        """)
        time.sleep(1)

        # Try Create for up to 40s
        for wi in range(20):
            time.sleep(2)
            created = page.evaluate("""(() => {
                let btn = document.querySelector('button[aria-label*="Create song"]');
                if (btn && !btn.hasAttribute('disabled') && btn.offsetParent !== null) {
                    btn.click(); return 'clicked';
                }
                btn = Array.from(document.querySelectorAll('button')).find(b =>
                    (b.innerText || '').includes('Create') && b.offsetParent !== null && !b.hasAttribute('disabled')
                );
                if (btn) { btn.click(); return 'clicked_fallback'; }
                return 'disabled';
            })()""")
            if created != "disabled":
                return True

        return False

    def download_mp3(session_token, out_mp3):
        """Find the most recent clip and download it."""
        page.goto("https://suno.com/create", timeout=30000)
        time.sleep(5)
        clips = re.findall(r"/song/([0-9a-f-]+)", page.content())
        if not clips:
            return False

        cid = clips[-1]
        for i in range(30):
            try:
                r = requests.get(
                    f"https://studio-api.prod.suno.com/api/clip/{cid}/",
                    headers={"Authorization": f"Bearer {session_token}"},
                    timeout=10,
                )
                if r.status_code == 200 and r.json().get("status") == "complete":
                    url = r.json().get("audio_url", "")
                    if url:
                        resp = requests.get(url, timeout=120, stream=True)
                        with open(out_mp3, "wb") as f:
                            for chunk in resp.iter_content(chunk_size=65536):
                                f.write(chunk)
                        return True
            except:
                pass
            time.sleep(5)
        return False

    # === MAIN LOOP ===
    # Show credits once
    page.goto("https://suno.com/create", wait_until="domcontentloaded", timeout=30000)
    time.sleep(6)
    try:
        dismiss_dialogs()
    except Exception:
        pass
    try:
        body = page.inner_text("body")
    except Exception:
        body = ""
    credits = re.search(r"([\d,]+)\s*Credits?", body)
    print(f"Credits: {credits.group(1) if credits else 'unknown'}")

    for genre_prompt, genre_slug in GENRES:
        for speed in SPEEDS:
            wav_file = f"{SONG}_speed_{str(speed).replace('.', '_')}.wav"
            wav_path = os.path.join(RENDER_DIR, wav_file)
            out_mp3 = os.path.join(
                OUTPUT_DIR,
                f"{SONG}_{genre_slug}_speed_{str(speed).replace('.', '_')}.mp3",
            )

            if os.path.exists(out_mp3):
                print(f"\nAlready exists: {out_mp3}")
                continue
            if not os.path.exists(wav_path):
                print(f"\nWAV not found: {wav_path}")
                continue

            print(f"\n=== {wav_file} | {genre_slug} ===")

            # Retry loop
            success = False
            for attempt in range(1, MAX_RETRIES + 1):
                print(f"  Attempt {attempt}/{MAX_RETRIES}")

                # Close and recreate page for a clean state each retry
                try:
                    page.close()
                except Exception:
                    pass
                page = context.new_page()

                if try_create(genre_prompt, wav_path):
                    print("  Create clicked OK")
                    time.sleep(90)

                    # Also poll the feed as fallback
                    cookies = context.cookies()
                    session_token = ""
                    for c in cookies:
                        if c.get("name") == "__session":
                            session_token = c.get("value", "")
                            break

                    downloaded = False
                    if session_token:
                        downloaded = download_mp3(session_token, out_mp3)
                        if not downloaded:
                            # Fallback: poll the feed API
                            for fi in range(12):
                                time.sleep(10)
                                try:
                                    feed = requests.get(
                                        "https://studio-api.prod.suno.com/api/feed/?page=1",
                                        headers={
                                            "Authorization": f"Bearer {session_token}"
                                        },
                                        timeout=10,
                                    )
                                    if feed.status_code == 200:
                                        items = feed.json()
                                        for item in items:
                                            if item.get(
                                                "status"
                                            ) == "complete" and item.get("audio_url"):
                                                title = (
                                                    item.get("title") or ""
                                                ).lower()
                                                if "twinkle" in title or SONG in title:
                                                    resp = requests.get(
                                                        item["audio_url"],
                                                        timeout=120,
                                                        stream=True,
                                                    )
                                                    with open(out_mp3, "wb") as f:
                                                        for chunk in resp.iter_content(
                                                            chunk_size=65536
                                                        ):
                                                            f.write(chunk)
                                                    downloaded = True
                                                    break
                                except:
                                    pass
                                if downloaded:
                                    break

                    if downloaded:
                        print(f"  Downloaded: {out_mp3}")
                        success = True
                        break
                    else:
                        print("  Download failed, retrying...")
                else:
                    print("  Create stayed disabled, retrying...")

                time.sleep(5)

            if not success:
                print(f"  FAILED after {MAX_RETRIES} attempts")

            time.sleep(10)

    print("\nDone!")
