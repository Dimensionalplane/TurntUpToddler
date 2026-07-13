"""tut_utils/browser.py — connect to Edge CDP or launch fresh."""
import time
import subprocess
import logging

logger = logging.getLogger(__name__)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
CDP_URL = "http://127.0.0.1:9222"


def is_cdp_alive():
    """Check if Edge CDP port is responding."""
    import urllib.request
    try:
        urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=2)
        return True
    except Exception:
        return False


def launch_edge(user_data_dir=None):
    """Launch Edge with CDP and return True once ready."""
    if not user_data_dir:
        user_data_dir = r"C:\Users\hyper\.edge-tut"
    try:
        subprocess.Popen(
            [EDGE_PATH, "--remote-debugging-port=9222", f"--user-data-dir={user_data_dir}", "https://suno.com/create"],
            shell=False,
        )
    except Exception as e:
        logger.warning(f"Edge launch via subprocess failed: {e}")
        return False

    for _ in range(20):
        time.sleep(2)
        if is_cdp_alive():
            return True
    return False


def connect_playwright():
    """Connect Playwright to existing CDP browser. Raises if not available."""
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp(CDP_URL)
    return pw, browser


def dismiss_dialogs(page):
    """Remove cookie/consent/privacy modals from Suno page."""
    try:
        page.evaluate("document.querySelectorAll('[role=dialog]').forEach(d => d.remove())")
    except Exception:
        pass


def create_fresh_page(browser):
    """Close stale pages, return a clean new page."""
    ctx = browser.contexts[0]
    for p in ctx.pages[:]:
        try:
            p.close()
        except Exception:
            pass
    return ctx.new_page()
