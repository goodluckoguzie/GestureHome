# Branches

| Branch | Approach | Use when |
|--------|----------|----------|
| **`main`** | **Python + Arduino** (`home_controller.py`) | Default, easier to learn, one Python script |
| **`legacy/web-bridge`** | **Chrome + FastAPI** (`web/` + `bridge/`) | Browser UI like PuzzleCam |

Both branches share the same **Arduino firmware** (`firmware/gesture_home/gesture_home.ino`).

```bash
git checkout main                 # Python + OpenCV window
git checkout legacy/web-bridge    # Browser at http://127.0.0.1:8090/
```
