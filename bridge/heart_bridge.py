#!/usr/bin/env python3
"""
ESP32 HEART SOUND MONITOR - Bluetooth Classic bridge

1. Pair ESP32 named ESP32-HEART with Windows.
2. Find the outgoing Bluetooth COM port.
3. Run:
       python heart_bridge.py COM7
4. Open:
       http://127.0.0.1:8080

The bridge reads the ESP32 BluetoothSerial text stream and exposes it
to the browser dashboard through a local HTTP API.
"""

import json, os, sys, threading, time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

try:
    import serial
except ImportError:
    print("Missing pyserial. Run: python -m pip install pyserial")
    raise

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PORT = 8080
BT_PORT = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ESP32_BT_PORT", "COM7")
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
        import re
        m=re.search(r"Sound #\s*(\d+)",line,re.I)
        if m: state["totalSounds"]=int(m.group(1))
        m=re.search(r"Heartbeat #\s*(\d+)",line,re.I)
        if m: state["totalBeats"]=int(m.group(1)); state["event"]="Heartbeat detected"
        m=re.search(r"S1-S2 gap\s*=\s*(\d+)\s*ms",line,re.I)
        if m: state["gap"]=int(m.group(1)); state["event"]="S2 detected"
        m=re.search(r"Total sounds\s*=\s*(\d+)",line,re.I)
        if m: state["sounds"]=int(m.group(1))
        m=re.search(r"S1-S2 pairs\s*=\s*(\d+)",line,re.I)
        if m: state["beats"]=int(m.group(1))
        m=re.search(r"BPM\s*=\s*([\d.]+)",line,re.I)
        if m: state["bpm"]=float(m.group(1)); state["updated"]=time.time()
        m=re.search(r"Difference\s*=\s*([+-]?[\d.]+)",line,re.I)
        if m: state["diff"]=float(m.group(1))

def serial_reader():
    print(f"Opening Bluetooth COM port {BT_PORT} at {BAUD} baud…")
    while True:
        try:
            with serial.Serial(BT_PORT, BAUD, timeout=1) as ser:
                print(f"Connected to {BT_PORT}. Waiting for ESP32 data…")
                while True:
                    raw=ser.readline()
                    if raw:
                        process(raw.decode("utf-8","replace"))
        except Exception as e:
            print(f"Bluetooth connection error: {e}")
            time.sleep(2)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass
    def send_json(self,obj):
        body=json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type","application/json")
        self.send_header("Cache-Control","no-store")
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Content-Length",str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=="/api/state":
            with lock:
                payload={"state":dict(state),"lines":list(lines)}
                lines.clear()
            self.send_json(payload); return
        if path=="/api/health":
            self.send_json({"ok":True,"bluetooth_port":BT_PORT}); return
        file_path=os.path.join(ROOT,"index.html" if path in ("/","") else path.lstrip("/"))
        if os.path.isfile(file_path):
            try:
                data=open(file_path,"rb").read()
                ctype="text/html" if file_path.endswith(".html") else "text/plain"
                self.send_response(200);self.send_header("Content-Type",ctype);self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)
            except Exception:
                self.send_error(500)
        else:self.send_error(404)

def main():
    print("ESP32 Heart Sound Monitor")
    print(f"Bluetooth port: {BT_PORT}")
    print(f"Dashboard: http://127.0.0.1:{PORT}")
    threading.Thread(target=serial_reader,daemon=True).start()
    server=ThreadingHTTPServer(("127.0.0.1",PORT),Handler)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=="__main__":
    main()
