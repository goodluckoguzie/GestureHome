# GestureHome - what we are focusing on right now

**Product:** Gesture-controlled **Keyestudio Smart Home** kit (home security / IoT demo)  
**Kit:** Keyestudio PLUS + sensor shield (assumed **KS0085**)

**Rule:** Phase 1 = **one gesture → one actuator** (white LED on pin 13). Full PIR alarm / away mode is Phase 2+.

---

## Pipeline wireframes (`main` branch) - for students

Visual maps: hands → `home_controller.py` → USB → Arduino → LED.

| Style | File | Best for |
|-------|------|----------|
| Default | `docs/main-pipeline-wireframe.png` / `.svg` | Detailed script names |
| Alt 1 - Vertical timeline | `docs/gesturehome-alt1-vertical.png` | Step-by-step lesson |
| Alt 2 - Circular | `docs/gesturehome-alt2-circular.png` | Big picture around the house |
| Alt 3 - Swimlane | `docs/gesturehome-alt3-swimlane.png` | Engineering / CS students |
| Alt 4 - Classroom poster | `docs/gesturehome-alt4-classroom.png` | Beginners, non-coders |
| Alt 5 - Dark tech | `docs/gesturehome-alt5-dark-tech.png` | Coding / IoT club |

```text
  Both hands UP/DOWN (webcam)
           |
           v
  home_controller.py  (MediaPipe + gesture rules)
           |
           v USB serial LIGHTS_ON / LIGHTS_OFF
  gesture_home.ino  (pin 13 LED on Keyestudio house)
```

---

## Two main branches (pick your path)

GestureHome has **two primary branches** - same Arduino house, different **who holds the camera**:

| Branch | Who controls | Screen | Start command | Best for |
|--------|--------------|--------|---------------|----------|
| **`main`** | One person on the **laptop** | OpenCV window on laptop | `python home_controller.py` | Solo dev, classroom, quick hardware test |
| **`upgrade/booth`** | **Anyone with a phone** | Projector + audience phones | `./upgrade/run_booth.sh` | LaunchPoint, IoT showcase, home-security booth |

```text
main:
  Laptop webcam  →  home_controller.py  →  USB serial  →  gesture_home.ino  →  LED

upgrade/booth (phone):
  QR on projector  →  phone opens booth page  →  booth_bridge  →  USB  →  house
```

There is also a **third, older** path on `legacy/web-bridge` (Chrome on the **same laptop**, not audience phones). Use that only if you want a browser UI without the booth setup.

---

## Branch 1 - `main` (laptop)

```bash
conda activate home
cd GestureHome
git checkout main
python home_controller.py
```

```text
┌─────────────────────────────────────────────────────────────┐
│  PYTHON - home_controller.py                                │
│  Webcam + hand gestures → USB serial → LED                  │
│  Firmware: firmware/gesture_home.ino                        │
└─────────────────────────────────────────────────────────────┘
         │ USB serial (9600 baud)
         ▼
┌─────────────────────────────────────────────────────────────┐
│  ARDUINO - pin 13 white LED                                 │
│  LIGHTS_ON / LIGHTS_OFF                                     │
└─────────────────────────────────────────────────────────────┘
```

### Gesture rules (Phase 1)

| Gesture | Action | Serial command |
|---------|--------|----------------|
| Both hands up (stable) | White LED **on** | `LIGHTS_ON` |
| Both hands down (stable) | White LED **off** | `LIGHTS_OFF` |
| Keys `o` / `f` | Manual on / off | same commands |
| Key `q` | Quit | - |

Tuning: `HANDS_UP_Y`, `HANDS_DOWN_Y`, `COOLDOWN_S`, `STABLE_FRAMES` in `home_controller.py`.

### Useful flags (`main`)

| Flag | Purpose |
|------|---------|
| `--no-serial` | Camera + skeleton only (no Arduino) |
| `--port /dev/ttyUSB0` | Pick USB port manually |
| `--no-mirror` | Raw camera (no horizontal flip) |
| `--self-test` | Headless 30-frame camera + model smoke test |

---

## Branch 2 - `upgrade/booth` (phone)

Audience scans a **QR code on the projector**, opens the page on their **phone**, uses the **phone camera**, and controls the **real house** on your table.

```bash
conda activate home
cd GestureHome
git checkout upgrade/booth
pip install -r requirements.txt -r bridge/requirements.txt
./upgrade/run_booth.sh
```

| Surface | Page | Role |
|---------|------|------|
| **Projector** | `upgrade/web/host.html` | QR code, join URL, live house status, gesture cheat sheet |
| **Phone** | `upgrade/web/booth.html` | Camera, hand tracking, sends gestures to laptop bridge |
| **Laptop** | `upgrade/booth_bridge.py` | HTTPS + API; forwards gestures to USB serial |

Physical kit on `upgrade/booth` can drive lights, fan, door servo, LCD, buzzer, and PIR security - beyond Phase 1 LED-only on `main`.

---

## ✅ Focusing on right now

Depends which branch you are on:

| Branch | Focus now | Technology |
|--------|-----------|------------|
| **`main`** | Phase 1 LED via laptop webcam | **Python**, OpenCV, MediaPipe, **C++** Arduino |
| **`upgrade/booth`** | Phone gestures → real house at events | **HTML/JS** booth pages, **Python** `booth_bridge`, Arduino |

Shared across both:

- **Serial protocol:** `LIGHTS_ON` / `LIGHTS_OFF` (and more on booth firmware)
- **Firmware:** `gesture_home.ino` (paths differ slightly per branch)
- **Gestures:** both hands up → on; both hands down → off (Phase 1 baseline)

### Setup checklist (`main`)

1. Upload `firmware/gesture_home.ino` to Keyestudio (9600 baud).
2. Serial Monitor: `LIGHTS_ON` / `LIGHTS_OFF` → LED toggles.
3. `pip install -r requirements.txt`
4. `python home_controller.py` → raise/lower both hands.

---

## ❌ Not focusing on right now

| Part | Branch / path | Why not now |
|------|---------------|-------------|
| **`legacy/web-bridge`** | Laptop Chrome + `bridge/bridge.py` (port 8090) | Older 3-layer stack; prefer `main` or `upgrade/booth` |
| **Phase 2+ on `main`** | Fan, servo, PIR alarm, MQ-2, away mode | Documented in `docs/PHASE1.md` as next steps |
| **WindmillStretch** | Different repo folder | Exercise coach, not smart home |

### `legacy/web-bridge` (optional, not a main path)

```bash
git checkout legacy/web-bridge
pip install -r bridge/requirements.txt
python bridge/bridge.py
# Open http://127.0.0.1:8090/ in Chrome on the laptop
```

---

## Per-frame pipeline (`main` - `home_controller.py`)

```text
Webcam frame
  → mirror (optional)
  → MediaPipe Hand Landmarker (2 hands)
  → draw hand skeleton on frame
  → average wrist height → up / down / neutral
  → stable frames + cooldown
  → serial: LIGHTS_ON or LIGHTS_OFF
  → OpenCV window + status text
```

---

## Related docs

| File | Contents |
|------|----------|
| `docs/PHASE1.md` | Phase 1 goal, hardware, serial protocol |
| `docs/BRANCHES.md` | All three branches |
| `upgrade/README.md` | Booth assets (on `upgrade/booth`) |
| `README.md` | Quick start (content varies by checked-out branch) |

---

## Compare to WindmillStretch

| | **GestureHome** | **WindmillStretch** |
|--|-----------------|---------------------|
| Goal | Control **smart home** with **hands** | **Exercise coach** with **body pose** |
| Main command (`main`) | `python home_controller.py` | `python -m coach.journey_coach --windowed` |
| Phone branch | `upgrade/booth` → `./upgrade/run_booth.sh` | - |
| Output | USB → **physical house** | On-screen coaching + optional SQLite |
| Focus doc | `GESTUREHOME_FOCUS_NOW.md` | `windmill_stretch/WINDMILL_FOCUS_NOW.md` |

---

*Last updated: two main branches - `main` (laptop) and `upgrade/booth` (phone); `legacy/web-bridge` is legacy.*
