#!/usr/bin/env python3
"""
ESP32 HEART SOUND MONITOR - Bluetooth Classic bridge.

Can be run directly:
    python heart_bridge.py COM7

It can also be imported by HeartMonitor.exe.
"""

import json
import os
import re
import sys
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

try:
    import serial
except ImportError:
    serial = None

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PORT = 8080
BAUD = 115200

lines = deque(maxlen=300)
lock = threading.Lock()
state = {
    "bpm": None, "beats": 0, "sounds": 0, "gap": None,
    "totalSounds": 0, "totalBeats": 0, "event": None,
    "diff": None, "updated": None
}

def process(line):
    line = line.strip()
    if not line:
        return
    with lock:
        lines.append(line)

        m = re.search(r"Sound #\s*(\d+)", line, re.I)
        if m:
            state["totalSounds"] = int(m.group(1))

        m = re.search(r"Heartbeat #\s*(\d+)", line, re.I)
        if m:
            state["totalBeats"] = int(m.group(1))
            state["event"] = "Heartbeat detected"

        m = re.search(r"S1-S2 gap\s*=\s*(\d+)\s*ms", line, re.I)
        if m:
            state["gap"] = int(m.group(1))
            state["event"] = "S2 detected"

        m = re.search(r"Total sounds\s*=\s*(\d+)", line, re.I)
        if m:
            state["sounds"] = int(m.group(1))

        m = re.search(r"S1-S2 pairs\s*=\s*(\d+)", line, re.I)
        if m:
            state["beats"] = int(m.group(1))

        # IMPORTANT: only accept the actual ESP32 BPM result line.
        m = re.fullmatch(r"BPM\s*=\s*(\d+(?:\.\d+)?)", line, re.I)
        if m:
            measured = float(m.group(1))
            if measured >= 0:
                state["bpm"] = measured
                state["updated"] = time.time()

        m = re.search(r"Difference\s*=\s*([+-]?[\d.]+)", line, re.I)
        if m:
            state["diff"] = float(m.group(1))

def serial_reader(bt_port):
    if serial is None:
        print("Missing pyserial. Install with: python -m pip install pyserial")
        return

    print(f"Opening Bluetooth COM port {bt_port} at {BAUD} baud...")
    while True:
        try:
            with serial.Serial(bt_port, BAUD, timeout=1) as ser:
                print(f"Connected to {bt_port}. Waiting for ESP32 data...")
                while True:
                    raw = ser.readline()
                    if raw:
                        process(raw.decode("utf-8", "replace"))
        except Exception as e:
            print(f"Bluetooth connection error: {e}")
            time.sleep(2)

def start(bt_port):
    """Start the Bluetooth reader and local dashboard server."""
    global ROOT
    if getattr(sys, "frozen", False):
        ROOT = os.path.dirname(sys.executable)

    threading.Thread(target=serial_reader, args=(bt_port,), daemon=True).start()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def send_json(self, obj):
            body = json.dumps(obj).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlparse(self.path).path

            if path == "/api/state":
                with lock:
                    payload = {"state": dict(state), "lines": list(lines)}
                    lines.clear()
                self.send_json(payload)
                return

            if path == "/api/health":
                self.send_json({"ok": True, "bluetooth_port": bt_port})
                return

            rel = "index.html" if path in ("/", "") else path.lstrip("/")
            file_path = os.path.join(ROOT, rel)

            if os.path.isfile(file_path):
                try:
                    with open(file_path, "rb") as f:
                        data = f.read()
                    if file_path.endswith(".html"):
                        ctype = "text/html; charset=utf-8"
                    elif file_path.endswith(".js"):
                        ctype = "application/javascript"
                    elif file_path.endswith(".css"):
                        ctype = "text/css"
                    else:
                        ctype = "text/plain"
                    self.send_response(200)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                except Exception:
                    self.send_error(500)
            else:
                self.send_error(404)

    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    return server

def main():
    bt_port = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ESP32_BT_PORT", "COM7")
    print("ESP32 Heart Sound Monitor")
    print(f"Bluetooth port: {bt_port}")
    print(f"Dashboard: http://127.0.0.1:{PORT}")
    server = start(bt_port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
