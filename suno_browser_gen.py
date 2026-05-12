"""Suno browser automation - generate a track via Playwright."""
import time, json, os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv(override=True)

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

def generate_suno_track(prompt, make_instrumental=True, max_wait=300):
    """Generate a track via Suno browser automation."""
    
    stealth = Stealth()
    clip_ids = []
    turnstile_token = None
    
    with sync_playwright() as p:
        stealth.hook_playwright_context(p)
        
        browser = p.chromium.launch(headless=False, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width': 1280, 'height': 720})
        
        # Set auth cookies
        session_token = os.environ.get('SUNO_SESSION_TOKEN', '')
        client_token = os.environ.get('SUNO_CLIENT_TOKEN', '')
        context.add_cookies([
            {'name': '__session', 'value': session_token, 'domain': '.suno.com', 'path': '/'},
            {'name': '__client', 'value': client_token, 'domain': '.suno.com', 'path': '/'},
        ])
        
        page = context.new_page()
        
        # Track generate requests
        def handle_request(request):
            nonlocal turnstile_token
            if '/api/generate/v2' in request.url and request.method == 'POST':
                print(f'[REQUEST] POST generate')
                if request.post_data:
                    try:
                        data = json.loads(request.post_data)
                        token = data.get('token', '')
                        if token and len(str(token)) > 20:
                            turnstile_token = token
                            print(f'[TOKEN] Captured: {str(token)[:50]}...')
                    except:
                        pass
        
        def handle_response(response):
            if '/api/generate/v2' in response.url and response.status == 200:
                print(f'[RESPONSE] 200 OK')
                try:
                    data = response.json()
                    clips = data if isinstance(data, list) else [data]
                    for clip in clips:
                        cid = clip.get('id')
                        if cid:
                            clip_ids.append(cid)
                            print(f'[CLIP] ID: {cid} status: {clip.get("status", "?")}')
                except Exception as e:
                    print(f'[ERROR] Parse: {e}')
            elif '/api/generate/v2' in response.url and response.status >= 400:
                print(f'[ERROR] Generate failed: {response.status}')
        
        page.on('request', handle_request)
        page.on('response', handle_response)
        
        # Load create page
        print('[NAV] Loading suno.com/create...')
        page.goto('https://suno.com/create', timeout=30000, wait_until='domcontentloaded')
        time.sleep(10)
        
        # Fill description
        print('[INPUT] Typing prompt...')
        textarea = page.locator('textarea:visible').first
        textarea.click()
        time.sleep(0.5)
        page.keyboard.press('Control+a')
        time.sleep(0.3)
        page.keyboard.type(prompt, delay=20)
        time.sleep(2)
        
        # Toggle Instrumental
        if make_instrumental:
            print('[INPUT] Toggling Instrumental...')
            try:
                instr = page.locator('text=Instrumental').first
                if instr.is_visible(timeout=5000):
                    instr.click()
                    time.sleep(1)
            except:
                print('[WARN] Could not toggle Instrumental')
        
        # Click Create
        print('[ACTION] Clicking Create...')
        try:
            create_btn = page.locator('button[aria-label*="Create"]').first
            for i in range(20):
                if not create_btn.is_disabled():
                    break
                time.sleep(1)
            
            create_btn.click(timeout=30000)
            print('[ACTION] Create button clicked! Waiting for Turnstile + generate...')
        except Exception as e:
            print(f'[ERROR] Create click failed: {e}')
            page.screenshot(path='suno_error_create.png')
            browser.close()
            return None, None, []
        
        # Wait for generation to start (Turnstile can take up to 2 min)
        print('[WAIT] Waiting for Turnstile to solve and generate request...')
        for i in range(max_wait):
            time.sleep(1)
            if clip_ids:
                print(f'[SUCCESS] Generation started after {i+1}s! Clips: {clip_ids}')
                break
            if i % 30 == 29:
                print(f'[WAIT] Still waiting... ({i+1}s)')
        
        if not clip_ids:
            print('[FAIL] No clip IDs received after max wait')
            page.screenshot(path='suno_fail.png')
            browser.close()
            return None, None, []
        
        # Poll for completion via API
        print('[POLL] Waiting for clips to complete...')
        completed_clips = []
        
        for i in range(60):
            import requests as req
            headers = {
                'Authorization': f'Bearer {session_token}',
                'Cookie': f'__session={session_token}; __client={client_token}',
            }
            try:
                ids_param = ','.join(clip_ids)
                resp = req.get(
                    f'https://studio-api.prod.suno.com/api/get/?ids={ids_param}',
                    headers=headers, timeout=10
                )
                if resp.status_code == 200:
                    clips_data = resp.json()
                    if isinstance(clips_data, list):
                        all_done = all(c.get('status') in ('complete', 'completed') for c in clips_data)
                        has_audio = any(c.get('audio_url') for c in clips_data)
                        if all_done or has_audio:
                            print(f'[POLL] Clips complete after {(i+1)*5}s!')
                            completed_clips = clips_data
                            with open('suno_completed_clips.json', 'w') as f:
                                json.dump(clips_data, f, indent=2, default=str)
                            break
                        statuses = [c.get('status', '?') for c in clips_data]
                        if i % 4 == 3:
                            print(f'[POLL] Status: {statuses}')
            except Exception as e:
                if i % 4 == 3:
                    print(f'[POLL] Error: {e}')
            
            time.sleep(5)
        
        # Download audio if available
        audio_urls = []
        for clip in completed_clips:
            url = clip.get('audio_url', '')
            if url:
                audio_urls.append(url)
                print(f'[AUDIO] Clip {clip.get("id", "?")[:8]}: {url[:80]}...')
        
        page.screenshot(path='suno_generation_result.png')
        time.sleep(3)
        browser.close()
    
    return clip_ids, turnstile_token, completed_clips

if __name__ == '__main__':
    prompt = sys.argv[1] if len(sys.argv) > 1 else 'Deep house instrumental, four on the floor kick, atmospheric pads'
    
    clip_ids, token, clips = generate_suno_track(prompt, make_instrumental=True)
    
    print(f'\n=== RESULT ===')
    print(f'Clip IDs: {clip_ids}')
    print(f'Turnstile token: {"Yes" if token else "No"}')
    print(f'Completed clips: {len(clips)}')
    
    if clips:
        for clip in clips:
            cid = clip.get('id', '?')
            status = clip.get('status', '?')
            audio_url
