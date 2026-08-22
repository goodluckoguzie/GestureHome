# GestureHome

**Hands-free smart home and security** — control a Keyestudio Smart Home kit with webcam gestures.

Webcam → MediaPipe → `home_controller.py` → USB serial (9600) → `gesture_home.ino` → **LED, door, fan, PIR security**.

| | |
|---|---|
| **Presentation** | **[View the IoT talk slides](https://goodluckoguzie.github.io/GestureHome/)** (Reveal.js, QAHE branded) |
| **Live demo** | `python home_controller.py` on branch `main` |
| **Kit** | Keyestudio PLUS + sensor shield (KS0085) |

---

## Presentation

5-minute QA Higher Education IoT talk — same Reveal.js style as the [PhD Viva deck](https://goodluckoguzie.github.io/Viva/).

**Slides:** https://goodluckoguzie.github.io/GestureHome/

Open fullscreen in Chrome. Keys: → next, ↓ extra detail on Architecture / Stack, **S** speaker notes.

---

## Quick start (`main`)

```bash
conda activate home
cd GestureHome
git checkout main
pip install -r requirements.txt
python home_controller.py
```

Upload `firmware/gesture_home/gesture_home.ino` to the Keyestudio board. Serial: **9600 baud** (`/dev/ttyUSB0` or `/dev/ttyACM0`).

### Gestures

| Gesture | Hold | Command | House |
|---------|------|---------|-------|
| Closed fist | 3s | `LIGHTS_ON` | White LED on |
| Open palm | 3s | `LIGHTS_OFF` | White LED off |
| 1 / 2 / 3 fingers | 2s | `FAN_SPEED_*` | Fan speed |
| Thumbs up | 2s | `FAN_STOP` | Fan off |
| Two fists | 2s | `DOOR_TOGGLE` | Door servo |
| Wave / two palms | 2s | `SECURITY_ON/OFF` | PIR alarm |

Keyboard backup while the demo window is focused: `o` / `f` lights, `1` `2` `3` fan, `0` stop, `d` door, `s` security.

---

## Architecture

```text
Hands → webcam → MediaPipe → home_controller.py → USB 9600 → Arduino kit → LED · door · fan · PIR
```

Wireframe diagrams for teaching: `docs/gesturehome-wireframe.svg` (and variants in `docs/`).

Local slides and assets: `talk/` — regenerate videos with `talk/scripts/`.

---

## Branches

| Branch | Use |
|--------|-----|
| **`main`** | Laptop webcam + OpenCV (`home_controller.py`) — default |
| **`upgrade/booth`** | Audience phones + projector booth |
| **`legacy/web-bridge`** | Browser + FastAPI bridge (`web/` + `bridge/`) |

See `docs/BRANCHES.md` and `GESTUREHOME_FOCUS_NOW.md` for booth setup and student wireframes.

---

## Links

- **Presentation:** https://goodluckoguzie.github.io/GestureHome/
- **Repository:** https://github.com/goodluckoguzie/GestureHome
