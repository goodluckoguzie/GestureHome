# Legacy: browser + FastAPI bridge

Phase 1 can also run via **Chrome + `bridge/bridge.py`** (port **8090**).

This is the older 3-layer setup:

```text
web/ (gestures.js)  →  bridge/bridge.py  →  USB serial  →  gesture_home.ino
```

Use it if you prefer a web UI (similar to PuzzleCam). The **recommended** path is `home_controller.py` (Python + Arduino only).

```bash
conda activate home
pip install fastapi uvicorn pydantic pyserial
python bridge/bridge.py
# Open http://127.0.0.1:8090/
```
