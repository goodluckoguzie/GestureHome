# Branches

GestureHome has **two main branches** plus one legacy path.

| Branch | Who uses the camera | UI | Start | Use when |
|--------|---------------------|-----|-------|----------|
| **`main`** | Person on **laptop** | OpenCV window | `python home_controller.py` | Default - learn Python + Arduino, solo demo |
| **`upgrade/booth`** | **Audience on phones** | Projector + phone browser | `./upgrade/run_booth.sh` | Events, LaunchPoint, phone-controlled booth |
| **`legacy/web-bridge`** | Person on **laptop** (Chrome) | Browser at port 8090 | `python bridge/bridge.py` | Older browser stack (like PuzzleCam) |

All branches drive the same **Keyestudio house** over USB serial and share similar **Arduino firmware**.

```bash
git checkout main                 # laptop webcam + OpenCV
git checkout upgrade/booth        # phone gestures + projector booth
git checkout legacy/web-bridge    # laptop Chrome + FastAPI bridge
```

## Quick comparison

```text
main:
  Laptop webcam → home_controller.py → USB → Arduino → LED (Phase 1)

upgrade/booth:
  Phone camera → booth.html → booth_bridge.py → USB → Arduino → full kit

legacy/web-bridge:
  Laptop Chrome → web/ + bridge/bridge.py → USB → Arduino → LED
```

See `GESTUREHOME_FOCUS_NOW.md` for what to focus on in each path.
