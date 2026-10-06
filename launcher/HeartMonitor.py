import os
import sys
import time
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox

import serial.tools.list_ports

# The Bluetooth bridge lives in ../bridge in the repository.\nBRIDGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bridge"))\nif BRIDGE_DIR not in sys.path:\n    sys.path.insert(0, BRIDGE_DIR)\nimport heart_bridge

APP_TITLE = "ESP32 Heart Monitor"
DASHBOARD = "http://127.0.0.1:8080"

def find_bluetooth_port():
    preferred = os.environ.get("ESP32_BT_PORT")
    if preferred:
        return preferred

    ports = list(serial.tools.list_ports.comports())

    # Prefer Bluetooth SPP ports whose Windows description mentions Bluetooth.
    for p in ports:
        text = f"{p.device} {p.description} {p.manufacturer or ''}".lower()
        if "bluetooth" in text or "esp32-heart" in text:
            return p.device

    # Keep the user's current setup as the first fallback.
    for p in ports:
        if p.device.upper() == "COM7":
            return p.device

    return ports[0].device if ports else None

def start():
    port = find_bluetooth_port()

    if not port:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            APP_TITLE,
            "No Bluetooth COM port was found.\n\n"
            "Pair ESP32-HEART with Windows and try again."
        )
        root.destroy()
        return

    server = heart_bridge.start(port)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    time.sleep(0.8)
    webbrowser.open(DASHBOARD)

    # Small hidden Tk event loop keeps the application alive.
    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry("1x1")
    root.withdraw()

    def close():
        try:
            server.shutdown()
            server.server_close()
        finally:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", close)
    root.after(1000, lambda: None)
    root.mainloop()

if __name__ == "__main__":
    start()
