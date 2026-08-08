# GestureHome User manual (Phase 1)

Step-by-step guide: setup, run, gestures, manual controls, and troubleshooting.

## What this project does

Wave your hands at the webcam → **white LED** on the Keyestudio kit turns on or off.

**Phase 1 uses two programs:**

```text
home_controller.py  (laptop)  ──USB──►  gesture_home.ino  (board)  ──►  LED pin 13
```

---

## What you need

| Item | Notes |
|------|--------|
| Keyestudio PLUS + sensor shield | Assumed **KS0085**, check box label |
| USB cable | Laptop ↔ board |
| Webcam | Built-in or external |
| White LED on pin 13 | Usually pre-wired on shield |
| Laptop | Linux tested; Windows/macOS should work |

**Software:** Arduino IDE, conda env `home`, Python 3.9–3.12.

---

## Setup (first time)

### 1. Clone the repo

```bash
git clone https://github.com/goodluckoguzie/GestureHome.git
cd GestureHome
git checkout main
```

### 2. Python environment

```bash
conda env create -f environment.yml
conda activate home
pip install -r requirements.txt
```

First run downloads the hand model (~7.5 MB) into `models/` automatically.

### 3. Upload Arduino firmware

1. Open `firmware/gesture_home/gesture_home.ino` in Arduino IDE.
2. Board: **Arduino UNO** (Keyestudio PLUS).
3. Port: your USB port (e.g. `/dev/ttyUSB0`).
4. Upload.

### 4. Test firmware (Serial Monitor)

1. Arduino IDE → Tools → Serial Monitor.
2. Set baud to **9600**.
3. Type `LIGHTS_ON` → LED should glow.
4. Type `LIGHTS_OFF` → LED should go off.

If this fails, fix USB/firmware before running Python.

### 5. Smoke test (no board required)

```bash
conda activate home
python home_controller.py --self-test
```

Expect: `PASS: self-test 30 frames`.

---

## Run (every time)

```bash
cd GestureHome
conda activate home
python home_controller.py
```

Plug in the Keyestudio via USB before running (unless using `--no-serial`).

An **OpenCV window** opens: live camera + green hand skeleton.

---

## Gestures

| Action | Result |
|--------|--------|
| **Open palm** (5 fingers spread) held **3 seconds** | `LIGHTS_OFF` |
| **Closed fist** held **3 seconds** | `LIGHTS_ON` |
| No hand visible | Show your hand |
| Unclear pose | Hold open palm or close fist |

The on-screen timer shows progress (e.g. `Fist 2.1s / 3.0s → ON`).

With `--no-serial`, the on-screen **LED: ON/OFF** text still updates (preview mode). The physical LED needs USB and no `--no-serial`.

- **Cooldown:** 1.5 seconds between commands.
- **On-screen text** shows status (`Hands up (2/4)`, `LED: ON`, `USB: OK`).

---

## Manual controls (keyboard)

Use these if gestures are awkward or for testing serial without waving:

| Key | Action |
|-----|--------|
| **o** | Lights **on** (`LIGHTS_ON`) |
| **f** | Lights **off** (`LIGHTS_OFF`) |
| **q** | Quit |

Manual keys also respect the 1.5 s cooldown.

### Web UI manual buttons (`legacy/web-bridge` branch only)

On the browser UI, use **Lights on** / **Lights off** buttons in the side panel (same commands as keys `o` / `f`).

---

## Command-line options

```bash
python home_controller.py --port /dev/ttyUSB0    # explicit USB port
python home_controller.py --no-serial            # camera only, no Arduino
python home_controller.py --camera 1             # second webcam
python home_controller.py --self-test            # headless quick check
GESTURE_HOME_PORT=/dev/ttyACM0 python home_controller.py
```

---

## Branches

| Branch | Stack | How to run |
|--------|-------|------------|
| **`main`** | Python + Arduino | `python home_controller.py` |
| **`legacy/web-bridge`** | Chrome + FastAPI + Arduino | `python bridge/bridge.py` → http://127.0.0.1:8090/ |

See `docs/BRANCHES.md`.

---

## Architecture

```text
   YOU + WEBCAM
        │
        ▼
┌───────────────────┐
│ home_controller.py│  OpenCV window + MediaPipe hands
│ (conda env home)  │
└─────────┬─────────┘
          │ USB serial: LIGHTS_ON / LIGHTS_OFF
          ▼
┌───────────────────┐
│ gesture_home.ino  │  pin 13 → white LED
│ (Keyestudio)      │
└───────────────────┘
```

---

## Serial protocol

- **Baud:** 9600
- **Format:** ASCII line + newline
- **Commands:** `LIGHTS_ON`, `LIGHTS_OFF`
- **Arduino replies:** `OK LIGHTS_ON` or `OK LIGHTS_OFF`

---

## Tuning gestures

Edit constants at the top of `home_controller.py`:

| Constant | Default | Meaning |
|----------|---------|---------|
| `HANDS_UP_Y` | `0.42` | Lower = hands must be higher |
| `HANDS_DOWN_Y` | `0.58` | Higher = hands must be lower |
| `COOLDOWN_S` | `1.5` | Seconds between commands |
| `STABLE_FRAMES` | `4` | Frames to hold pose |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No USB port | `ls /dev/ttyUSB* /dev/ttyACM*`, replug cable, re-upload firmware |
| Permission denied on USB | `sudo chmod a+rw /dev/ttyUSB0` |
| `No USB serial port found` | Use `--no-serial` to test camera; plug board in |
| Camera won’t open | Close other apps using webcam; try `--camera 1` |
| Gestures too sensitive | Adjust `HANDS_UP_Y` / `HANDS_DOWN_Y` |
| Model download slow | Needs internet first run; check `models/hand_landmarker.task` |
| Wrong port auto-selected | Set `--port` or `GESTURE_HOME_PORT` |
| LED works in Serial Monitor but not Python | Same baud (9600); close Serial Monitor before Python (port is exclusive) |

---

## Repo layout

```text
GestureHome/
├── home_controller.py      # Main app (main branch)
├── firmware/gesture_home/gesture_home.ino
├── requirements.txt
├── environment.yml
├── docs/
│   ├── MANUAL.md           # This file
│   ├── PHASE1.md
│   └── BRANCHES.md
├── bridge/                 # legacy/web-bridge branch primary
└── web/                    # legacy/web-bridge branch primary
```

---

## Next phases (planned)

| Phase | Features |
|-------|----------|
| 2 | Door, fan, relay, LCD, more gestures |
| 3 | PIR / gas dashboard |
| 4 | ESP32 Wi‑Fi, polish |

---

## Related repos

- [PuzzleCam](https://github.com/goodluckoguzie/PuzzleCam), browser MediaPipe photobooth
- GestureHome `legacy/web-bridge`, similar browser + API pattern
