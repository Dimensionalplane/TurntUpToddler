"""Test Suno generation with audio influence using fill() + React onChange."""
import sys, os, time, json
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env', override=True)

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

mp3_path = "hymn_remaker/output/Adventist Youth_base.mp3"
clip_ids = []

with sync_playwright() as p:
    stealth = Stealth()
    stealth.hook_playwright_context(p)

    browser = p.chromium.launch(headless=False, args=['--no-sandbox'])
    context = browser.new_context(viewport={'width': 1280, 'height': 720})

    session_token = os.environ.get('SUNO_SESSION_TOKEN', '')
    client_token = os.environ.get('SUNO_CLIENT_TOKEN', '')
    context.add_cookies([
        {'name': '__session', 'value': session_token, 'domain': '.suno.com', 'path': '/'},
        {'name': '__client', 'value': client_token, 'domain': '.suno.com', 'path': '/'},
    ])

    page = context.new_page()

    def is_gen(resp):
        return '/api/generate/v2' in resp.url and resp.status == 200

    print("[1] Loading...")
    page.goto('https://suno.com/create', timeout=30000, wait_until='domcontentloaded')
    time.sleep(15)

    # Dismiss overlays
    for _ in range(5):
        page.keyboard.press('Escape')
        time.sleep(0.3)

    # Step 1: Upload audio
    print("[2] Uploading audio influence...")
    try:
        audio_tab = page.locator('text=Audio').first
        audio_tab.click(force=True)
        time.sleep(3)

        file_input = page.locator('input[type="file"]').first
        file_input.set_input_files(mp3_path)
        print(f"    Uploaded: {os.path.basename(mp3_path)}")

        # Wait for processing
        for i in range(30):
            time.sleep(2)
            status = page.evaluate(r'''() => {
                const audio = document.querySelector('audio');
                return audio ? 'ready' : 'waiting';
            }''')
            if status == 'ready':
                print(f"    Audio processed after {(i+1)*2}s!")
                break
        time.sleep(5)
    except Exception as e:
        print(f"    Error: {e}")

    # Step 2: Set prompt - try BOTH fill() AND React onChange
    prompt = ("Deep house instrumental, four on the floor kick drum, "
              "atmospheric pads, melodic synth leads, inspired by this hymn melody")

    print(f"\n[3] Setting prompt with fill() + React onChange...")
    desc_ta = page.locator('textarea[placeholder*="Describe"], textarea[placeholder*="describe"]').first
    found = desc_ta.count() > 0
    print(f"    Description textarea found: {found}")

    if found:
        # First: use Playwright fill() which triggers proper React events
        desc_ta.click(force=True, timeout=5000)
        time.sleep(0.3)
        desc_ta.fill(prompt)
        time.sleep(1)

        # Then ALSO call React onChange to be absolutely sure
        page.evaluate('''(prompt) => {
            const ta = document.querySelector('textarea[placeholder*="Describe"], textarea[placeholder*="describe"]');
            if (!ta) return;
            const propsKey = Object.keys(ta).find(k => k.startsWith('__reactProps$'));
            if (propsKey) {
                const props = ta[propsKey];
                if (props && props.onChange) {
                    props.onChange({
                        target: { value: prompt },
                        currentTarget: { value: prompt },
                        persist: () => {},
                    });
                }
            }
        }''', prompt)
        time.sleep(3)

        val = desc_ta.input_value()
        print(f"    Value: {val[:50]}...")
    else:
        # Fallback: React fiber on last textarea
        page.evaluate('''(prompt) => {
            const tas = document.querySelectorAll('textarea');
            const ta = tas[tas.length - 1];
            if (!ta) return;
            const propsKey = Object.keys(ta).find(k => k.startsWith('__reactProps$'));
            if (propsKey && ta[propsKey] && ta[propsKey].onChange) {
                ta[propsKey].onChange({
                    target: { value: prompt },
                    currentTarget: { value: prompt },
                    persist: () => {},
                });
            }
        }''', prompt)
        time.sleep(3)

    # Check Create button
    create_btn = page.locator('button[aria-label*="Create"]').first
    btn_text = (create_btn.text_content() or '').strip()
    disabled = create_btn.is_disabled()
    print(f"\n[4] Create button: disabled={disabled} text='{btn_text}'")

    # If disabled, try keyboard typing as last resort
    if disabled and found:
        print("    Trying keyboard typing...")
        desc_ta.click(force=True, timeout=5000)
        time.sleep(0.2)
        page.keyboard.press('Control+a')
        time.sleep(0.1)
        page.keyboard.type(prompt, delay=10)
        time.sleep(3)
        disabled = create_btn.is_disabled()
        print(f"    After typing: disabled={disabled}")

    # Toggle Instrumental
    try:
        instr = page.locator('button:has-text("Instrumental")').first
        instr.click(force=True)
        time.sleep(1)
    except:
        pass

    # Check again
    disabled = create_btn.is_disabled()
    print(f"    After Instrumental toggle: disabled={disabled}")

    # Click Create
    if not disabled:
        print("\n[5] Clicking Create...")
        try:
            with page.expect_response(is_gen, timeout=300000) as resp_info:
                create_btn.click(force=True, timeout=10000)
                print("    Clicked! Waiting for response...")

            resp = resp_info.value
            data = resp.json()
            clips = data if isinstance(data, list) else [data]
            for c in clips:
                cid = c.get('id')
                if cid:
                    clip_ids.append(cid)
                    print(f"    Clip: {cid}")
        except Exception as e:
            print(f"    Error: {e}")

        # Poll and download
        if clip_ids:
            print(f"\n[6] Polling for completion...")
            import requests
            headers = {'Authorization': f'Bearer {session_token}'}

            for i in range(60):
                time.sleep(5)
                try:
                    r = requests.get(
                        f'https://studio-api.prod.suno.com/api/get/?ids={",".join(clip_ids)}',
                        headers=headers, timeout=10
                    )
                    if r.status_code == 200:
                        clips = r.json()
                        if isinstance(clips, list) and any(c.get('audio_url') for c in clips):
                            print(f"\n=== COMPLETE! ===")
                            for c in clips:
                                au = c.get('audio_url', '')
                                title = c.get('title', '')
                                print(f"  '{title}' audio={bool(au)}")
                                if au:
                                    try:
                                        ar = requests.get(au, timeout=30)
                                        if ar.status_code == 200:
                                            safe = (title or 'suno').replace(' ', '_').replace('/', '_')
                                            out = f"hymn_remaker/output/{safe}_suno.mp3"
                                            with open(out, 'wb') as f:
                                                f.write(ar.content)
                                            print(f"  Saved: {out} ({len(ar.content)//1024} KB)")
                                    except Exception as e:
                                        print(f"  DL error: {e}")
                            with open('suno_result.json', 'w') as f:
                                json.dump(clips, f, indent=2, default=str)
                            break
                except Exception as e:
                    if i % 4 == 3:
                        print(f"  Error: {e}")
    else:
        # Debug
        print("\n[DEBUG] All textarea values:")
        all_tas = page.evaluate(r'''() => {
            const tas = document.querySelectorAll('textarea');
            return Array.from(tas).map(ta => ({
                ph: ta.placeholder.substring(0, 40),
                val: ta.value.substring(0, 40),
                vis: ta.offsetHeight > 0,
            }));
        }''')
        for ta in all_tas:
            print(f"    ph='{ta['ph']}' val='{ta['val']}' vis={ta['vis']}")

    time.sleep(5)
    browser.close()
    print("\n[DONE]")
