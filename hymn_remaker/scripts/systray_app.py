"""
HymnMania System Tray Controller
Runs in the background, serves as server manager, and launches the dashboard.
"""
import pystray
from PIL import Image, ImageDraw
import subprocess
import webbrowser
import os
import sys
import time

PORT = 8083
server_proc = None

def create_image():
    # Generate a purple square icon dynamically
    image = Image.new('RGB', (64, 64), color=(192, 132, 252))
    d = ImageDraw.Draw(image)
    # Draw white H letter
    d.rectangle([(8, 8), (56, 56)], outline=(255, 255, 255), width=3)
    # Draw simple bar H design
    d.line([(24, 16), (24, 48)], fill=(255, 255, 255), width=4)
    d.line([(40, 16), (40, 48)], fill=(255, 255, 255), width=4)
    d.line([(24, 32), (40, 32)], fill=(255, 255, 255), width=4)
    return image

def start_server():
    global server_proc
    if server_proc and server_proc.poll() is None:
        return
    print("Starting Dashboard Server...")
    server_proc = subprocess.Popen(
        [sys.executable, "dashboard_server.py"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    )

def stop_server():
    global server_proc
    if server_proc:
        try:
            server_proc.terminate()
            server_proc.wait(timeout=3)
        except:
            pass
        server_proc = None
        print("Dashboard Server stopped.")

def open_dashboard():
    webbrowser.open(f"http://localhost:{PORT}")

def quit_all(icon, item):
    stop_server()
    # Terminate background tasks
    try:
        # Trigger stop route in server if running
        import urllib.request
        urllib.request.urlopen(f"http://localhost:{PORT}/api/stop", data=b"", timeout=1)
    except:
        pass
    icon.stop()

def setup(icon):
    icon.visible = True
    start_server()

def main():
    icon = pystray.Icon(
        "HymnMania",
        create_image(),
        menu=pystray.Menu(
            pystray.MenuItem("Open Dashboard", open_dashboard, default=True),
            pystray.MenuItem("Restart Dashboard", lambda icon, item: (stop_server(), start_server())),
            pystray.MenuItem("Stop Dashboard", lambda icon, item: stop_server()),
            pystray.MenuItem("Quit Pipeline & Exit", quit_all)
        )
    )
    icon.run(setup)

if __name__ == '__main__':
    main()
