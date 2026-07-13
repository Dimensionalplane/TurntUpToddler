"""
HymnMania Dashboard Server — Consolidated Single-Page Interface
Serves controls, logs, generation triggers, and track management at http://localhost:8083/
"""
import os
import sys
import json
import glob
import time
import subprocess
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(ROOT, "generated")
TRACK_FILE = os.path.join(ROOT, ".uploaded_videos.txt")
LOG_FILE = os.path.join(ROOT, "pipeline.log")

# Global dict to track active background process
active_process = {
    "process": None,
    "task_name": "Idle",
    "started_at": 0
}

def log_message(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")

def run_background_task(cmd, name):
    global active_process
    if active_process["process"] and active_process["process"].poll() is None:
        log_message(f"Task already running: {active_process['task_name']}. Aborting new run.")
        return False
        
    log_message(f"Starting background task: {name} ({' '.join(cmd)})")
    try:
        # Clear log file for new task
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"--- Task: {name} started ---\n")
            
        proc = subprocess.Popen(
            cmd,
            cwd=ROOT,
            stdout=open(LOG_FILE, "a", encoding="utf-8"),
            stderr=subprocess.STDOUT,
            text=True,
            shell=True
        )
        active_process["process"] = proc
        active_process["task_name"] = name
        active_process["started_at"] = time.time()
        return True
    except Exception as e:
        log_message(f"Error starting task: {e}")
        return False

def check_edge_and_credits():
    try:
        req = urllib.request.Request("http://127.0.0.1:9222/json")
        with urllib.request.urlopen(req, timeout=1.5) as r:
            pages = json.loads(r.read().decode())
        edge_ok = True
    except:
        return {"edge": "Offline", "credits": "Offline"}

    # Attempt to query Suno credits using Clerk token from active suno tab
    try:
        import websocket
        tab = [p for p in pages if "suno.com" in p.get("url", "") and p.get("type") == "page"][0]
        ws = websocket.create_connection(tab["webSocketDebuggerUrl"].replace("localhost", "127.0.0.1"), suppress_origin=True, timeout=1.5)
        ws.send(json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {
                "expression": "(async function(){try{return await Clerk.session.getToken()}catch(e){return null}})()",
                "returnByValue": True,
                "awaitPromise": True
            }
        }))
        res = json.loads(ws.recv())
        token = res.get("result", {}).get("result", {}).get("value")
        ws.close()
        if token:
            resp = requests.get("https://studio-api-prod.suno.com/api/billing/info/", headers={"Authorization": f"Bearer {token}"}, timeout=2.0)
            if resp.status_code == 200:
                credits = resp.json().get("total_credits_remaining", 0)
                return {"edge": "Online", "credits": f"{credits:,} Credits"}
    except Exception as e:
        pass
    return {"edge": "Online", "credits": "Unknown (Open suno.com)"}

def get_hymns():
    mp3s = sorted(glob.glob(os.path.join(GEN, "*.mp3")))
    uploaded = {}
    if os.path.exists(TRACK_FILE):
        with open(TRACK_FILE) as f:
            for line in f:
                line = line.strip()
                if " | " in line:
                    vid, fname = line.split(" | ", 1)
                    uploaded[fname.strip()] = vid.strip()
    rows = []
    for p in mp3s:
        name = os.path.basename(p)
        size = os.path.getsize(p) // 1024
        vid = uploaded.get(name, "")
        
        # Check if video file (mp4) exists
        mp4_name = name.replace(".mp3", "_projectm.mp4")
        video_rendered = os.path.exists(os.path.join(GEN, mp4_name))
        
        rows.append({
            "name": name,
            "size_kb": size,
            "youtube_id": vid,
            "video_rendered": video_rendered
        })
    return rows

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>HymnMania Console</title>
<style>
  :root {
    --bg: #0b0c10;
    --card-bg: #15161e;
    --text: #f1f3f9;
    --accent: #c084fc;
    --accent-hover: #a855f7;
    --border: #232530;
    --green: #4ade80;
    --yellow: #facc15;
    --red: #f87171;
  }
  body {
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    margin: 0;
    padding: 24px;
  }
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border);
    padding-bottom: 16px;
    margin-bottom: 24px;
  }
  h1 {
    font-size: 24px;
    color: var(--accent);
    margin: 0;
  }
  .status-pills {
    display: flex;
    gap: 12px;
  }
  .pill {
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    background: #232530;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .pill-green { color: var(--green); border: 1px solid var(--green); }
  .pill-red { color: var(--red); border: 1px solid var(--red); }
  .pill-yellow { color: var(--yellow); border: 1px solid var(--yellow); }
  
  .grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
  }
  .card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
  }
  h2 {
    font-size: 16px;
    margin-top: 0;
    margin-bottom: 16px;
    color: var(--accent);
    border-bottom: 1px solid var(--border);
    padding-bottom: 8px;
  }
  .form-group {
    margin-bottom: 12px;
  }
  label {
    display: block;
    font-size: 12px;
    color: #888;
    margin-bottom: 4px;
  }
  select, input {
    width: 100%;
    background: #232530;
    border: 1px solid var(--border);
    color: var(--text);
    padding: 8px;
    border-radius: 6px;
    box-sizing: border-box;
  }
  button {
    background: var(--accent);
    color: #000;
    font-weight: 600;
    border: none;
    padding: 10px 16px;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.2s;
  }
  button:hover {
    background: var(--accent-hover);
  }
  .btn-danger {
    background: var(--red);
  }
  .btn-danger:hover {
    background: #ef4444;
  }
  .btn-secondary {
    background: #3b82f6;
    color: white;
  }
  .btn-secondary:hover {
    background: #2563eb;
  }
  
  /* Live log window */
  .log-container {
    background: #000;
    border: 1px solid var(--border);
    border-radius: 6px;
    height: 180px;
    overflow-y: scroll;
    padding: 12px;
    font-family: monospace;
    font-size: 12px;
    white-space: pre-wrap;
    margin-top: 10px;
  }
  
  /* Table styling */
  table {
    border-collapse: collapse;
    width: 100%;
    font-size: 13px;
  }
  th {
    background: #1c1e28;
    color: var(--accent);
    padding: 8px 12px;
    text-align: left;
  }
  td {
    padding: 6px 12px;
    border-bottom: 1px solid var(--border);
  }
  tr:hover td {
    background: #1c1e28;
  }
  a {
    color: #818cf8;
    text-decoration: none;
  }
  a:hover {
    text-decoration: underline;
  }
  .tooltip {
    position: relative;
    display: inline-block;
    cursor: help;
    color: var(--accent);
    margin-left: 4px;
    font-size: 11px;
  }
  .tooltip .tooltiptext {
    visibility: hidden;
    width: 200px;
    background-color: #232530;
    color: #fff;
    text-align: center;
    border-radius: 6px;
    padding: 8px;
    position: absolute;
    z-index: 1;
    bottom: 125%;
    left: 50%;
    margin-left: -100px;
    opacity: 0;
    transition: opacity 0.3s;
    font-size: 11px;
    border: 1px solid var(--border);
  }
  .tooltip:hover .tooltiptext {
    visibility: visible;
    opacity: 1;
  }
</style>
</head>
<body>

<header>
  <h1>HymnMania Control Console</h1>
  <div class="status-pills">
    <div id="edge-pill" class="pill pill-yellow">Edge debugger: Loading...</div>
    <div id="credits-pill" class="pill pill-yellow">Suno credits: Loading...</div>
    <div id="task-pill" class="pill pill-yellow">Task: Idle</div>
  </div>
</header>

<div class="grid">
  <!-- Left Side: Controls & Logs -->
  <div>
    <div class="card" style="margin-bottom: 24px;">
      <h2>
        Generate Suno Cover
        <span class="tooltip">[?]
          <span class="tooltiptext">Starts a new cover generation from the selected speed of Joy to the World using Suno.</span>
        </span>
      </h2>
      <div class="form-group">
        <label for="speed">Select Input Speed</label>
        <select id="speed">
          <option value="1.0x">1.0x (Normal)</option>
          <option value="0.5x">0.5x (Slow)</option>
          <option value="2.5x">2.5x (Fast)</option>
          <option value="5.0x">5.0x (Very Fast)</option>
          <option value="10.0x">10.0x (Hyper)</option>
          <option value="20.0x">20.0x (Speedcore)</option>
        </select>
      </div>
      <div class="form-group">
        <label for="genre">Select Style / Genre</label>
        <select id="genre">
          <option value="psytrance">psytrance (Psychedelic Trance)</option>
          <option value="japanese_hardcore_techno">japanese hardcore techno</option>
          <option value="gabba">gabba (Gabber Hardcore)</option>
          <option value="hardstyle_trance">hardstyle trance</option>
        </select>
      </div>
      <button onclick="startGeneration()">Start Cover Generation</button>
    </div>

    <div class="card" style="margin-bottom: 24px;">
      <h2>System Controls</h2>
      <div style="display: flex; gap: 10px;">
        <button onclick="startBatchUpload()" class="btn-secondary">Upload to YouTube</button>
        <button onclick="stopAllTasks()" class="btn-danger">Stop All Tasks</button>
      </div>
    </div>

    <div class="card">
      <h2>Live Log Console Output</h2>
      <div id="log-window" class="log-container">Loading logs...</div>
    </div>
  </div>

  <!-- Right Side: Track Manager -->
  <div class="card" style="max-height: 700px; overflow-y: scroll;">
    <h2>Track & Cover Manager</h2>
    <table>
      <thead>
        <tr>
          <th>Track File</th>
          <th>Size</th>
          <th>Viz Status</th>
          <th>YouTube Link</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody id="track-rows">
        <tr><td colspan="5">Loading track list...</td></tr>
      </tbody>
    </table>
  </div>
</div>

<script>
  function updateStatus() {
    fetch('/api/status')
      .then(r => r.json())
      .then(data => {
        // Update Edge
        const ep = document.getElementById('edge-pill');
        ep.textContent = `Edge debugger: ${data.edge}`;
        ep.className = `pill ${data.edge === 'Online' ? 'pill-green' : 'pill-red'}`;
        
        // Update Credits
        const cp = document.getElementById('credits-pill');
        cp.textContent = `Suno credits: ${data.credits}`;
        cp.className = `pill ${data.credits.includes('Credits') ? 'pill-green' : 'pill-yellow'}`;

        // Update Active Task
        const tp = document.getElementById('task-pill');
        tp.textContent = `Task: ${data.task}`;
        tp.className = `pill ${data.task === 'Idle' ? 'pill-green' : 'pill-yellow'}`;
      });

    // Refresh logs
    fetch('/api/logs')
      .then(r => r.text())
      .then(text => {
        const lw = document.getElementById('log-window');
        const scrollAtBottom = lw.scrollHeight - lw.clientHeight <= lw.scrollTop + 10;
        lw.textContent = text;
        if (scrollAtBottom) {
          lw.scrollTop = lw.scrollHeight;
        }
      });
  }

  function refreshTracks() {
    fetch('/api/hymns')
      .then(r => r.json())
      .then(data => {
        const tbody = document.getElementById('track-rows');
        tbody.innerHTML = '';
        data.forEach(d => {
          const size = (d.size_kb / 1024).toFixed(1) + ' MB';
          const viz = d.video_rendered ? '<span style="color:var(--green)">Rendered</span>' : '<span style="color:var(--yellow)">Pending</span>';
          const yt = d.youtube_id ? `<a href="https://youtu.be/${d.youtube_id}" target="_blank">youtu.be/${d.youtube_id}</a>` : '<span style="color:var(--yellow)">Not uploaded</span>';
          
          tbody.innerHTML += `
            <tr>
              <td>${d.name}</td>
              <td>${size}</td>
              <td>${viz}</td>
              <td>${yt}</td>
              <td>
                <button style="padding:4px 8px; font-size:11px;" onclick="renderVideo('${d.name}')" class="btn-secondary">Render</button>
              </td>
            </tr>
          `;
        });
      });
  }

  function startGeneration() {
    const speed = document.getElementById('speed').value;
    const genre = document.getElementById('genre').value;
    fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `speed=${speed}&genre=${genre}`
    }).then(() => alert('Generation triggered! Watch logs.'));
  }

  function startBatchUpload() {
    fetch('/api/upload', { method: 'POST' })
      .then(() => alert('Batch uploader triggered!'));
  }

  function renderVideo(name) {
    fetch('/api/render', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `name=${name}`
    }).then(() => alert('Render triggered for ' + name));
  }

  function stopAllTasks() {
    fetch('/api/stop', { method: 'POST' })
      .then(() => alert('Killed all active background pipeline processes!'));
  }

  setInterval(updateStatus, 3000);
  setInterval(refreshTracks, 5000);
  updateStatus();
  refreshTracks();
</script>
</body>
</html>
"""

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass # Disable HTTP access log outputs to console to prevent log pollution

    def do_GET(self):
        if self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            global active_process
            task_status = "Idle"
            if active_process["process"] and active_process["process"].poll() is None:
                task_status = active_process["task_name"]
                
            status_info = check_edge_and_credits()
            status_info["task"] = task_status
            self.wfile.write(json.dumps(status_info).encode())
            
        elif self.path == "/api/hymns":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(get_hymns()).encode())
            
        elif self.path == "/api/logs":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    self.wfile.write(f.read().encode())
            else:
                self.wfile.write(b"No active logs yet.")
                
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode())

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode()
        params = urllib.parse.parse_qs(post_data)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        if self.path == "/api/generate":
            speed = params.get("speed", ["1.0x"])[0]
            genre = params.get("genre", ["psytrance"])[0]
            cmd = f"python -u _oneshot_cover.py"
            run_background_task(["python", "-u", "_oneshot_cover.py"], f"Suno Cover {speed} {genre}")
            self.wfile.write(json.dumps({"status": "started"}).encode())
            
        elif self.path == "/api/render":
            name = params.get("name", [""])[0]
            run_background_task(["python", "-u", "render_batch_videos.py", name], f"Video Render {name}")
            self.wfile.write(json.dumps({"status": "started"}).encode())
            
        elif self.path == "/api/upload":
            run_background_task(["python", "-u", "_batch_upload.py"], "YouTube Batch Upload")
            self.wfile.write(json.dumps({"status": "started"}).encode())
            
        elif self.path == "/api/stop":
            global active_process
            if active_process["process"]:
                try:
                    active_process["process"].terminate()
                    log_message(f"Terminated background process {active_process['task_name']}.")
                except Exception as e:
                    pass
                active_process["process"] = None
                active_process["task_name"] = "Idle"
            self.wfile.write(json.dumps({"status": "stopped"}).encode())

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8083), Handler)
    print("HymnMania Redesigned Dashboard running at http://localhost:8083/")
    server.serve_forever()
