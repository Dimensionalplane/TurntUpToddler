"""
Suno Browser Automation Client — Driving Suno.com via CDP (Chrome DevTools Protocol).
"""

import json
import time
import logging
import requests
import websocket
import os

logger = logging.getLogger(__name__)


class SunoBrowserAutomation:
    """Automates Suno.com generation by injecting prompts directly into the active Edge tab."""

    def __init__(self, port=9222, base_url="https://suno.com"):
        self.port = port
        self.base_url = base_url

    def _get_page_targets(self):
        """Fetch all debuggable targets from Edge and filter for pages."""
        try:
            res = requests.get(f"http://127.0.0.1:{self.port}/json", timeout=3)
            targets = res.json()
        except Exception:
            try:
                res = requests.get(f"http://localhost:{self.port}/json", timeout=3)
                targets = res.json()
            except Exception as e:
                logger.warning(
                    f"Could not connect to Edge debugging port {self.port}: {e}"
                )
                return []

        return [
            t
            for t in targets
            if t.get("type") == "page" and "webSocketDebuggerUrl" in t
        ]

    def _get_active_tab(self, require_suno=False):
        """Find or prioritize the Suno tab."""
        targets = self._get_page_targets()
        suno_targets = [t for t in targets if "suno.com" in t.get("url", "").lower()]
        if suno_targets:
            res_tab = suno_targets[0]
            # Prioritize create page
            for t in suno_targets:
                if "/create" in t.get("url", "").lower():
                    res_tab = t
                    break
            logger.info(
                f"Selected Suno tab: {res_tab.get('url')} (ID: {res_tab.get('id')})"
            )
            return res_tab

        if require_suno:
            raise RuntimeError("No Suno tab found. Please open suno.com in Edge.")
        return targets[0] if targets else None

    def execute_js(self, ws_url, script, timeout=60):
        """Evaluate arbitrary JavaScript on the target tab via CDP and return result."""
        ws = None
        last_err = None
        for attempt in range(6):
            if attempt > 0:
                try:
                    tab = self._get_active_tab(require_suno=True)
                    ws_url = tab.get("webSocketDebuggerUrl")
                except Exception as e:
                    logger.warning(f"Could not re-fetch Suno tab: {e}")

            ws_url_variants = [
                ws_url.replace("localhost", "127.0.0.1"),
                ws_url.replace("127.0.0.1", "localhost"),
            ]
            target_ws = ws_url_variants[attempt % 2]
            try:
                ws = websocket.create_connection(
                    target_ws, suppress_origin=True, timeout=30
                )
                ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
                payload = {
                    "id": 2,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": script,
                        "returnByValue": True,
                        "awaitPromise": True,
                    },
                }
                ws.send(json.dumps(payload))
                start_poll = time.time()
                while time.time() - start_poll < timeout:
                    try:
                        resp = json.loads(ws.recv())
                        if resp.get("id") == 2:
                            result = resp.get("result", {}).get("result", {})
                            if "exceptionDetails" in resp.get("result", {}):
                                exception = resp["result"]["exceptionDetails"].get(
                                    "exception", {}
                                )
                                if "description" in exception:
                                    raise RuntimeError(
                                        f"JS Error: {exception['description']}"
                                    )
                            return result.get("value")
                    except websocket.WebSocketTimeoutException:
                        pass
                raise TimeoutError(f"CDP Timeout after {timeout}s")
            except Exception as e:
                last_err = e
                logger.warning(f"WebSocket attempt {attempt + 1} failed: {e}")
                time.sleep(3)
            finally:
                if ws:
                    ws.close()
        raise last_err or RuntimeError(
            "Failed to connect to WebSocket after multiple attempts"
        )

    def _send_cdp_cmd(self, ws, msg_id, method, params=None):
        payload = {"id": msg_id, "method": method}
        if params:
            payload["params"] = params
        ws.send(json.dumps(payload))
        start_time = time.time()
        while time.time() - start_time < 30:
            try:
                resp = json.loads(ws.recv())
                if resp.get("id") == msg_id:
                    return resp
            except websocket.WebSocketTimeoutException:
                pass
        raise TimeoutError(f"No response for {method}")

    def cdp_click(self, ws_url, selector):
        find_js = f"""
        (function() {{
            const el = document.querySelector("{selector}");
            if (!el) return null;
            var r = el.getBoundingClientRect();
            if (r.width === 0 || r.height === 0) return null;
            var inViewport = (
                r.top >= 0 &&
                r.left >= 0 &&
                r.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                r.right <= (window.innerWidth || document.documentElement.clientWidth)
            );
            if (!inViewport) {{
                el.scrollIntoView({{ block: 'center' }});
                r = el.getBoundingClientRect();
            }}
            return [r.left + r.width/2, r.top + r.height/2];
        }})()
        """
        coords = self.execute_js(ws_url, find_js)
        if not coords:
            return False

        self._cdp_click_coords(ws_url, coords[0], coords[1])
        return True

    def cdp_click_text(self, ws_url, selector, text, exact=False):
        find_js = f"""
        (function() {{
            const els = Array.from(document.querySelectorAll("{selector}"));
            const el = els.find(e => {{
                var txt = (e.innerText || '').trim();
                var matches = {"txt === " if exact else "txt.includes("}{json.dumps(text)}{"" if exact else ")"};
                return matches && e.getBoundingClientRect().width > 0;
            }});
            if (!el) return null;
            var r = el.getBoundingClientRect();
            var inViewport = (
                r.top >= 0 &&
                r.left >= 0 &&
                r.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                r.right <= (window.innerWidth || document.documentElement.clientWidth)
            );
            if (!inViewport) {{
                el.scrollIntoView({{ block: 'center' }});
                r = el.getBoundingClientRect();
            }}
            return [r.left + r.width/2, r.top + r.height/2];
        }})()
        """
        coords = self.execute_js(ws_url, find_js)
        if not coords:
            return False

        self._cdp_click_coords(ws_url, coords[0], coords[1])
        return True

    def _cdp_click_coords(self, ws_url, x, y):
        x = int(round(x))
        y = int(round(y))
        ws_url = ws_url.replace("localhost", "127.0.0.1")
        ws = None
        try:
            ws = websocket.create_connection(ws_url, suppress_origin=True, timeout=10)
            ws.send(json.dumps({"id": 70, "method": "Page.bringToFront"}))
            ws.recv()
            time.sleep(0.5)
            ws.send(
                json.dumps(
                    {
                        "id": 71,
                        "method": "Input.dispatchMouseEvent",
                        "params": {"type": "mouseMoved", "x": x, "y": y},
                    }
                )
            )
            ws.recv()
            time.sleep(0.1)
            ws.send(
                json.dumps(
                    {
                        "id": 72,
                        "method": "Input.dispatchMouseEvent",
                        "params": {
                            "type": "mousePressed",
                            "x": x,
                            "y": y,
                            "button": "left",
                            "clickCount": 1,
                        },
                    }
                )
            )
            ws.recv()
            time.sleep(0.05)
            ws.send(
                json.dumps(
                    {
                        "id": 73,
                        "method": "Input.dispatchMouseEvent",
                        "params": {
                            "type": "mouseReleased",
                            "x": x,
                            "y": y,
                            "button": "left",
                            "clickCount": 1,
                        },
                    }
                )
            )
            ws.recv()
        finally:
            if ws:
                ws.close()

    def _clear_suno_popups(self, ws_url):
        """Clear modals/overlays in Suno."""
        clear_js = """
        (function() {
            // Dismiss cookie banners or intro modals
            const all = Array.from(document.querySelectorAll('button, [role="button"]'));
            const closeBtn = all.find(el => {
                const t = (el.innerText || '').toLowerCase();
                const a = (el.getAttribute('aria-label') || '').toLowerCase();
                return (t.includes('close') || t.includes('dismiss') || t.includes('got it') || a.includes('close'));
            });
            if (closeBtn && closeBtn.offsetParent !== null) {
                closeBtn.click();
                return "closed_modal";
            }
            return "ready";
        })()
        """
        self.execute_js(ws_url, clear_js)
        return True

    def _save_debug_screenshot(self, ws_url):
        try:
            ws_url = ws_url.replace("localhost", "127.0.0.1")
            ws = websocket.create_connection(ws_url, suppress_origin=True, timeout=10)
            ws.send(json.dumps({"id": 99, "method": "Page.captureScreenshot"}))
            resp = json.loads(ws.recv())
            if "result" in resp and "data" in resp["result"]:
                import base64

                with open("cdp_debug_suno.png", "wb") as f:
                    f.write(base64.b64decode(resp["result"]["data"]))
                logger.info("Saved debug screenshot to cdp_debug_suno.png")
            ws.close()
        except Exception as e:
            logger.warning(f"Failed to save debug screenshot: {e}")

    def trigger_generation(
        self, prompt, audio_path=None, make_instrumental=True, lyrics=None
    ):
        tab = self._get_active_tab(require_suno=True)
        if not tab:
            raise RuntimeError("No Suno tab found for trigger_generation")
        ws_url = tab.get("webSocketDebuggerUrl")

        if audio_path and os.path.exists(audio_path):
            # Clear active filters in localStorage before reloading to keep the clips visible
            clear_filters_js = """
            (function() {
                var cleared = 0;
                for (var i = localStorage.length - 1; i >= 0; i--) {
                    var k = localStorage.key(i);
                    if (k && k.startsWith('sept-12-2025-clip-browser-filters')) {
                        localStorage.removeItem(k);
                        cleared++;
                    }
                }
                return cleared;
            })()
            """
            try:
                cleared_count = self.execute_js(ws_url, clear_filters_js)
                logger.info(
                    f"Suno: Cleared {cleared_count} active filter keys from localStorage."
                )
            except Exception as e:
                logger.warning(
                    f"Suno: Warning: Could not clear filters from localStorage: {e}"
                )

            # Force page reload to clear any stuck states or previous modals
            logger.info(
                "Suno: Reloading page via location.href to clear stuck states/modals..."
            )
            self.execute_js(ws_url, "window.__my_reload_flag = true;")
            try:
                self.execute_js(
                    ws_url,
                    "window.location.href = 'https://suno.com/create';",
                    timeout=3,
                )
            except Exception:
                pass
            time.sleep(1)

            # Wait for reload to start (flag to disappear)
            reload_started = False
            for i in range(10):
                res = self.execute_js(ws_url, "window.__my_reload_flag")
                if res is None:
                    reload_started = True
                    break
                time.sleep(1)
            logger.info(f"Suno: Reload started: {reload_started}")
            time.sleep(5)

            # Wait for page reload to complete and React hydration/workspace load
            logger.info("Suno: Waiting for page reload and React workspace load...")
            for load_attempt in range(60):
                ready_state = self.execute_js(ws_url, "document.readyState")
                is_hydrated = self.execute_js(
                    ws_url,
                    """
                (function() {
                    function isVis(el) { var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }
                    var els = Array.from(document.querySelectorAll('*')).filter(isVis);
                    return els.some(el => {
                        var cls = typeof el.className === 'string' ? el.className : (el.className && el.className.baseVal) || '';
                        return cls.includes('clip-row') || cls.includes('clip-card');
                    });
                })()
                """,
                )
                if ready_state == "complete" and is_hydrated:
                    logger.info(
                        f"Suno: React workspace hydrated and loaded successfully on attempt {load_attempt + 1}. Waiting 5s for stability..."
                    )
                    time.sleep(5)
                    break
                time.sleep(2)
            else:
                logger.warning("Suno: Page load/hydration timeout, proceeding anyway.")

            # Dismiss OneTrust cookie banner if present
            dismiss_cookies_js = """
            (function() {
                const accept = document.getElementById('accept-recommended-btn-handler') || document.querySelector('.onetrust-close-btn-handler');
                if (accept) {
                    accept.click();
                    return 'dismissed_cookie_banner';
                }
                return 'no_cookie_banner';
            })()
            """
            logger.info(
                f"Suno: Dismissing Cookie Banner... {self.execute_js(ws_url, dismiss_cookies_js)}"
            )
            # Wait for the cookie banner wrapper to disappear/unmount completely from the DOM
            for i in range(10):
                has_banner = self.execute_js(
                    ws_url, "document.getElementById('onetrust-banner-sdk') !== null"
                )
                if not has_banner:
                    logger.info(
                        f"Suno: Cookie Banner unmounted from DOM on attempt {i + 1}."
                    )
                    break
                time.sleep(1)
            time.sleep(2)

            # Navigate to create if needed
            if "/create" not in tab.get("url", ""):
                try:
                    self.execute_js(
                        ws_url,
                        f"window.location.href = '{self.base_url}/create'",
                        timeout=3,
                    )
                except Exception:
                    pass
                time.sleep(8)

            self._clear_suno_popups(ws_url)

            # 0. Ensure Custom Mode is ON
            custom_mode_js = """
            (function() {
                const allBtns = Array.from(document.querySelectorAll('button'));
                const b = allBtns.find(el => {
                    const txt = (el.innerText || '').toLowerCase();
                    return (txt.includes('custom') || txt.includes('advanced')) && el.offsetParent !== null;
                });
                if (b) {
                    const hasStyleArea = document.querySelector('textarea[placeholder*="style"], textarea[placeholder*="genres"], textarea[placeholder*="describe"]');
                    if (!hasStyleArea) {
                        b.click();
                        return "toggled_advanced";
                    }
                    return "advanced_already_on";
                }
                return "advanced_btn_not_found";
            })()
            """
            logger.info(
                f"Suno: Checking Custom Mode... {self.execute_js(ws_url, custom_mode_js)}"
            )
            time.sleep(3)

        # 1. Handle Audio Upload (if provided)
        if audio_path and os.path.exists(audio_path):
            logger.info(f"Suno: Uploading audio {audio_path}...")
            api_uploaded = False

            # Use browser-click upload to ensure correct workspace association (wid=default)
            try:
                token_js = """
                (async function() {
                    try {
                        if (typeof Clerk !== 'undefined' && Clerk.session) {
                            return await Clerk.session.getToken();
                        }
                        return 'no_session';
                    } catch(e) {
                        return 'error: ' + e.message;
                    }
                })()
                """
                token = self.execute_js(ws_url, token_js)
                if not token or "error" in token or token == "no_session":
                    raise Exception("No active Clerk session or token retrieval failed")

                logger.info("Suno: Initializing upload via Direct HTTP API...")
                url = "https://studio-api-prod.suno.com/api/uploads/audio/"
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Origin": "https://suno.com",
                    "Referer": "https://suno.com/",
                    "x-workspace-id": "default",
                }
                data = {
                    "spec": {"type": "audio/mpeg", "name": os.path.basename(audio_path)}
                }
                r = requests.post(url, headers=headers, json=data, timeout=20)
                if r.status_code != 200:
                    raise Exception(
                        f"Initialization failed: {r.status_code} - {r.text}"
                    )

                ud = r.json()
                clip_id = ud["id"]
                s3_url = ud["url"]
                s3_fields = ud["fields"]
                logger.info(f"Suno: Upload initialized. Clip ID: {clip_id}")

                logger.info("Suno: Uploading file to S3 bucket...")
                with open(audio_path, "rb") as f:
                    file_data = f.read()
                files = {
                    "file": (os.path.basename(audio_path), file_data, "audio/mpeg")
                }
                form_data = {}
                for k, v in s3_fields.items():
                    form_data[k] = v
                s3_r = requests.post(s3_url, data=form_data, files=files, timeout=45)
                if s3_r.status_code not in (200, 201, 204):
                    raise Exception(
                        f"S3 upload failed: {s3_r.status_code} - {s3_r.text}"
                    )

                logger.info("Suno: File uploaded to S3. Confirming upload finish...")
                finish_url = f"https://studio-api-prod.suno.com/api/uploads/audio/{clip_id}/upload-finish/"
                finish_data = {
                    "upload_type": "audio/mpeg",
                    "upload_filename": os.path.basename(audio_path),
                }
                finish_r = requests.post(
                    finish_url, headers=headers, json=finish_data, timeout=20
                )
                if finish_r.status_code not in (200, 201, 204):
                    raise Exception(
                        f"Finish confirmation failed: {finish_r.status_code} - {finish_r.text}"
                    )

                logger.info("Suno: Confirmation successful. Polling for readiness...")
                for poll_attempt in range(30):
                    time.sleep(3)
                    poll_url = (
                        f"https://studio-api-prod.suno.com/api/uploads/audio/{clip_id}/"
                    )
                    poll_r = requests.get(poll_url, headers=headers, timeout=20)
                    if poll_r.status_code == 200:
                        pd = poll_r.json()
                        status = pd.get("status")
                        logger.info(
                            f"Suno: Poll attempt {poll_attempt + 1}: status={status}"
                        )
                        if status in ("complete", "ready"):
                            logger.info("Suno: Direct API upload complete and ready!")
                            api_uploaded = True
                            break
                        if status in ("failed", "error"):
                            raise Exception(f"Upload failed on Suno side: {pd}")
                    else:
                        logger.warning(f"Suno: Polling error: {poll_r.status_code}")

                if not api_uploaded:
                    raise Exception(
                        "Polling timed out before audio was marked complete"
                    )

            except Exception as api_err:
                logger.warning(
                    f"Suno: Direct API upload failed: {api_err}. Falling back to browser-click upload..."
                )

            if not api_uploaded:
                # Dismiss "Agree to Terms" modal if present
                agree_terms_js = """
                (function() {
                    var btn = Array.from(document.querySelectorAll('button')).find(function(el) {
                        return (el.innerText || '').trim() === 'Agree to Terms';
                    });
                    if (btn) {
                        btn.click();
                        return true;
                    }
                    return false;
                })()
                """
                try:
                    if self.execute_js(ws_url, agree_terms_js):
                        logger.info("Suno: Dismissed 'Agree to Terms' upload modal.")
                        time.sleep(2)
                except Exception as e:
                    logger.warning(f"Suno: Error checking for terms modal: {e}")

                # Switch to Audio tab (which opens the dropdown menu and activates the upload listener)
                logger.info("Suno: Clicking Add Audio tab...")
                tab_clicked = False
                for tab_attempt in range(10):
                    get_tab_coords_js = """
                    (function() {
                        const b = Array.from(document.querySelectorAll('button')).find(el => {
                            var txt = (el.innerText || '').trim();
                            var label = el.getAttribute('aria-label') || '';
                            return (txt === '+ Audio' || txt === 'Audio' || label.toLowerCase().includes('audio')) && el.getBoundingClientRect().width > 0;
                        });
                        if (b) {
                            var rect = b.getBoundingClientRect();
                            return [rect.left + rect.width / 2, rect.top + rect.height / 2];
                        }
                        return null;
                    })()
                    """
                    coords = self.execute_js(ws_url, get_tab_coords_js)
                    if coords and len(coords) == 2:
                        logger.info(
                            f"Suno: Found Add Audio button coordinates: {coords}. Clicking via CDP..."
                        )
                        self._cdp_click_coords(ws_url, coords[0], coords[1])
                        tab_clicked = True
                        break
                    time.sleep(2)
                if not tab_clicked:
                    logger.warning(
                        "Suno: Failed to click Audio tab button, proceeding anyway."
                    )
                time.sleep(2)

                # Click "Upload" in the dropdown menu
                logger.info("Suno: Clicking Upload menu option...")
                upload_clicked = False
                for upload_attempt in range(5):
                    get_upload_coords_js = """
                    (function() {
                        var all = Array.from(document.querySelectorAll('*'));
                        var target = all.find(function(el) {
                            var txt = (el.innerText || el.textContent || "").trim();
                            if (txt !== 'Upload') return false;
                            var r = el.getBoundingClientRect();
                            return r.width > 0 && r.height > 0 && r.left >= 150 && r.right <= 450 && r.top >= 100 && r.bottom <= 450;
                        });
                        if (target) {
                            var rect = target.getBoundingClientRect();
                            return [rect.left + rect.width / 2, rect.top + rect.height / 2];
                        }
                        return null;
                    })()
                    """
                    coords = self.execute_js(ws_url, get_upload_coords_js)
                    if coords and len(coords) == 2:
                        logger.info(
                            f"Suno: Found Upload button coordinates: {coords}. Clicking via CDP..."
                        )
                        self._cdp_click_coords(ws_url, coords[0], coords[1])
                        upload_clicked = True
                        break
                    time.sleep(1)
                time.sleep(5)

                # Check and cancel any active/stuck uploads before starting the new upload
                cancel_stuck_js = """
                (function() {
                    function isVis(el) { var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }
                    var cancel = Array.from(document.querySelectorAll('*')).find(function(el) {
                        return (el.innerText || '').trim() === 'Cancel' && isVis(el) && el.children.length === 0;
                    }) || Array.from(document.querySelectorAll('*')).find(function(el) {
                        return (el.innerText || '').trim() === 'Cancel' && isVis(el);
                    });
                    if (cancel) {
                        cancel.click();
                        return 'cancelled_stuck_upload';
                    }
                    return 'no_stuck_uploads';
                })()
                """
                stuck_res = self.execute_js(ws_url, cancel_stuck_js)
                logger.info(f"Suno: Clearing stuck uploads... {stuck_res}")
                if stuck_res == "cancelled_stuck_upload":
                    time.sleep(3)

                ws = None
                try:
                    ws = websocket.create_connection(
                        ws_url.replace("localhost", "127.0.0.1"),
                        suppress_origin=True,
                        timeout=15,
                    )
                    self._send_cdp_cmd(ws, 10, "DOM.enable")
                    self._send_cdp_cmd(ws, 101, "Runtime.enable")
                    injected = False
                    for inject_attempt in range(5):
                        count = (
                            self.execute_js(
                                ws_url,
                                "document.querySelectorAll(\"input[type='file']\").length",
                            )
                            or 0
                        )
                        htmls = self.execute_js(
                            ws_url,
                            "Array.from(document.querySelectorAll(\"input[type='file']\")).map(el => el.outerHTML)",
                        )
                        logger.info(
                            f"Suno: Found {count} file inputs on page. HTML: {htmls}"
                        )
                        if count > 0:
                            # Get root document node ID
                            doc_res = self._send_cdp_cmd(
                                ws,
                                102,
                                "DOM.getDocument",
                                {"depth": -1, "pierce": True},
                            )
                            root_node_id = (
                                doc_res.get("result", {})
                                .get("root", {})
                                .get("nodeId", 1)
                            )

                            # Query selector all natively
                            query_res = self._send_cdp_cmd(
                                ws,
                                103,
                                "DOM.querySelectorAll",
                                {
                                    "nodeId": root_node_id,
                                    "selector": "input[type='file']",
                                },
                            )
                            node_ids = query_res.get("result", {}).get("nodeIds", [])

                            injected_any = False
                            for idx, node_id in enumerate(node_ids):
                                logger.info(
                                    f"Suno: Injecting file into input[type='file'] #{idx} (nodeId={node_id})"
                                )
                                res_set = self._send_cdp_cmd(
                                    ws,
                                    130 + idx,
                                    "DOM.setFileInputFiles",
                                    {
                                        "files": [os.path.abspath(audio_path)],
                                        "nodeId": node_id,
                                    },
                                )
                                logger.info(
                                    f"Suno: Input #{idx} DOM.setFileInputFiles result: {res_set}"
                                )
                                self.execute_js(
                                    ws_url,
                                    f'(function() {{ try {{ var el = document.querySelectorAll("input[type=\'file\']")[{idx}]; if (el) {{ delete el._valueTracker; el.dispatchEvent(new Event("change", {{ bubbles: true }})); el.dispatchEvent(new Event("input", {{ bubbles: true }})); }} }} catch(e) {{}} }})()',
                                )
                                injected_any = True
                            if injected_any:
                                time.sleep(2)

                            verify_js = """
                            (function() {
                                var inputs = Array.from(document.querySelectorAll("input[type='file']"));
                                return inputs.some(function(el) { return el.files && el.files.length > 0; });
                            })()
                            """
                            if self.execute_js(ws_url, verify_js):
                                logger.info(
                                    "Suno: Audio file injected and verified successfully."
                                )
                                injected = True
                                break
                        time.sleep(1)

                    if not injected:
                        logger.warning(
                            "Suno: Warning: Failed to verify file injection in inputs."
                        )

                    # Handle new upload modals (Identify and Describe)
                    logger.info("Suno: Handling upload modals (Identify/Describe)...")
                    clicked_describe = False
                    for attempt in range(80):
                        time.sleep(2)

                        ref_name = os.path.splitext(os.path.basename(audio_path))[0]
                        modal_state_js = f"""                        (function() {{
                            var txt = (document.body.textContent || '').toLowerCase();
                            if (txt.includes('identify audio content') || txt.includes('full song')) return 'identify';
                            if (txt.includes('describe your audio') || txt.includes('describe your sound')) return 'describe';
                            if (txt.includes('saving...')) return 'saving';
                            
                            // Handle Agree to Terms modal
                            var agreeBtn = Array.from(document.querySelectorAll('button')).find(function(el) {{
                                return (el.innerText || '').trim() === 'Agree to Terms';
                            }});
                            if (agreeBtn) {{
                                agreeBtn.click();
                                return 'clicked_agree';
                            }}
                            
                            var els = Array.from(document.querySelectorAll('*')).filter(function(el) {{
                                var r = el.getBoundingClientRect();
                                return r.width > 0 && r.height > 0 && r.left < window.innerWidth * 0.45;
                            }});
                            var hasRef = els.some(function(el) {{
                                var txt = el.textContent || '';
                                return txt.includes('{ref_name}') && /\\d\\d:\\d\\d/.test(txt) && !txt.includes('Cancel') && !txt.includes('Identify') && !txt.includes('Describe');
                            }});
                            if (hasRef) return 'reference_registered';
                            
                            return 'none';
                        }})()
                        """
                        modal_state = self.execute_js(ws_url, modal_state_js) or "none"

                        if modal_state == "identify":
                            logger.info(
                                "Suno: Handling 'Identify audio content' modal..."
                            )
                            modal_res = self.execute_js(
                                ws_url,
                                """
                            (function() {
                                function isVis(el) { var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }
                                var btns = Array.from(document.querySelectorAll('button'));
                                var fullSong = btns.find(function(b) {
                                    return (b.innerText || '').trim() === 'Full Song' && isVis(b);
                                });
                                if (fullSong) {
                                    var isChecked = fullSong.querySelector('svg') !== null || 
                                                    fullSong.className.includes('border-foreground-primary') || 
                                                    fullSong.className.includes('border-strawberry-');
                                    if (!isChecked) {
                                        fullSong.click();
                                        return 'clicked_full_song';
                                    }
                                }
                                var cont = Array.from(document.querySelectorAll('*')).filter(function(el) {
                                    var txt = (el.innerText || '').trim();
                                    return (txt === 'Continue' || txt === 'Skip') && isVis(el);
                                });
                                if (cont.length > 0) {
                                    cont[cont.length - 1].click();
                                    return 'clicked_continue';
                                }
                                return 'waiting_for_buttons';
                            })()
                            """,
                            )
                            logger.info(f"Suno: Identify modal action: {modal_res}")

                        elif modal_state == "describe":
                            logger.info("Suno: Handling 'Describe Your Audio' modal...")
                            modal_res = self.execute_js(
                                ws_url,
                                """
                            (function() {
                                function isVis(el) { var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }
                                var cont = Array.from(document.querySelectorAll('*')).filter(function(el) {
                                    var txt = (el.innerText || '').trim();
                                    return (txt === 'Continue' || txt === 'Skip') && isVis(el);
                                });
                                if (cont.length > 0) {
                                    cont[cont.length - 1].click();
                                    return 'clicked_describe_continue';
                                }
                                var saving = Array.from(document.querySelectorAll('*')).find(function(el) {
                                    return (el.innerText || '').trim() === 'Saving...' && isVis(el);
                                });
                                if (saving) {
                                    return 'saving';
                                }
                                return 'waiting_for_continue';
                            })()
                            """,
                            )
                            logger.info(f"Suno: Describe modal action: {modal_res}")
                            if (
                                modal_res == "clicked_describe_continue"
                                or modal_res == "saving"
                            ):
                                clicked_describe = True

                        elif modal_state == "reference_registered":
                            logger.info(
                                "Suno: Active audio reference detected in panel, skipping modal checks."
                            )
                            break

                        elif modal_state == "saving":
                            logger.info("Suno: Modal is saving...")
                            clicked_describe = True

                        else:
                            if attempt > 75:
                                logger.info(
                                    "Suno: No upload modals detected after waiting. Proceeding."
                                )
                                break
                            else:
                                logger.info(
                                    f"Suno: Waiting for upload modals or reference registration (attempt {attempt})..."
                                )
                    time.sleep(2)

                    # 2.x Fill lyrics if they were supplied
                    if lyrics:
                        logger.info(
                            "Suno: Injecting lyrics into the lyrics textarea..."
                        )
                        lyrics_js = f"""
                        (function() {{
                            // After clicking the Lyrics button, a textarea usually appears.
                            const textareas = Array.from(document.querySelectorAll('textarea')).filter(t => t.offsetParent !== null);
                            const lyricTa = textareas.find(t => (t.placeholder || '').toLowerCase().includes('lyric'));
                            if (!lyricTa) return "no_lyrics_textarea";

                            // Set value via React props (if available) then native setter
                            const propsKey = Object.keys(lyricTa).find(k => k.startsWith('__reactProps$'));
                            if (propsKey && lyricTa[propsKey] && lyricTa[propsKey].onChange) {{
                                lyricTa[propsKey].onChange({{ target: {{ value: {json.dumps(lyrics)} }}, persist: () => {{}} }});
                            }}
                            const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                            setter.call(lyricTa, {json.dumps(lyrics)});
                            lyricTa.dispatchEvent(new Event('input', {{bubbles:true}}));
                            lyricTa.dispatchEvent(new Event('change', {{bubbles:true}}));
                            return "lyrics_set";
                        }})()
                        """
                        logger.info(
                            f"Suno: Lyrics injection result: {self.execute_js(ws_url, lyrics_js)}"
                        )
                        time.sleep(1)

                    self._clear_suno_popups(ws_url)
                finally:
                    if ws:
                        ws.close()

        # Wait for the uploaded reference to be active in the Simple panel before proceeding
        if audio_path:
            ref_name = os.path.splitext(os.path.basename(audio_path))[0]

            if api_uploaded:
                logger.info(
                    "Suno: Reloading page to hydrate clips list with new uploaded reference..."
                )
                try:
                    self.execute_js(
                        ws_url,
                        "location.href = 'https://suno.com/create?wid=default';",
                        timeout=3,
                    )
                except Exception:
                    pass
                time.sleep(5)
                logger.info("Suno: Waiting for React workspace load after reload...")
                for attempt in range(15):
                    ready = self.execute_js(
                        ws_url,
                        "typeof Clerk !== 'undefined' && document.body.textContent.toLowerCase().includes('credits')",
                    )
                    if ready:
                        logger.info("Suno: Hydration complete.")
                        break
                    time.sleep(1)
                time.sleep(3)

                logger.info("Suno: Waiting for workspace clips list to load...")
                for list_attempt in range(30):
                    has_clips = self.execute_js(
                        ws_url,
                        f"""
                    (function() {{
                        function isVis(el) {{ var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }}
                        return Array.from(document.querySelectorAll('*')).some(el => 
                            (el.innerText || '').includes('{ref_name}') && isVis(el)
                        );
                    }})()
                    """,
                    )
                    if has_clips:
                        logger.info(
                            f"Suno: Workspace clips list loaded successfully on attempt {list_attempt + 1}."
                        )
                        break
                    time.sleep(1)
                time.sleep(2)

                # Perform the selection clicks
                def get_coords(text, area=None):
                    js = f"""
                    (function() {{
                        var all = Array.from(document.querySelectorAll('*'));
                        var targets = all.filter(function(el) {{
                            var txt = (el.innerText || el.textContent || "").trim();
                            if (txt.indexOf('{text}') === -1) return false;
                            var r = el.getBoundingClientRect();
                            if (r.width === 0 || r.height === 0) return false;
                            if ('{area}' === 'left' && r.left > window.innerWidth * 0.45) return false;
                            if ('{area}' === 'right' && r.left < window.innerWidth * 0.45) return false;
                            if (el.tagName === 'BODY' || el.tagName === 'HTML') return false;
                            return true;
                        }});
                        if (targets.length > 0) {{
                            targets.sort(function(a, b) {{
                                var rA = a.getBoundingClientRect();
                                var rB = b.getBoundingClientRect();
                                return (rA.width * rA.height) - (rB.width * rB.height);
                            }});
                            var rect = targets[0].getBoundingClientRect();
                            return [rect.left + rect.width / 2, rect.top + rect.height / 2];
                        }}
                        return null;
                    }})()
                    """
                    return self.execute_js(ws_url, js)

                logger.info("Suno: Clicking Add Audio button...")
                coords = get_coords("+ Audio") or get_coords("Audio")
                if coords and len(coords) == 2:
                    self._cdp_click_coords(ws_url, coords[0], coords[1])
                    time.sleep(2)

                    logger.info("Suno: Clicking Browse option...")
                    browse_coords = get_coords("Browse")
                    if browse_coords and len(browse_coords) == 2:
                        self._cdp_click_coords(
                            ws_url, browse_coords[0], browse_coords[1]
                        )
                        time.sleep(3)

                        logger.info(f"Suno: Clicking reference clip '{ref_name}'...")
                        clip_coords = get_coords(ref_name)
                        if clip_coords and len(clip_coords) == 2:
                            self._cdp_click_coords(
                                ws_url, clip_coords[0], clip_coords[1]
                            )
                            time.sleep(2)
                            logger.info(
                                "Suno: Reference clip clicked and selected successfully!"
                            )
                        else:
                            logger.warning(
                                f"Suno: Clip '{ref_name}' not found in popover list."
                            )
                    else:
                        logger.warning("Suno: 'Browse' option not found in dropdown.")
                else:
                    logger.warning("Suno: '+ Audio' button not found.")

            else:
                # Wait for clips list to load/render on screen first
                logger.info("Suno: Waiting for workspace clips list to load...")
                for list_attempt in range(25):
                    has_clips = self.execute_js(
                        ws_url,
                        f"""
                    (function() {{
                        function isVis(el) {{ var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }}
                        return Array.from(document.querySelectorAll('*')).some(el => 
                            (el.innerText || '').includes('{ref_name}') && isVis(el)
                        );
                    }})()
                    """,
                    )
                    if has_clips:
                        logger.info(
                            f"Suno: Workspace clips list loaded successfully on attempt {list_attempt + 1}."
                        )
                        break
                    time.sleep(1)

            logger.info(
                "Suno: Waiting for active audio reference to be registered in the panel..."
            )
            ref_selected = False
            for ref_attempt in range(45):
                ref_check_js = f"""
                (function() {{
                    function isVis(el) {{ var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.left < window.innerWidth * 0.45; }}
                    var els = Array.from(document.querySelectorAll('*')).filter(isVis);
                    return els.some(function(el) {{
                        var txt = el.innerText || '';
                        return txt.includes('{ref_name}') && !txt.includes('Cancel') && !txt.includes('Identify') && !txt.includes('Describe');
                    }});
                }})()
                """
                if self.execute_js(ws_url, ref_check_js):
                    logger.info("Suno: Active audio reference detected!")
                    ref_selected = True
                    break
                time.sleep(1)
            if not ref_selected:
                logger.warning(
                    "Suno: Warning: Active audio reference not detected in panel, continuing anyway."
                )

            # Close the Add Audio tab dropdown if it remains open to unblock the rest of the Create panel
            logger.info("Suno: Closing Add Audio tab dropdown...")
            close_dropdown_js = """
            (function() {
                const isVis = function(el) { var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
                const dropdownOpen = Array.from(document.querySelectorAll('*')).filter(isVis).some(el => (el.innerText || '').trim() === 'Record');
                if (dropdownOpen) {
                    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', keyCode: 27, which: 27, bubbles: true }));
                    document.body.click();
                    return "toggled_via_escape_and_body_click";
                }
                return "already_closed";
            })()
            """
            logger.info(
                f"Suno: Close dropdown result: {self.execute_js(ws_url, close_dropdown_js)}"
            )
            time.sleep(2)

        # 1.5 Click mode (Suno's new UI uses Simple/Advanced tabs)
        if audio_path:
            logger.info("Suno: Ensuring Custom mode is active for audio influence...")
            mode_js = """
            (function() {
                const allBtns = Array.from(document.querySelectorAll('button'));
                const b = allBtns.find(el => {
                    const txt = (el.innerText || '').toLowerCase();
                    return (txt.includes('custom') || txt.includes('advanced')) && el.offsetParent !== null;
                });
                if (b) {
                    const hasStyleArea = document.querySelector('textarea[placeholder*="style"], textarea[placeholder*="genres"], textarea[placeholder*="describe"]');
                    if (!hasStyleArea) {
                        b.click();
                        return "clicked_custom";
                    }
                    return "already_custom";
                }
                return "custom_btn_not_found";
            })()
            """
        else:
            logger.info("Suno: Switching to Simple mode...")
            mode_js = """
            (function() {
                function isVis(el) { var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }
                const btns = Array.from(document.querySelectorAll('button'));
                const simpleBtn = btns.find(el =>
                    el.innerText.trim() === 'Simple' && isVis(el)
                );
                if (simpleBtn) {
                    const isActive = simpleBtn.className.includes('active');
                    if (!isActive) {
                        simpleBtn.click();
                        return "clicked_simple";
                    }
                    return "already_simple";
                }
                return "simple_btn_not_found";
            })()
            """
        logger.info(f"Suno: Mode switch result: {self.execute_js(ws_url, mode_js)}")
        time.sleep(2)

        # 2. Set Prompt (Style) on the FIRST visible style/description/genre textarea
        logger.info(f"Suno: Setting style/prompt: {prompt[:50]}...")
        prompt_js = f"""
        (function() {{
            function isVis(el) {{ var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }}
            const textareas = Array.from(document.querySelectorAll('textarea')).filter(el => {{
                var isLyrics = el.getAttribute('data-testid') === 'lyrics-textarea' || (el.getAttribute('placeholder') || '').includes('[Verse]');
                return !isLyrics && isVis(el);
            }});
            if (textareas.length === 0) return "no_textareas";
            // ta[0] = style/genre field, ta[1] = prompt field
            var ns = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
            if (textareas.length > 0) {{
                // Style field: use just the first ~30 chars or a short genre tag
                var style = {json.dumps(prompt)};
                if (style.length > 40) style = style.substring(0, style.indexOf(','));
                ns.call(textareas[0], style);
                textareas[0].dispatchEvent(new Event('input', {{ bubbles: true }}));
                textareas[0].dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
            if (textareas.length > 1) {{
                // Prompt field: full prompt
                ns.call(textareas[1], {json.dumps(prompt)});
                textareas[1].dispatchEvent(new Event('input', {{ bubbles: true }}));
                textareas[1].dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
            if (textareas.length > 2) {{
                // Extra field (if present): style again
                ns.call(textareas[2], style);
                textareas[2].dispatchEvent(new Event('input', {{ bubbles: true }}));
                textareas[2].dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
            return "set_on_" + (textareas[0].placeholder || "ok");
        }}())
        """
        logger.info(
            f"Suno: Prompt injection result: {self.execute_js(ws_url, prompt_js)}"
        )

        # 3. Toggle Instrumental
        if make_instrumental:
            instr_js = """
            (function() {
                function isVis(el) { var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }
                const b = Array.from(document.querySelectorAll('button')).find(el => el.innerText.includes('Instrumental') && isVis(el));
                if (b) {
                    const isChecked = b.className.includes('checked') || b.getAttribute('aria-checked') === 'true' || b.innerText.includes('ON');
                    if (!isChecked) {
                        b.click();
                        return "toggled_instrumental";
                    }
                    return "instrumental_already_on";
                }
                return "instrumental_btn_not_found";
            })()
            """
            logger.info(
                f"Suno: Instrumental check: {self.execute_js(ws_url, instr_js)}"
            )

        # Capture pre-existing clip IDs and the old latest track ID right before clicking Create
        self.pre_existing_ids = set()
        self.old_latest_id = None
        try:
            token_js = """
            (async function() {
                try {
                    if (typeof Clerk !== 'undefined' && Clerk.session) {
                        return await Clerk.session.getToken();
                    }
                    return '';
                } catch(e) {
                    return '';
                }
            })()
            """
            token = self.execute_js(ws_url, token_js)
            if token:
                r = requests.get(
                    "https://studio-api-prod.suno.com/api/feed/",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10,
                )
                if r.status_code == 200:
                    feed_data = r.json()
                    clips_list = (
                        feed_data.get("clips", [])
                        if isinstance(feed_data, dict)
                        else feed_data
                    )
                    if isinstance(clips_list, list):
                        self.pre_existing_ids = {
                            c.get("id") for c in clips_list if c.get("id")
                        }
                        logger.info(
                            f"Suno: Captured {len(self.pre_existing_ids)} pre-existing clip IDs."
                        )
        except Exception as pre_id_err:
            logger.warning(f"Suno: Failed to capture pre-existing IDs: {pre_id_err}")

        try:
            # Extract old latest ID from DOM
            old_id_js = """
            (function() {
                const rows = Array.from(document.querySelectorAll('[data-testid="song-row"], [class*="SongRow"], .clip-row, [class*="clip-row"]'));
                if (rows.length > 0) {
                    const links = Array.from(rows[0].querySelectorAll('a'));
                    for (let l of links) {
                        const href = l.getAttribute('href') || '';
                        const m = href.match(/\\/song\\/([^\\/\\?#]+)/) || href.match(/\\/clip\\/([^\\/\\?#]+)/);
                        if (m) return m[1];
                    }
                }
                return '';
            })()
            """
            self.old_latest_id = self.execute_js(ws_url, old_id_js)
            logger.info(f"Suno: Stored old latest track ID: {self.old_latest_id}")
        except Exception as old_id_err:
            logger.warning(
                f"Suno: Failed to capture old latest ID from DOM: {old_id_err}"
            )

        # 4. Click Create
        logger.info("Suno: Clicking Create...")
        create_js = """
        (function() {
            function isVis(el) { var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }
            const allBtns = Array.from(document.querySelectorAll('button'));
            const b = allBtns.find(el => (el.getAttribute('aria-label') || '').includes('Create') && isVis(el))
                    || allBtns.find(el => (el.innerText || '').includes('Create') && isVis(el));
            if (b) {
                const info = {
                    text: b.innerText,
                    disabled: b.disabled,
                    classes: b.className
                };
                if (b.disabled) {
                    return "disabled:" + JSON.stringify(info);
                }
                b.click();
                return "clicked:" + JSON.stringify(info);
            }
            return "not_found";
        })()
        """
        res = self.execute_js(ws_url, create_js)
        if res and "clicked" in res:
            logger.info(f"Suno: Generation triggered! Button info: {res}")
            return True
        else:
            logger.warning(f"Suno: Could not trigger generation: {res}")
            self._save_debug_screenshot(ws_url)
            return False

    def wait_for_completion_and_download(self, timeout=400):
        """Poll for completion and trigger download of the latest track."""
        start = time.time()
        logger.info("Suno: Polling for track completion...")
        while time.time() - start < timeout:
            tab = self._get_active_tab(require_suno=True)
            if not tab:
                raise RuntimeError(
                    "No Suno tab found for wait_for_completion_and_download"
                )
            ws_url = tab.get("webSocketDebuggerUrl")

            old_id = getattr(self, "old_latest_id", "") or ""
            poll_js = f"""
            (function() {{
                const rows = Array.from(document.querySelectorAll('[data-testid="song-row"], [class*="SongRow"], .clip-row, [class*="clip-row"]'));
                if (rows.length === 0) return "no_tracks";

                const latest = rows[0];
                let latestId = '';
                const links = Array.from(latest.querySelectorAll('a'));
                for (let l of links) {{
                    const href = l.getAttribute('href') || '';
                    const m = href.match(/\\/song\\/([^\\/\\?#]+)/) || href.match(/\\/clip\\/([^\\/\\?#]+)/);
                    if (m) {{ latestId = m[1]; break; }}
                }}

                if (latestId && latestId === '{old_id}') {{
                    return "waiting_for_new_row";
                }}

                const text = (latest.innerText || '').toLowerCase();

                if (text.includes('error') || text.includes('failed')) return "error";

                // Check duration first to bypass description text matches (e.g. "creating a dense texture")
                const hasDuration = /\\d+:\\d+/.test(text);
                if (hasDuration) {{
                    return "ready";
                }}

                if (text.includes('creating') || text.includes('queue') || text.includes('generating')) return "generating";
                return "waiting";
            }})()
            """
            res = self.execute_js(ws_url, poll_js)
            if res == "ready":
                logger.info("Suno: Track is ready and generated successfully!")
                return True

            logger.info(f"Suno status: {res} ({int(time.time() - start)}s)")
            time.sleep(15)
        return False
