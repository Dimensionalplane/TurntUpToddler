"""Fresh Suno generation with audio influence.
Opens browser, waits for login, grabs tokens, then generates with audio influence."""
import sys, os, time, json
sys.path.insert(0, '.')

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# Pick a hymn MP3 for audio influence
mp3_path = "hymn_remaker/output/Adventist Youth_base.mp3"
if not os.path.exists(mp3_path):
    import glob
    mp3s = sorted(glob.glob("hymn_remaker/output/*_base.mp3"))
    mp3_path = mp3s[0] if mp3s else None

if not mp3_path:
    print("ERROR: No base MP3 files found!")
    sys.exit(1)

print("=" * 60)
print("  SUNO GENERATION WITH AUDIO INFLUENCE")
print("=" * 60)
print(f"\nAudio influence: {mp3_path}")
print(f"Size: {os.path.getsize(mp3_path) / 1024:.0f} KB\n")

clip_ids = []

with sync_playwright() as p:
    stealth = Stealth()
    stealth.hook_playwright_context(p)
    
    browser = p.chromium.launch(headless=False, args=['--no-sandbox'])
    context = browser.new_context(viewport={'width': 1280, 'height': 720})
    
    # Try setting existing tokens
    from dotenv import load_dotenv
    load_dotenv('.env', override=True)
    old_session = os.environ.get('SUNO_SESSION_TOKEN', '')
    old_client = os.environ.get('SUNO_CLIENT_TOKEN', '')
    if old_session:
        context.add_cookies([
            {'name': '__session', 'value': old_session, 'domain': '.suno.com', 'path': '/'},
            {'name': '__client', 'value': old_client, 'domain': '.suno.com', 'path': '/'},
        ])
    
    page = context.new_page()
    
    print("[1] Loading suno.com/create...")
    page.goto('https://suno.com/create', timeout=30000, wait_until='domcontentloaded')
    time.sleep(15)
    print(f"    URL: {page.url[:60]}")
    
    # Wait for login if needed
    if 'sign-in' in page.url or 'login' in page.url:
        print("    Login required! Please log in in the browser window...")
        for i in range(180):
            time.sleep(2)
            cur = page.url
            if 'suno.com' in cur and 'sign-in' not in cur and 'login' not in cur:
                print(f"    Login completed after {(i+1)*2}s!")
                break
            if i % 15 == 14:
                print(f"    Still waiting... ({(i+1)*2}s)")
        time.sleep(5)
    
    # Extract fresh tokens
    print("\n[2] Extracting tokens...")
    session_token = None
    client_token = None
    
    for c in context.cookies():
        if c['name'] == '__session' and 'suno.com' in c.get('domain', ''):
            val = c['value']
            if len(val) > 100:
                session_token = val
        elif c['name'] == '__client' and 'suno.com' in c.get('domain', ''):
            val = c['value']
            if len(val) > 100:
                client_token = val
    
    # Fallback: try document.cookie
    if not session_token:
        doc_cookies = page.evaluate('document.cookie')
        for part in doc_cookies.split(';'):
            part = part.strip()
            if part.startswith('__session='):
                session_token = part.split('=', 1)[1]
            elif part.startswith('__client='):
                client_token = part.split('=', 1)[1]
    
    if session_token:
        print(f"    Session: {session_token[:40]}... ({len(session_token)} chars)")
    else:
        print("    WARNING: No session token found!")
    if client_token:
        print(f"    Client: {client_token[:40]}... ({len(client_token)} chars)")
    
    # Save to .env
    if session_token and client_token:
        env_path = '.env'
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        updated_s = updated_c = False
        for i, line in enumerate(lines):
            if line.startswith('SUNO_SESSION_TOKEN='):
                lines[i] = f'SUNO_SESSION_TOKEN={session_token}\n'
                updated_s = True
            elif line.startswith('SUNO_CLIENT_TOKEN='):
                lines[i] = f'SUNO_CLIENT_TOKEN={client_token}\n'
                updated_c = True
        if not updated_s:
            lines.append(f'SUNO_SESSION_TOKEN={session_token}\n')
        if not updated_c:
            lines.append(f'SUNO_CLIENT_TOKEN={client_token}\n')
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print("    Saved to .env!")
    
    # Dismiss overlays
    for _ in range(5):
        page.keyboard.press('Escape')
        time.sleep(0.3)
    try:
        close_btn = page.locator('[aria-label="Close"]')
        if close_btn.count() > 0:
            close_btn.first.click(force=True)
            time.sleep(1)
    except:
        pass
    
    # Check credits
    print("\n[3] Checking credits...")
    credits_text = page.evaluate(r'''() => {
        const buttons = document.querySelectorAll('button');
        for (const btn of buttons) {
            const text = btn.textContent.trim();
            if (/credit/i.test(text)) return text;
        }
        return 'not found';
    }''')
    print(f"    {credits_text}")
    
    # Upload audio influence
    print(f"\n[4] Uploading audio influence: {os.path.basename(mp3_path)}...")
    try:
        audio_tab = page.locator('text=Audio').first
        if audio_tab.is_visible(timeout=5000):
            audio_tab.click(force=True)
            print("    Clicked Audio tab")
            time.sleep(3)
        
        file_input = page.locator('input[type="file"]').first
        file_input.set_input_files(mp3_path)
        print(f"    File uploaded!")
        
        # Wait for processing
        print("    Waiting for audio processing...")
        for i in range(30):
            time.sleep(2)
            status = page.evaluate(r'''() => {
                const text = document.body.innerText;
                if (text.includes('Adventist Youth')) return 'title_found';
                const audio = document.querySelector('audio');
                return audio ? 'audio_player' : 'waiting';
            }''')
            if status in ('title_found', 'audio_player'):
                print(f"    Processed after {(i+1)*2}s! ({status})")
                break
            if i % 5 == 4:
                print(f"    Still processing... ({(i+1)*2}s)")
        time.sleep(5)
    except Exception as e:
        print(f"    Audio upload error: {e}")
    
    # Set prompt via React fiber on the DESCRIPTION textarea
    prompt = ("Deep house instrumental, four on the floor kick drum, "
              "atmospheric pads, melodic synth leads, inspired by this hymn melody")
    print(f"\n[5] Setting prompt: {prompt[:60]}...")
    
    result = page.evaluate('''(prompt) => {
        const textareas = document.querySelectorAll('textarea');
        let descTextarea = null;
        for (const ta of textareas) {
            const ph = (ta.placeholder || '').toLowerCase();
            if (ph.includes('describe') || ph.includes('sound you want')) {
                descTextarea = ta;
                break;
            }
        }
        if (!descTextarea) descTextarea = textareas[textareas.length - 1];
        if (!descTextarea) return "no textarea";
        
        const propsKey = Object.keys(descTextarea).find(k => k.startsWith('__reactProps$'));
        if (propsKey) {
            const props = descTextarea[propsKey];
            if (props && props.onChange) {
                props.onChange({
                    target: { value: prompt },
                    currentTarget: { value: prompt },
                    persist: () => {},
                });
                return "ok: " + descTextarea.placeholder;
            }
        }
        // Fallback
        const setter = Object.getOwnPropertyDescriptor(
            window.HTMLTextAreaElement.prototype, 'value'
        ).set;
        setter.call(descTextarea, prompt);
        descTextarea.dispatchEvent(new Event('input', { bubbles: true }));
        return "fallback: " + descTextarea.placeholder;
    }''', prompt)
    print(f"    Result: {result}")
    time.sleep(3)
    
    # Check Create button
    create_btn = page.locator('button[aria-label*="Create"]').first
    btn_text = (create_btn.text_content() or '').strip()
    disabled = create_btn.is_disabled()
    print(f"\n[6] Create button: disabled={disabled} text='{btn_text}'")
    
    if 'out of credit' in btn_text.lower():
        print("\n    OUT OF CREDITS! Wait for daily reset or upgrade at suno.com")
        browser.close()
        sys.exit(1)
    
    # Toggle Instrumental
    print("\n[7] Toggling Instrumental...")
    try:
        instr = page.locator('button:has-text("Instrumental")').first
        instr.click(force=True)
        time.sleep(1)
        print("    Toggled!")
    except:
        print("    Could not toggle (may already be set)")
    
    # Re-check
    disabled = create_btn.is_disabled()
    print(f"    Create disabled: {disabled}")
    
    # Click Create and wait for generation response
    if not disabled:
        print("\n[8] Clicking Create...")
        
        def is_generate_resp(resp):
            return '/api/generate/v2' in resp.url and resp.status == 200
        
        try:
            with page.expect_response(is_generate_resp, timeout=300000) as resp_info:
                create_btn.click(force=True, timeout=10000)
                print("    Clicked! Waiting for generation...")
            
            resp = resp_info.value
            print(f"    Response: {resp.status}")
            data = resp.json()
            clips = data if isinstance(data, list) else [data]
            for c in clips:
                cid = c.get('id')
                if cid:
                    clip_ids.append(cid)
                    print(f"    Clip: {cid} status={c.get('status', '?')}")
        except Exception as e:
            print(f"    Error: {e}")
        
        # Poll for completion and download
        if clip_ids and session_token:
            print(f"\n[9] Polling for {len(clip_ids)} clips...")
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
                            print(f"\n    === COMPLETE after {(i+1)*5}s! ===")
                            for c in clips:
                                au = c.get('audio_url', '')
                                title = c.get('title', '')
                                dur = c.get('metadata', {}).get('duration', 0)
                                print(f"    Clip: title='{title}' dur={dur}s")
                                if au:
                                    try:
                                        ar = requests.get(au, timeout=30)
                                        if ar.status_code == 200:
                                            safe = (title or 'suno_track').replace(' ', '_').replace('/', '_')
                                            out = f"hymn_remaker/output/{safe}_suno.mp3"
                                            with open(out, 'wb') as f:
                                                f.write(ar.content)
                                            sz = len(ar.content) / 1024
                                            print(f"    Downloaded: {out} ({sz:.0f} KB)")
                                    except Exception as e:
                                        print(f"    Download error: {e}")
                            with open('suno_result.json', 'w') as f:
                                json.dump(clips, f, indent=2, default=str)
                            break
                    elif r.status_code == 401:
                        print("    401 - token expired")
                        break
                except Exception as e:
                    if i % 4 == 3:
                        print(f"    Error: {e}")
        elif not clip_ids:
            print("    No clip IDs - waiting for clips to appear in browser...")
            time.sleep(60)
    else:
        print("\n    Cannot generate - button is disabled")
    
    time.sleep(5)
    browser.close()
    print("\n[DONE]")
