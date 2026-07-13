import os
import sys
import json
import glob
import time
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(ROOT, "..", "generated")
TRACK_FILE = os.path.join(ROOT, "..", ".uploaded_videos.txt")
LOG_FILE = os.path.join(ROOT, "..", "pipeline.log")

active_process = {
    "process": None,
    "task_name": "Idle",
    "started_at": 0
}

def log_message(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")

class DashboardHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = f"""
            <html>
            <head><title>HymnMania Console</title></head>
            <body>
                <h1>HymnMania Single Page Control Dashboard</h1>
                <p>Status: {active_process['task_name']}</p>
                <form action="/run" method="POST">
                    <button type="submit">Trigger Pipeline Chain</button>
                </form>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        elif parsed.path == "/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            status = {"task": active_process["task_name"]}
            self.wfile.write(json.dumps(status).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/run":
            global active_process
            cmd = [sys.executable, os.path.join(ROOT, "pipeline_chain.py"), "--midi", "hymn_remaker/input/Thy_Word.mid"]
            proc = subprocess.Popen(cmd, cwd=os.path.join(ROOT, ".."), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            active_process["process"] = proc
            active_process["task_name"] = "Running Pipeline Chain"
            active_process["started_at"] = time.time()
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()

def main():
    server = HTTPServer(("localhost", 8083), DashboardHTTPHandler)
    print("Dashboard Console Server running at http://localhost:8083/")
    server.serve_forever()

if __name__ == "__main__":
    main()
