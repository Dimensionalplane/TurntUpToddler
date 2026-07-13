import time
import sys
import logging
from hymn_remaker.src.suno_browser_automation import SunoBrowserAutomation

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main():
    suno = SunoBrowserAutomation()
    tab = suno._get_active_tab(require_suno=True)
    if not tab:
        print("No Suno tabs found!")
        return
    
    ws_url = tab["webSocketDebuggerUrl"]
    print(f"Using tab: {tab['title']} ({ws_url})")
    
    # 1. Click Add Audio tab
    click_js = """
    (function() {
        const b = Array.from(document.querySelectorAll('button')).find(el => (el.getAttribute('aria-label') || '').includes('Add audio') && el.getBoundingClientRect().width > 0);
        if (b) {
            var ev1 = new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window});
            var ev2 = new MouseEvent('mouseup', {bubbles: true, cancelable: true, view: window});
            var ev3 = new MouseEvent('click', {bubbles: true, cancelable: true, view: window});
            b.dispatchEvent(ev1);
            b.dispatchEvent(ev2);
            b.dispatchEvent(ev3);
            return true;
        }
        return false;
    })()
    """
    res = suno.execute_js(ws_url, click_js)
    print(f"Clicked Add Audio: {res}")
    time.sleep(2)
    
    # 2. Inspect match elements
    inspect_js = """
    (function() {
        return Array.from(document.querySelectorAll('*')).map((el, idx) => {
            var txt = (el.innerText || '').trim();
            if (!txt.includes('Upload')) return null;
            var r = el.getBoundingClientRect();
            return {
                index: idx,
                tagName: el.tagName,
                className: el.className,
                rect: { left: r.left, top: r.top, width: r.width, height: r.height },
                visible: r.width > 0 && r.height > 0,
                html: el.outerHTML.substring(0, 150)
            };
        }).filter(x => x !== null);
    })()
    """
    matches = suno.execute_js(ws_url, inspect_js)
    print(f"Found matches: {len(matches)}")
    for m in matches:
        print(m)

if __name__ == "__main__":
    main()
