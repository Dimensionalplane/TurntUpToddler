import os
import sys
import subprocess
import signal

ROOT = os.path.dirname(os.path.abspath(__file__))
SERVER_PATH = os.path.join(ROOT, "dashboard_flask_server_for_single_page_control.py")


def main():
    print("Starting HymnMania Console System Tray Manager...")
    cf = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    proc = subprocess.Popen([sys.executable, SERVER_PATH], creationflags=cf)

    print(
        "Dashboard server started. Press Ctrl+C in this console to terminate cleanly."
    )
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("Stopping server...")
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                creationflags=cf,
            )
        else:
            os.kill(proc.pid, signal.SIGTERM)


if __name__ == "__main__":
    main()
