#!/usr/bin/env python
"""
Launch Edge with remote debugging on port 9222 for Suno automation.

Usage:
    python scripts/launch_edge_suno.py [--user-data-dir <path>]
"""

import os
import sys
import subprocess
import socket
import time
import argparse


EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_edge():
    """Find Edge browser executable."""
    for path in EDGE_PATHS:
        if os.path.exists(path):
            return path
    
    # Try searching PATH
    import shutil
    edge = shutil.which("msedge") or shutil.which("msedge.exe")
    if edge:
        return edge
    
    raise FileNotFoundError(
        "Microsoft Edge not found. Please install Edge or specify the path."
    )


def is_port_open(port=9222):
    """Check if a port is open."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(("127.0.0.1", port))
    sock.close()
    return result == 0


def launch_edge(port=9222, user_data_dir=None):
    """Launch Edge with remote debugging enabled."""
    if is_port_open(port):
        print(f"Port {port} is already open. Edge is probably already running with CDP.")
        return True

    edge_path = find_edge()
    print(f"Found Edge: {edge_path}")

    if user_data_dir is None:
        user_data_dir = os.path.join(os.environ.get("LOCALAPPDATA", "."), "EdgeSunoProfile")
    
    os.makedirs(user_data_dir, exist_ok=True)

    cmd = [
        edge_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "https://suno.com/create",
    ]

    print(f"Launching Edge with CDP on port {port}...")
    print(f"  User data dir: {user_data_dir}")
    print(f"  Opening: suno.com/create")

    subprocess.Popen(cmd, shell=True)

    # Wait for CDP to be ready
    print("Waiting for CDP connection...")
    for i in range(30):
        if is_port_open(port):
            print(f"✓ Edge is ready! CDP port {port} is open.")
            time.sleep(3)  # Give Suno a moment to load
            return True
        time.sleep(1)
    
    print("⚠ Timed out waiting for Edge. Check manually.")
    return False


def main():
    parser = argparse.ArgumentParser(description="Launch Edge with CDP for Suno")
    parser.add_argument("--port", type=int, default=9222, help="CDP port (default: 9222)")
    parser.add_argument("--user-data-dir", help="Custom user data directory")
    args = parser.parse_args()

    if is_port_open(args.port):
        print(f"Port {args.port} is already open. Edge CDP is running.")
        print("If you need to restart, close Edge first.")
        sys.exit(0)

    success = launch_edge(args.port, args.user_data_dir)
    if success:
        print("\n✓ Edge launched successfully!")
        print("  - Log into Suno.com if needed")
        print("  - Navigate to the Create page")
        print("  - Then run: python scripts/full_suno_pipeline.py <midi_file>")
    else:
        print("\n⚠ Edge may not have started. Try launching manually:")
        print(f'  "{EDGE_PATHS[0]}" --remote-debugging-port={args.port} https://suno.com/create')
        sys.exit(1)


if __name__ == "__main__":
    main()
