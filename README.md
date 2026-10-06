# ESP32 Bluetooth Heart Sound Monitor

A responsive web dashboard for the ESP32 Bluetooth Classic SPP heart-sound monitor.

## Architecture

The ESP32 uses Bluetooth Classic, so the hosted website does not connect directly to the ESP32.

ESP32 → Bluetooth Classic → Windows Bluetooth COM port → Heart Monitor bridge → Web dashboard

The dashboard itself can be hosted on any static web platform. The bridge runs on the Windows computer that has the ESP32 Bluetooth connection.

## Website

index.html is hosting-ready.

After uploading it to your external hosting platform, open the hosted URL. In Live Data Source, enter:

http://127.0.0.1:8080

when the Heart Monitor bridge is running on the same computer.

If the bridge is available at another HTTP address, enter that address instead. The selected address is saved in the browser.

## What the dashboard shows

- Actual ESP32 5-second BPM
- Heartbeats / 5 seconds
- Sounds / 5 seconds
- S1-S2 gap
- Total sounds
- Total heartbeats
- Last detected event
- Difference from the ESP32 reference value of 72 BPM
- Live Bluetooth messages
- BPM trend graph
- Bridge connection status

Important: the dashboard does not replace the ESP32 BPM calculation and does not force the display to 72 BPM. It displays the numeric BPM = ... result received from the ESP32.

## Windows one-click application

The repository includes a Windows launcher at launcher/HeartMonitor.py and a GitHub Actions workflow at .github/workflows/build-heart-monitor.yml.

The workflow builds HeartMonitor.exe. The EXE is intended to be the user-facing launcher: double-click it, and it starts the bridge and opens the dashboard automatically.

## Bluetooth setup

1. Upload the ESP32 sketch.
2. Power the ESP32.
3. Pair ESP32-HEART with Windows.
4. Windows creates a Bluetooth SPP COM port.
5. Start HeartMonitor.exe.

The launcher attempts to identify the Bluetooth COM port automatically.

If Windows has no usable Bluetooth SPP COM port, the hardware connection still needs to be repaired in Windows first.

## External hosting

You can upload only index.html to most static hosting platforms for the visual website.

For live ESP32 data, the Windows computer running the Bluetooth bridge must remain available and reachable by the browser.

### HTTPS hosting note

If your hosting platform serves the site over HTTPS, the browser may apply secure-content restrictions when connecting to a local HTTP bridge. If that happens, use a secure/reverse-proxied API endpoint for the bridge or host the dashboard through the local bridge itself.

## ESP32 message format

The bridge understands:

- S1 detected
- S2 detected
- S1-S2 gap = XXX ms
- Heartbeat #N
- Total sounds = N
- S1-S2 pairs = N
- BPM = XX.X
- Difference = X.X

## Current BPM calculation

The current ESP32 sketch calculates: BPM = number of S1-S2 pairs in 5 seconds × 12.

The website displays that result exactly as received.

For a physiologically stronger implementation, BPM should eventually be derived from successive S1-to-S1 intervals with artifact rejection.

## USB audio

The ESP32 also sends a separate binary USB audio stream: A5 5A 80 [128 audio bytes] CHECKSUM.

This is intentionally separate from the Bluetooth text data.

## Repository files

- index.html — responsive, externally hostable dashboard
- bridge/heart_bridge.py — Bluetooth Classic to HTTP bridge
- bridge/requirements.txt — Python dependency
- launcher/HeartMonitor.py — one-click Windows launcher source
- .github/workflows/build-heart-monitor.yml — Windows EXE build workflow

Repository: https://github.com/sukritmodak/blootooth_heart