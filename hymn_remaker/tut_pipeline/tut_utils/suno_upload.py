"""tut_utils/suno_upload.py — upload WAV to Suno via file input + handle Identify/Describe."""
import time
import logging

logger = logging.getLogger(__name__)


def upload_wav_to_suno(page, wav_path, genre_prompt):
    """Upload a WAV to Suno, handle Identify/Describe, switch to Advanced, fill style.

    Returns True if Create button clicked, False if disabled."""
    page.goto("https://suno.com/create", wait_until="domcontentloaded", timeout=30000)
    time.sleep(6)
    try:
        page.evaluate("document.querySelectorAll('[role=dialog]').forEach(d => d.remove())")
    except Exception:
        pass

    # Click Add Audio
    try:
        page.evaluate("document.querySelector('button[aria-label*=\"Add audio\"]')?.click()")
    except Exception:
        return False
    time.sleep(3)

    # Upload file via hidden input
    try:
        page.locator('input[type="file"]').first.set_input_files(wav_path)
    except Exception:
        return False
    time.sleep(10)

    # Handle Identify / Describe / Upload-flow
    for i in range(40):
        time.sleep(2)
        try:
            bt = page.inner_text("body").lower()
        except Exception:
            break

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
    try:
        page.evaluate("""Array.from(document.querySelectorAll('[role="tab"]')).find(t =>
            (t.innerText || '').trim() === 'Advanced'
        )?.click()""")
    except Exception:
        pass
    time.sleep(2)

    # Fill style
    try:
        page.evaluate(f"""
            var tas = Array.from(document.querySelectorAll('textarea')).filter(t => t.offsetParent !== null);
            if (tas.length >= 2) {{
                var ns = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                ns.call(tas[1], '{genre_prompt}');
                tas[1].dispatchEvent(new Event('input', {{bubbles: true}}));
            }}
        """)
    except Exception:
        pass
    time.sleep(1)

    # Try Create for up to 40s
    for _ in range(20):
        time.sleep(2)
        try:
            created = page.evaluate("""(() => {
                let btn = Array.from(document.querySelectorAll('button')).find(b =>
                    (b.innerText || '').includes('Create') && b.offsetParent !== null && !b.hasAttribute('disabled')
                );
                if (btn) { btn.click(); return 'clicked'; }
                return 'disabled';
            })()""")
            if created != "disabled":
                return True
        except Exception:
            pass
    return False
