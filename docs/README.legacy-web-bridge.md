# GestureHome (legacy/web-bridge branch)

Control a **Keyestudio Smart Home** kit with **webcam gestures** via **Chrome + FastAPI bridge**.

**Phase 1:** both hands up → white LED on; both hands down → LED off.

> **Note:** This branch documents the **browser + bridge** stack. For the simpler **Python + Arduino** approach, switch to `main`.

## Architecture (3 layers)

```text
Chrome (camera + UI)  →  bridge.py (FastAPI)  →  USB serial  →  gesture_home.ino  →  LED
```

| Layer | Path |
|-------|------|
| Web UI | `web/`, MediaPipe in browser |
| Bridge | `bridge/bridge.py`, port **8090** |
| Firmware | `firmware/gesture_home/gesture_home.ino` |

## Quick start

### 1. Firmware

Upload `firmware/gesture_home/gesture_home.ino` to Keyestudio PLUS (Arduino UNO). Test Serial Monitor at 9600: `LIGHTS_ON` / `LIGHTS_OFF`.

### 2. Bridge + web

```bash
conda activate home
pip install -r bridge/requirements.txt
python bridge/bridge.py
```

Open **http://127.0.0.1:8090/** in Chrome.

### 3. Gestures

Both hands up → on. Both hands down → off. Manual buttons on the side panel.

## Alternative on `main`

```bash
git checkout main
python home_controller.py   # OpenCV window, no browser
```
