"""
Suno AI Music Remaker - Deep House generation via Suno web API.

Uses the Suno AI API (studio-api.prod.suno.com) to generate Deep House
remixes of hymn MIDI renders. Two generation modes are supported:

1. API Mode (Direct): POST to /api/generate/v2-web/ with a valid
   Cloudflare Turnstile token. The token is obtained by solving
   an invisible Turnstile CAPTCHA challenge.

2. Browser Mode (Playwright): Automates the Suno web UI to fill in
   the prompt, toggle instrumental, and click Create. The browser
   handles the Turnstile challenge automatically. This is the
   recommended mode for reliability.

Authentication:
  Requires SUNO_SESSION_TOKEN + SUNO_CLIENT_TOKEN from suno.com cookies.
  1. Go to https://suno.com in your browser
  2. Open DevTools > Application > Cookies > suno.com
  3. Copy __session and __client cookie values
  4. Set SUNO_SESSION_TOKEN and SUNO_CLIENT_TOKEN in .env

API Endpoints (reverse-engineered from Suno web app):
  - Session:        GET  /api/session/
  - Captcha Check:  POST /api/c/check  {ctype: "generation"}
  - Generate:       POST /api/generate/v2-web/
  - Poll:           GET  /api/get/?ids=...
  - Feed:           GET  /api/feed/?page=1

Cloudflare Turnstile Sitekeys:
  - General:     0x4AAAAAABd64Cd9aq5C--VE
  - Generation:  0x4AAAAAADI7xDNyj-3LcIbi
  - Auth:        0x4AAAAAABtnpJo7aKMs9JLQ

Generate Payload Format (Simple mode):
  {
    "token": "<turnstile_token>",
    "gpt_description_prompt": "Deep house instrumental...",
    "mv": "chirp-auk-turbo",
    "prompt": "",
    "make_instrumental": true,
    "generation_type": "TEXT",
    "metadata": {
      "create_mode": "simple",
      "user_tier": "free",
      "lyrics_model": "default"
    }
  }

Generate Payload Format (Custom mode):
  {
    "token": "<turnstile_token>",
    "gpt_description_prompt": "description (if create-v1.5 flag)",
    "prompt": "lyrics text",
    "tags": "deep house, electronic",
    "negative_tags": "",
    "mv": "chirp-auk-turbo",
    "title": "Song Title",
    "make_instrumental": true,
    "generation_type": "TEXT",
    "metadata": {...}
  }

Workflow:
  1. Check captcha requirement (POST /api/c/check)
  2. Obtain Turnstile token (Playwright or direct)
  3. POST /api/generate/v2-web/ with payload + token
  4. Poll /api/get/?ids=... until songs are complete
  5. Download the best generated audio
  6. Save as remake WAV
"""

import os
import sys
import time
import json
import base64
import logging
import subprocess
import tempfile
import shutil
import requests
from pathlib import Path

from hymn_remaker import settings

logger = logging.getLogger(__name__)

# Suno API endpoints
SUNO_BASE_URL = "https://studio-api.prod.suno.com"
GEN_ENDPOINT = "/api/generate/v2-web/"  # Web UI endpoint (requires Turnstile)
SESSION_ENDPOINT = "/api/session/"
CAPTCHA_CHECK_ENDPOINT = "/api/c/check"
FEED_ENDPOINT = "/api/feed/"

# Cloudflare Turnstile sitekeys (from Suno web app JS)
TURNSTILE_SITEKEY_GEN = "0x4AAAAAADI7xDNyj-3LcIbi"
TURNSTILE_SITEKEY_AUTH = "0x4AAAAAABtnpJo7aKMs9JLQ"
TURNSTILE_SITEKEY_GENERAL = "0x4AAAAAABd64Cd9aq5C--VE"

# Default model version (v3.5 is the highest free users can use)
DEFAULT_MODEL_VERSION = "chirp-auk-turbo"  # v4.5 - current Suno default

# Polling settings
POLL_INTERVAL = 5   # seconds between status checks
POLL_TIMEOUT = 300  # max seconds to wait for generation (5 min)


class SunoRemaker:
    """
    Generate Deep House remixes of hymn audio using Suno AI.

    Supports two modes:
    - API mode: Direct HTTP requests with Turnstile token
    - Browser mode: Playwright automation of the Suno web UI
    """

    def __init__(self, session_token=None, client_token=None, model_version=None):
        """
        Initialize the Suno Remaker.

        Args:
            session_token (str): Suno __session JWT from browser cookies.
            client_token (str): Suno __client JWT from browser cookies.
            model_version (str): Suno model version. Defaults to chirp-v3-5.
        """
        self.session_token = session_token or os.environ.get("SUNO_SESSION_TOKEN", "")
        self.client_token = client_token or os.environ.get("SUNO_CLIENT_TOKEN", "")
        self.model_version = model_version or os.environ.get("SUNO_MODEL_VERSION", DEFAULT_MODEL_VERSION)
        self.base_url = os.environ.get("SUNO_BASE_URL", SUNO_BASE_URL)

        if not self.session_token:
            logger.warning("SUNO_SESSION_TOKEN not set. SunoRemaker will not function.")
            logger.warning("Get your token from suno.com browser cookies (DevTools > Application > Cookies)")
        else:
            logger.info(f"SunoRemaker initialized with model {self.model_version}")

        # FFmpeg path from settings
        self.ffmpeg_bin = settings.FFMPEG_BIN

    def is_available(self):
        """Check if Suno API is configured and session is valid."""
        if not self.session_token:
            return False
        try:
            headers = self._get_headers()
            resp = requests.get(
                f"{self.base_url}{SESSION_ENDPOINT}",
                headers=headers, timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                user = data.get("user", {})
                handle = user.get("handle", "")
                return bool(handle)
            return False
        except Exception:
            return False

    def _get_headers(self):
        """Build request headers with auth tokens."""
        headers = {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Authorization": f"Bearer {self.session_token}",
            "Content-Type": "application/json",
            "Origin": "https://suno.com",
            "Referer": "https://suno.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
        }
        # Set cookies if we have both tokens
        cookie_parts = []
        if self.session_token:
            cookie_parts.append(f"__session={self.session_token}")
        if self.client_token:
            cookie_parts.append(f"__client={self.client_token}")
        if cookie_parts:
            headers["Cookie"] = "; ".join(cookie_parts)
        return headers

    def check_captcha(self):
        """Check if CAPTCHA is required for generation.

        Returns:
            dict: {"required": bool, "captcha_version": int}
        """
        headers = self._get_headers()
        try:
            resp = requests.post(
                f"{self.base_url}{CAPTCHA_CHECK_ENDPOINT}",
                json={"ctype": "generation"},
                headers=headers, timeout=10
            )
            if resp.status_code == 200:
                return resp.json()
            return {"required": True, "captcha_version": 1}
        except Exception as e:
            logger.warning(f"Captcha check failed: {e}")
            return {"required": True, "captcha_version": 1}

    def get_session_info(self):
        """Get current session info from Suno API.

        Returns:
            dict: Session data including user info, credits, and available models.
        """
        headers = self._get_headers()
        resp = requests.get(
            f"{self.base_url}{SESSION_ENDPOINT}",
            headers=headers, timeout=15
        )
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 401:
            raise RuntimeError("SUNO_SESSION_TOKEN expired. Get a new one from suno.com")
        else:
            raise RuntimeError(f"Session check failed: {resp.status_code} {resp.text[:200]}")

    def get_feed(self, page=1):
        """Get user's song feed.

        Returns:
            list: List of clip dictionaries from the user's feed.
        """
        headers = self._get_headers()
        resp = requests.get(
            f"{self.base_url}{FEED_ENDPOINT}?page={page}",
            headers=headers, timeout=15
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            raise RuntimeError(f"Feed request failed: {resp.status_code}")

    # -------------------------------------------------------------------------
    # Turnstile Token Acquisition
    # -------------------------------------------------------------------------

    def get_turnstile_token(self, timeout=30):
        """Obtain a Cloudflare Turnstile token using Playwright.

        Opens a headless browser to the Suno create page, lets the
        invisible Turnstile widget auto-solve, and captures the token
        from the generate request.

        Args:
            timeout (int): Max seconds to wait for token.

        Returns:
            str: Valid Turnstile token, or None if failed.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && python -m playwright install chromium")
            return None

        captured_token = None

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
            )
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            )

            # Set auth cookies
            if self.session_token:
                context.add_cookies([
                    {'name': '__session', 'value': self.session_token, 'domain': '.suno.com', 'path': '/'},
                ])
            if self.client_token:
                context.add_cookies([
                    {'name': '__client', 'value': self.client_token, 'domain': '.suno.com', 'path': '/'},
                ])

            page = context.new_page()
            page.add_init_script('Object.defineProperty(navigator, "webdriver", {get: () => undefined})')

            # Intercept the generate request to capture the token
            def handle_request(request):
                nonlocal captured_token
                if GEN_ENDPOINT in request.url and request.method == 'POST':
                    if request.post_data:
                        try:
                            data = json.loads(request.post_data)
                            token = data.get('token', '')
                            if token and len(str(token)) > 20:
                                captured_token = token
                                logger.info(f"Captured Turnstile token: {str(token)[:40]}...")
                        except Exception:
                            pass

            page.on('request', handle_request)

            # Navigate to create page
            logger.info("Opening Suno create page to harvest Turnstile token...")
            page.goto('https://suno.com/create', timeout=30000, wait_until='domcontentloaded')

            # Wait for the page to fully load
            time.sleep(8)

            # Fill in the description
            try:
                textarea = page.locator('textarea:visible').first
                textarea.click()
                time.sleep(0.3)
                page.keyboard.press('Control+a')
                time.sleep(0.2)
                page.keyboard.type('Deep house instrumental test', delay=30)
                time.sleep(1)

                # Toggle Instrumental
                instr = page.locator('text=Instrumental').first
                if instr.is_visible(timeout=3000):
                    instr.click()
                    time.sleep(1)

                # Click Create to trigger the Turnstile
                create_btn = page.locator('button[aria-label*="Create"]').first
                if create_btn.is_visible(timeout=5000):
                    create_btn.click(timeout=10000)

            except Exception as e:
                logger.warning(f"Error during browser interaction: {e}")

            # Wait for token
            start = time.time()
            while time.time() - start < timeout:
                if captured_token:
                    break
                time.sleep(1)

            browser.close()

        if captured_token:
            logger.info(f"Turnstile token captured successfully ({len(str(captured_token))} chars)")
        else:
            logger.warning("Failed to capture Turnstile token")

        return captured_token

    # -------------------------------------------------------------------------
    # Generation via API
    # -------------------------------------------------------------------------

    def _upload_audio(self, audio_path):
        """Upload an audio file to Suno for use as influence content.

        Follows Suno's upload flow:
        1. POST /api/uploads/audio/ to get presigned S3 URL
        2. Upload file to S3
        3. POST /api/uploads/audio/{id} to confirm
        4. Poll GET /api/uploads/audio/{id} until complete

        Args:
            audio_path (str): Path to the audio file (MP3 or WAV).

        Returns:
            dict: Upload info with 'id', 's3_id', 'title', or None on failure.
        """
        if not self.session_token:
            logger.error("No session token for audio upload")
            return None

        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return None

        ext = os.path.splitext(audio_path)[1].lstrip('.').lower()
        if ext not in ('mp3', 'wav', 'm4a', 'ogg', 'flac'):
            logger.warning(f"Unsupported audio format: {ext}")
            ext = 'mp3'

        headers = self._get_headers()
        base = self.base_url

        # Step 1: Request presigned upload URL
        logger.info(f"Requesting audio upload URL for {os.path.basename(audio_path)}...")
        try:
            resp = requests.post(
                f"{base}/api/uploads/audio/",
                json={"extension": ext, "upload_type": "file_upload"},
                headers=headers, timeout=15
            )
            if resp.status_code != 200:
                logger.error(f"Upload URL request failed: {resp.status_code} {resp.text[:200]}")
                return None

            upload_info = resp.json()
            upload_id = upload_info.get("id")
            upload_url = upload_info.get("url", "")
            fields = upload_info.get("fields", {})

            if not upload_id:
                logger.error("No upload ID returned")
                return None

            logger.info(f"Upload ID: {upload_id}")
        except Exception as e:
            logger.error(f"Upload URL request error: {e}")
            return None

        # Step 2: Upload file to S3
        logger.info(f"Uploading to S3...")
        try:
            with open(audio_path, 'rb') as f:
                file_data = f.read()

            s3_files = {"file": (os.path.basename(audio_path), file_data, f"audio/{ext}")}
            s3_data = dict(fields) if fields else {}
            # Remove Content-Type from fields if present (we set it in files)
            s3_data.pop("Content-Type", None)

            s3_resp = requests.post(upload_url, data=s3_data, files=s3_files, timeout=60)
            if s3_resp.status_code not in (200, 201, 204):
                logger.warning(f"S3 upload returned {s3_resp.status_code}")
        except Exception as e:
            logger.error(f"S3 upload error: {e}")
            return None

        # Step 3: Confirm upload
        logger.info("Confirming upload...")
        try:
            resp = requests.post(
                f"{base}/api/uploads/audio/{upload_id}",
                json={
                    "upload_type": "file_upload",
                    "upload_filename": os.path.basename(audio_path),
                },
                headers=headers, timeout=15
            )
            if resp.status_code != 200:
                logger.warning(f"Upload confirm: {resp.status_code}")
        except Exception as e:
            logger.warning(f"Upload confirm error: {e}")

        # Step 4: Poll until complete
        logger.info("Waiting for audio processing...")
        for i in range(30):
            time.sleep(2)
            try:
                resp = requests.get(
                    f"{base}/api/uploads/audio/{upload_id}",
                    headers=headers, timeout=10
                )
                if resp.status_code == 200:
                    info = resp.json()
                    status = info.get("status", "")
                    if status == "complete":
                        logger.info(f"Audio upload complete! s3_id={info.get('s3_id', '?')}")
                        return info
                    elif status in ("failed", "error", "rejected"):
                        logger.error(f"Audio upload failed: {status}")
                        return None
                    elif i % 5 == 4:
                        logger.info(f"  Status: {status} ({(i+1)*2}s)")
            except Exception as e:
                if i % 5 == 4:
                    logger.warning(f"  Poll error: {e}")

        logger.error("Audio upload timed out")
        return None

    def _generate_songs_api(self, prompt, turnstile_token=None, make_instrumental=True,
                            tags=None, title=None, generation_type="TEXT"):
        """Submit a song generation request to Suno via the v2-web API.

        Args:
            prompt (str): Text description of the song to generate.
            turnstile_token (str): Cloudflare Turnstile token (required for v2-web).
            make_instrumental (bool): Whether to generate instrumental only.
            tags (str): Genre tags (e.g., "deep house, electronic").
            title (str): Song title.
            generation_type (str): One of TEXT, AUDIO, IMAGE, VIDEO, TWITTER, SIMPLE_REMIX.

        Returns:
            list: List of clip dictionaries from the API response.

        Raises:
            RuntimeError: If the API request fails.
        """
        if not self.session_token:
            raise RuntimeError("SUNO_SESSION_TOKEN not configured")

        # Build the generation payload (Simple mode format)
        payload = {
            "token": turnstile_token if turnstile_token else None,
            "gpt_description_prompt": prompt,
            "mv": self.model_version,
            "prompt": "",
            "make_instrumental": make_instrumental,
            "generation_type": generation_type,
            "metadata": {
                "create_mode": "simple",
                "user_tier": "free",
                "lyrics_model": "default",
            },
        }

        # Add optional fields
        if tags:
            payload["tags"] = tags
        if title:
            payload["title"] = title

        logger.info(f"Submitting Suno generation request via API...")
        logger.info(f"  Prompt: {prompt[:100]}...")
        logger.info(f"  Model: {self.model_version}")
        logger.info(f"  Instrumental: {make_instrumental}")
        logger.info(f"  Has Turnstile token: {bool(turnstile_token)}")

        headers = self._get_headers()
        url = f"{self.base_url}{GEN_ENDPOINT}"

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code == 401:
                raise RuntimeError("SUNO_SESSION_TOKEN is invalid or expired. Get a new one from suno.com")
            if response.status_code == 402:
                raise RuntimeError("Suno credits exhausted. Wait for daily reset or upgrade plan.")
            if response.status_code == 429:
                raise RuntimeError("Suno rate limit hit. Waiting before retry.")

            # Check for token validation error (missing/invalid Turnstile token)
            if response.status_code == 422:
                try:
                    error_data = response.json()
                    error_type = error_data.get("error_type", "")
                    if error_type == "token_validation_failed":
                        raise RuntimeError(
                            "Turnstile token validation failed. Need a fresh token. "
                            "Use get_turnstile_token() or browser automation mode."
                        )
                    # Check for Pydantic validation errors
                    detail = error_data.get("detail", "")
                    if "params" in str(detail) and "prompt" in str(detail):
                        raise RuntimeError(
                            "API payload format error. The Suno API may have changed. "
                            f"Detail: {str(detail)[:300]}"
                        )
                except (json.JSONDecodeError, AttributeError):
                    pass
                raise RuntimeError(f"Suno API validation error 422: {response.text[:300]}")

            if response.status_code == 503:
                raise RuntimeError("Suno API is temporarily unavailable (503). Try again later.")
            if response.status_code != 200:
                raise RuntimeError(f"Suno API error {response.status_code}: {response.text[:300]}")

            clips = response.json()
            if isinstance(clips, dict) and "clips" in clips:
                clips = clips["clips"]

            logger.info(f"Suno generation submitted: {len(clips) if isinstance(clips, list) else 1} clip(s)")
            if isinstance(clips, list):
                for clip in clips:
                    clip_id = clip.get("id", "unknown")
                    logger.info(f"  Clip ID: {clip_id}")

            return clips

        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(f"Cannot connect to Suno API: {e}")
        except requests.exceptions.Timeout:
            raise RuntimeError("Suno API request timed out")

    # -------------------------------------------------------------------------
    # Generation via Browser Automation (Playwright)
    # -------------------------------------------------------------------------

    def _generate_songs_browser(self, prompt, make_instrumental=True, timeout=300,
                                  audio_influence_path=None):
        """Generate songs using Playwright browser automation with stealth.

        Automates the Suno web UI to create a song. Uses playwright-stealth
        to bypass Cloudflare Turnstile bot detection.

        KEY FINDINGS from reverse engineering:
        - The endpoint is /api/generate/v2-web/ (not /v2/)
        - Turnstile token can be null when using proper session cookies
        - The description textarea has placeholder "Describe the sound you want"
        - React state must be updated via __reactProps$ onChange handler
        - Audio upload: POST /api/uploads/audio/ → S3 presigned URL → poll status
        - Button shows "Out of Credits" when credits are exhausted

        Args:
            prompt (str): Text description for the song.
            make_instrumental (bool): Generate without vocals.
            timeout (int): Max seconds to wait for generation (default 300).
            audio_influence_path (str): Path to MP3/WAV to upload as influence.

        Returns:
            list: List of clip dictionaries with clip IDs.

        Raises:
            RuntimeError: If browser automation fails or credits exhausted.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError("Playwright not installed. Run: pip install playwright && python -m playwright install chromium")

        try:
            from playwright_stealth import Stealth
            use_stealth = True
        except ImportError:
            logger.warning("playwright-stealth not installed. Turnstile may fail.")
            use_stealth = False

        captured_clips = []

        with sync_playwright() as p:
            # Apply stealth to bypass Turnstile bot detection
            if use_stealth:
                stealth = Stealth()
                stealth.hook_playwright_context(p)

            browser = p.chromium.launch(headless=False, args=['--no-sandbox'])
            context = browser.new_context(viewport={'width': 1280, 'height': 720})

            # Set auth cookies on all relevant domains
            if self.session_token:
                context.add_cookies([
                    {'name': '__session', 'value': self.session_token,
                     'domain': '.suno.com', 'path': '/'},
                    {'name': '__session', 'value': self.session_token,
                     'domain': 'auth.suno.com', 'path': '/'},
                ])
            if self.client_token:
                context.add_cookies([
                    {'name': '__client', 'value': self.client_token,
                     'domain': '.suno.com', 'path': '/'},
                    {'name': '__client', 'value': self.client_token,
                     'domain': 'auth.suno.com', 'path': '/'},
                ])

            page = context.new_page()

            # Response filter for page.expect_response
            def is_generate_response(response):
                return '/api/generate/v2' in response.url and response.status == 200

            # Navigate to create page
            logger.info("Opening Suno create page with stealth...")
            page.goto('https://suno.com/create', timeout=30000,
                      wait_until='domcontentloaded')
            time.sleep(15)

            # ---- Dismiss overlays/modals ----
            for _ in range(3):
                page.keyboard.press('Escape')
                time.sleep(0.5)
            try:
                close_btn = page.locator('[aria-label="Close"]')
                if close_btn.count() > 0:
                    close_btn.first.click(force=True)
                    time.sleep(1)
            except Exception:
                pass

            # ---- Check for "Out of Credits" ----
            create_btn = page.locator('button[aria-label*="Create"]').first
            btn_text = create_btn.text_content() or ''
            if 'out of credit' in btn_text.lower():
                browser.close()
                raise RuntimeError(
                    "Suno account is out of credits. Wait for daily reset "
                    "or upgrade the plan at suno.com."
                )

            # ---- Audio Influence Upload ----
            if audio_influence_path and os.path.exists(audio_influence_path):
                logger.info(f"Uploading audio influence: {audio_influence_path}")
                try:
                    # Click the "Audio" tab to reveal upload UI
                    audio_tab = page.locator('text=Audio').first
                    if audio_tab.is_visible(timeout=5000):
                        audio_tab.click(force=True)
                        logger.info("Clicked Audio tab")
                        time.sleep(3)

                    # Upload via file input
                    file_input = page.locator('input[type="file"]').first
                    file_input.set_input_files(audio_influence_path)
                    logger.info(f"Uploaded audio: {os.path.basename(audio_influence_path)}")

                    # Wait for upload to complete (processing → moderation → complete)
                    logger.info("Waiting for audio upload to process...")
                    for i in range(30):
                        time.sleep(2)
                        # Check upload status via JS
                        status = page.evaluate('''() => {
                            const el = document.querySelector('[data-upload-status]');
                            return el ? el.getAttribute('data-upload-status') : null;
                        }''')
                        if status == 'complete':
                            logger.info("Audio upload complete!")
                            break
                        if i % 5 == 4:
                            logger.info(f"Upload still processing... ({(i+1)*2}s)")
                    time.sleep(3)
                except Exception as e:
                    logger.warning(f"Audio influence upload failed: {e}")
                    logger.info("Continuing without audio influence...")

            # ---- Set Prompt via React Fiber ----
            # CRITICAL: The description textarea has placeholder
            # "Describe the sound you want" - we must target THIS one,
            # not the lyrics textarea ("Write some lyrics or leave blank...").
            # We use React's __reactProps$ to call onChange directly,
            # which properly updates React's internal state.
            logger.info(f"Setting prompt via React fiber: {prompt[:60]}...")
            try:
                result = page.evaluate(f'''() => {{
                    const textareas = document.querySelectorAll('textarea');
                    let descTextarea = null;
                    for (const ta of textareas) {{
                        const ph = (ta.placeholder || '').toLowerCase();
                        if (ph.includes('describe') || ph.includes('sound you want')) {{
                            descTextarea = ta;
                            break;
                        }}
                    }}
                    // Fallback: last textarea (typically the description)
                    if (!descTextarea) {{
                        descTextarea = textareas[textareas.length - 1];
                    }}
                    if (!descTextarea) return "no description textarea found";

                    const prompt = {json.dumps(prompt)};
                    const propsKey = Object.keys(descTextarea).find(k =>
                        k.startsWith('__reactProps$')
                    );
                    if (propsKey) {{
                        const props = descTextarea[propsKey];
                        if (props && props.onChange) {{
                            props.onChange({{
                                target: {{ value: prompt }},
                                currentTarget: {{ value: prompt }},
                                persist: () => {{}},
                            }});
                            return "ok: " + descTextarea.placeholder;
                        }}
                    }}
                    // Fallback: native setter + events
                    const setter = Object.getOwnPropertyDescriptor(
                        window.HTMLTextAreaElement.prototype, 'value'
                    ).set;
                    setter.call(descTextarea, prompt);
                    descTextarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    descTextarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return "fallback: " + descTextarea.placeholder;
                }}''')
                logger.info(f"React fiber result: {result}")
                time.sleep(3)
            except Exception as e:
                logger.warning(f"React fiber approach failed: {e}")
                # Fallback: use fill() on the visible textarea
                try:
                    textarea = page.locator('textarea:visible').last
                    textarea.click(force=True)
                    time.sleep(0.3)
                    textarea.fill(prompt)
                    logger.info("Used fill() as fallback")
                    time.sleep(2)
                except Exception as e2:
                    logger.error(f"All prompt input methods failed: {e2}")

            # ---- Toggle Instrumental ----
            if make_instrumental:
                try:
                    instr = page.locator('button:has-text("Instrumental")').first
                    if instr.is_visible(timeout=5000):
                        instr.click(force=True)
                        logger.info("Clicked Instrumental toggle")
                        time.sleep(1)
                except Exception as e:
                    logger.debug(f"Instrumental toggle: {e}")

            # ---- Click Create and Wait for Response ----
            create_btn = page.locator('button[aria-label*="Create"]').first
            if create_btn.is_disabled():
                btn_text = create_btn.text_content() or ''
                if 'out of credit' in btn_text.lower():
                    browser.close()
                    raise RuntimeError(
                        "Suno account is out of credits. Wait for daily reset."
                    )
                else:
                    logger.warning(f"Create button disabled: {btn_text}")

            if not create_btn.is_disabled():
                logger.info("Clicking Create button...")
                try:
                    with page.expect_response(is_generate_response, timeout=timeout * 1000) as resp_info:
                        create_btn.click(force=True, timeout=10000)
                        logger.info("Create button clicked! Waiting for generate response...")

                    response = resp_info.value
                    logger.info(f"Generate response: {response.status}")

                    try:
                        data = response.json()
                        clips = data if isinstance(data, list) else [data]
                        for clip in clips:
                            cid = clip.get('id')
                            if cid:
                                captured_clips.append(clip)
                                logger.info(f"Clip captured: {cid} status={clip.get('status', '?')}")
                    except Exception as e:
                        logger.error(f"Error parsing generate response: {e}")

                except Exception as e:
                    logger.error(f"Generate response timeout or error: {e}")
                    # Try to capture via event listeners as fallback
                    logger.info("Trying event listener fallback...")
            else:
                logger.error("Create button is disabled, cannot generate")

            # Keep browser open briefly for any pending requests
            time.sleep(3)
            browser.close()

        if not captured_clips:
            raise RuntimeError(
                "Browser automation failed - no clips generated. "
                "Possible causes: out of credits, Turnstile blocked, or prompt issue."
            )

        return captured_clips

    def _poll_songs(self, clip_ids):
        """Poll Suno API until songs are complete.

        Suno generates 2 clips per request. We poll until both are done,
        then return the completed clips.

        Args:
            clip_ids (list): List of clip IDs to poll.

        Returns:
            list: List of completed clip dictionaries.

        Raises:
            RuntimeError: If polling times out.
        """
        if not clip_ids:
            raise RuntimeError("No clip IDs to poll")

        ids_param = ",".join(clip_ids)
        headers = self._get_headers()
        start_time = time.time()

        logger.info(f"Polling Suno for {len(clip_ids)} clip(s)...")

        while True:
            elapsed = time.time() - start_time
            if elapsed > POLL_TIMEOUT:
                raise RuntimeError(f"Suno generation timed out after {POLL_TIMEOUT}s")

            try:
                response = requests.get(
                    f"{self.base_url}/api/get/?ids={ids_param}",
                    headers=headers, timeout=15
                )
                if response.status_code != 200:
                    logger.warning(f"Suno poll returned {response.status_code}, retrying...")
                    time.sleep(POLL_INTERVAL)
                    continue

                clips = response.json()
                if isinstance(clips, list):
                    all_done = all(
                        clip.get("status") in ("complete", "completed")
                        for clip in clips
                    )
                else:
                    all_done = False

                if all_done:
                    logger.info(f"All clips complete after {elapsed:.0f}s")
                    return clips

                # Log progress
                for clip in clips if isinstance(clips, list) else []:
                    status = clip.get("status", "unknown")
                    clip_id = clip.get("id", "?")
                    if status == "error":
                        error_msg = clip.get("error_message", "unknown error")
                        logger.error(f"  Clip {clip_id} failed: {error_msg}")
                    elif status not in ("complete", "completed"):
                        logger.info(f"  Clip {clip_id}: {status}...")

            except requests.exceptions.RequestException as e:
                logger.warning(f"Poll request failed: {e}")

            time.sleep(POLL_INTERVAL)

    def _download_audio(self, clip, output_path):
        """Download the generated audio from a completed Suno clip.

        Suno provides audio_url (MP3). We download the MP3 and convert
        to WAV for pipeline compatibility.

        Args:
            clip (dict): Completed clip dictionary from Suno.
            output_path (str): Path to save the output WAV file.

        Returns:
            str: Path to the downloaded WAV file.

        Raises:
            RuntimeError: If download fails.
        """
        audio_url = clip.get("audio_url")
        if not audio_url:
            raise RuntimeError("Clip has no audio_url")

        logger.info(f"Downloading Suno audio from {audio_url[:80]}...")

        try:
            response = requests.get(audio_url, timeout=60, stream=True)
            response.raise_for_status()

            # Save as MP3 first
            mp3_path = output_path.rsplit(".", 1)[0] + "_suno.mp3"
            with open(mp3_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            mp3_size_mb = os.path.getsize(mp3_path) / (1024 * 1024)
            logger.info(f"Downloaded Suno MP3: {mp3_path} ({mp3_size_mb:.1f}MB)")

            # Convert MP3 to WAV for pipeline compatibility
            cmd = [
                self.ffmpeg_bin, "-y", "-i", mp3_path,
                "-codec:a", "pcm_s16le",
                "-ar", str(settings.SAMPLE_RATE),
                "-ac", "2", output_path
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg MP3->WAV failed: {result.stderr[-300:]}")

            # Clean up temp MP3
            try:
                os.remove(mp3_path)
            except OSError:
                pass

            wav_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            logger.info(f"Suno WAV saved: {output_path} ({wav_size_mb:.1f}MB)")
            return output_path

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to download Suno audio: {e}")

    def _select_best_clip(self, clips):
        """Select the best clip from the generated results.

        Suno generates 2 clips per request. We pick the one with the
        highest quality/relevance score if available.

        Args:
            clips (list): List of completed clip dictionaries.

        Returns:
            dict: The best clip.
        """
        if not clips:
            raise RuntimeError("No clips to select from")
        if len(clips) == 1:
            return clips[0]

        best = clips[0]
        for clip in clips[1:]:
            current_score = best.get("metadata_score", 0) or 0
            new_score = clip.get("metadata_score", 0) or 0
            if new_score > current_score:
                best = clip

        logger.info(f"Selected clip {best.get('id', '?')} as best result")
        return best

    # -------------------------------------------------------------------------
    # Main Entry Points
    # -------------------------------------------------------------------------

    def remake(self, wav_path, prompt, duration=30, make_instrumental=True,
               tags="deep house, electronic, club", keep_mp3=False,
               mode="auto", turnstile_token=None):
        """Generate a Deep House remake of a hymn using Suno AI.

        This is the main entry point for the pipeline. It supports two modes:
        - "api": Direct HTTP API calls (requires Turnstile token)
        - "browser": Playwright browser automation (handles Turnstile automatically)
        - "auto": Try API first, fall back to browser

        Args:
            wav_path (str): Path to the input WAV file (hymn base audio).
            prompt (str): Text prompt for the Deep House style.
            duration (int): Target duration in seconds.
            make_instrumental (bool): Generate without vocals (default True).
            tags (str): Genre tags for the generation.
            keep_mp3 (bool): Keep the intermediate MP3 file (default False).
            mode (str): Generation mode - "api", "browser", or "auto".
            turnstile_token (str): Pre-obtained Turnstile token (for API mode).

        Returns:
            str: Path to the generated remake WAV file.

        Raises:
            RuntimeError: If Suno API fails.
            FileNotFoundError: If input WAV doesn't exist.
        """
        if not self.session_token:
            raise RuntimeError("SunoRemaker not configured. Set SUNO_SESSION_TOKEN.")
        if not os.path.exists(wav_path):
            raise FileNotFoundError(f"Input WAV not found: {wav_path}")

        hymn_name = Path(wav_path).stem.replace("_base", "")
        logger.info(f"=== Suno Remake: {hymn_name} ===")

        full_prompt = (
            f"Create a {prompt} version inspired by this hymn melody. "
            f"Transform it into a club-ready deep house track with "
            f"four-on-the-floor kick, deep bass, atmospheric pads, "
            f"and subtle references to the original hymn's melody."
        )

        clips = None

        # Try API mode first (if auto or api)
        if mode in ("auto", "api"):
            try:
                # Get Turnstile token if not provided
                if not turnstile_token:
                    captcha = self.check_captcha()
                    if captcha.get("required"):
                        logger.info("CAPTCHA required, obtaining Turnstile token...")
                        turnstile_token = self.get_turnstile_token()

                clips = self._generate_songs_api(
                    prompt=full_prompt,
                    turnstile_token=turnstile_token,
                    make_instrumental=make_instrumental,
                    tags=tags,
                    title=f"{hymn_name} (Deep House Remix)",
                )
            except RuntimeError as e:
                logger.warning(f"API mode failed: {e}")
                if mode == "auto":
                    logger.info("Falling back to browser mode...")
                else:
                    raise

        # Prepare audio influence path (prefer MP3, fall back to WAV)
        audio_influence = None
        mp3_path = wav_path.rsplit('_base.wav', 1)[0] + '_base.mp3'
        if os.path.exists(mp3_path):
            audio_influence = mp3_path
            logger.info(f"Using MP3 as audio influence: {mp3_path}")
        elif os.path.exists(wav_path):
            audio_influence = wav_path
            logger.info(f"Using WAV as audio influence: {wav_path}")

        # Fall back to browser mode
        if clips is None and mode in ("auto", "browser"):
            clips = self._generate_songs_browser(
                prompt=full_prompt,
                make_instrumental=make_instrumental,
                audio_influence_path=audio_influence,
            )

        if not clips:
            raise RuntimeError("No clips generated")

        # Poll for completion
        clip_ids = [clip.get("id") for clip in clips if clip.get("id")]
        if not clip_ids:
            raise RuntimeError("Suno returned no clip IDs")

        completed_clips = self._poll_songs(clip_ids)

        # Filter out errored clips
        valid_clips = [
            c for c in completed_clips
            if c.get("status") != "error" and c.get("audio_url")
        ]
        if not valid_clips:
            raise RuntimeError("All Suno clips failed or have no audio_url")

        # Select best clip and download
        best_clip = self._select_best_clip(valid_clips)
        remake_wav = wav_path.rsplit("_base.wav", 1)[0] + "_remake.wav"
        self._download_audio(best_clip, remake_wav)

        logger.info(f"=== Suno Remake Complete: {remake_wav} ===")
        return remake_wav

    def remake_simple(self, prompt, make_instrumental=True, tags="deep house, electronic",
                      mode="auto", turnstile_token=None):
        """Generate a song from a text prompt only (no audio influence).

        Simpler version of remake() that doesn't require an input WAV.
        Useful for testing or generating standalone tracks.

        Args:
            prompt (str): Text description for the song.
            make_instrumental (bool): Generate without vocals.
            tags (str): Genre tags.
            mode (str): "api", "browser", or "auto".
            turnstile_token (str): Pre-obtained Turnstile token.

        Returns:
            list: List of completed clip dictionaries.
        """
        clips = None

        if mode in ("auto", "api"):
            try:
                if not turnstile_token:
                    captcha = self.check_captcha()
                    if captcha.get("required"):
                        turnstile_token = self.get_turnstile_token()

                clips = self._generate_songs_api(
                    prompt=prompt,
                    turnstile_token=turnstile_token,
                    make_instrumental=make_instrumental,
                    tags=tags,
                )
            except RuntimeError as e:
                logger.warning(f"API mode failed: {e}")
                if mode != "auto":
                    raise

        if clips is None and mode in ("auto", "browser"):
            clips = self._generate_songs_browser(
                prompt=prompt,
                make_instrumental=make_instrumental,
            )

        if not clips:
            raise RuntimeError("No clips generated")

        # Poll for completion
        clip_ids = [clip.get("id") for clip in clips if clip.get("id")]
        if clip_ids:
            return self._poll_songs(clip_ids)

        return clips

    def batch_wav_to_mp3(self, output_dir, bitrate="192k"):
        """Convert all base WAV files in the output directory to MP3.

        Args:
            output_dir (str): Directory containing WAV files.
            bitrate (str): MP3 bitrate (default 192k).

        Returns:
            tuple: (converted_count, failed_count)
        """
        import glob
        wav_files = glob.glob(os.path.join(output_dir, "*_base.wav"))
        logger.info(f"Found {len(wav_files)} base WAV files to convert to MP3")

        converted = 0
        failed = 0
        for wav_path in sorted(wav_files):
            mp3_path = wav_path.rsplit("_base.wav", 1)[0] + "_base.mp3"
            if os.path.exists(mp3_path):
                logger.info(f"  Already exists: {os.path.basename(mp3_path)}")
                converted += 1
                continue
            try:
                self._wav_to_mp3(wav_path, mp3_path, bitrate=bitrate)
                converted += 1
            except Exception as e:
                logger.error(f"  FAILED: {os.path.basename(wav_path)}: {e}")
                failed += 1

        logger.info(f"Batch WAV->MP3 complete: {converted} converted, {failed} failed")
        return converted, failed

    def _wav_to_mp3(self, wav_path, mp3_path=None, bitrate="192k"):
        """Convert a WAV file to MP3 using ffmpeg.

        Args:
            wav_path (str): Path to input WAV file.
            mp3_path (str): Path for output MP3.
            bitrate (str): MP3 bitrate (default 192k).

        Returns:
            str: Path to the generated MP3 file.
        """
        if not os.path.exists(wav_path):
            raise FileNotFoundError(f"WAV file not found: {wav_path}")

        if mp3_path is None:
            mp3_path = wav_path.rsplit(".", 1)[0] + ".mp3"

        cmd = [
            self.ffmpeg_bin, "-y", "-i", wav_path,
            "-codec:a", "libmp3lame", "-b:a", bitrate, "-joint_stereo", "1",
            mp3_path
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60,
            creation_flags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr[-500:]}")

        return mp3_path

    def batch_remake(self, output_dir, style="Deep House", skip_existing=True):
        """Batch generate Deep House remakes for all hymn WAVs using Suno.

        Args:
            output_dir (str): Directory containing base WAV files.
            style (str): Style prompt for generation.
            skip_existing (bool): Skip if _remake.wav already exists.

        Returns:
            tuple: (success_count, failed_count)
        """
        import glob
        if not self.session_token:
            raise RuntimeError("SunoRemaker not configured")

        wav_files = glob.glob(os.path.join(output_dir, "*_base.wav"))
        logger.info(f"Found {len(wav_files)} hymns to remake via Suno")

        success = 0
        failed = 0
        for wav_path in sorted(wav_files):
            name = Path(wav_path).stem.replace("_base", "")
            remake_path = wav_path.replace("_base.wav", "_remake.wav")

            if skip_existing and os.path.exists(remake_path):
                remake_size = os.path.getsize(remake_path)
                base_size = os.path.getsize(wav_path)
                if remake_size != base_size:
                    logger.info(f"  Skipping {name} (remake exists and differs from base)")
                    success += 1
                    continue

            try:
                logger.info(f"\n--- Remaking: {name} ---")
                self.remake(wav_path, style)
                success += 1
                time.sleep(2)  # Rate limiting
            except Exception as e:
                logger.error(f"  FAILED: {name}: {e}")
                failed += 1
                if "credits" in str(e).lower() or "402" in str(e):
                    logger.error("Suno credits exhausted. Stopping batch.")
                    break

        logger.info(f"\n=== Batch Suno Remake Complete ===")
        logger.info(f"Success: {success}")
        logger.info(f"Failed: {failed}")
        return success, failed
