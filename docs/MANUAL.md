# GestureHome user manual

Complete guide: wiring, setup, gestures, keyboard controls, serial protocol, and troubleshooting.

## What GestureHome does

Point your webcam at your hands. MediaPipe tracks your pose and `home_controller.py` sends commands over USB serial. `gesture_home.ino` on the Keyestudio board drives the physical house: lights, fan, door, LCD, buzzer, and PIR security alarm.

```text
Webcam  ->  home_controller.py  ->  USB serial (9600)  ->  gesture_home.ino  ->  house modules
```

### Main files (do not duplicate logic elsewhere)

| File | Role |
|------|------|
| `home_controller.py` | Camera, gestures, serial on the laptop |
| `firmware/gesture_home/gesture_home.ino` | Firmware on the board |
| `firmware/gesture_home/ks0085_pins.h` | Pin map for your wiring |

## Wiring and kit photos

- **Wireframe diagram:** [assets/ks0085-wiring.png](assets/ks0085-wiring.png) (also on the [README](../README.md))
- **Kit photo:** [assets/ks0085-kit-overview.png](assets/ks0085-kit-overview.png)
- **Hardware setup:** [ARDUINO_LED.md](ARDUINO_LED.md) (upload, Serial Monitor, pin table)

## What you need

| Item | Notes |
|------|--------|
| Keyestudio KS0085 kit | PLUS board + sensor shield + house model |
| USB cable | Laptop to board |
| Webcam | Built-in or external |
| Arduino IDE | Upload `gesture_home.ino` |
| Python 3.9-3.12 | Conda env `home` |

## Setup (first time)

### 1. Clone the repo

```bash
git clone https://github.com/goodluckoguzie/GestureHome.git
cd GestureHome
git checkout main
```

### 2. Wire the kit

Stack the sensor shield on the PLUS board. Wire modules per the [wiring table](../README.md#wiring-and-connections) or use the kit's pre-wired layout.

### 3. Python environment

```bash
conda env create -f environment.yml
conda activate home
pip install -r requirements.txt
```

First run downloads the hand model (~7.5 MB) into `models/`.

### 4. Upload firmware

1. Open `firmware/gesture_home/gesture_home.ino` in Arduino IDE
2. Board: **Arduino UNO** (Keyestudio PLUS)
3. Port: e.g. `/dev/ttyUSB0`
4. Upload

Optional first step: blink test with `firmware/phase0_led_blink/phase0_led_blink.ino` (see [ARDUINO_LED.md](ARDUINO_LED.md)).

### 5. Test firmware (Serial Monitor)

1. Arduino IDE -> Tools -> Serial Monitor, **9600 baud**
2. Type `LIGHTS_ON` and `LIGHTS_OFF`
3. Type `HELP` for the full command list

Close Serial Monitor before running Python.

### 6. Smoke test (no board)

```bash
conda activate home
python home_controller.py --self-test
```

Expect: `PASS: self-test 30 frames`.

## Run (every time)

```bash
cd GestureHome
conda activate home
python home_controller.py --port /dev/ttyUSB0
```

Plug in the board via USB before running (unless using `--no-serial`).

An **OpenCV window** opens with live camera, green hand skeleton, and status text.

## Gestures

Hold each pose until the on-screen timer completes. Short cooldown between commands (~0.5 s).

| Action | Gesture | Hold time |
|--------|---------|-----------|
| Lights ON | One closed fist | 3 s (LED blinks while holding) |
| Lights OFF | One open palm | 3 s (LED blinks while holding) |
| Fan speed 1 / 2 / 3 | 1, 2, or 3 extended fingers | 2 s |
| Fan stop | Thumbs up | 2 s |
| Door toggle | Two closed fists | 2 s |
| Security arm / disarm | Wave ~2 s, or two open palms (10 fingers) | 2 s |

On-screen text shows progress (e.g. `Fist 2.1s / 3.0s blink->ON`).

When security is armed, PIR motion triggers yellow LED blink and buzzer alarm on the house.

With `--no-serial`, gestures still update the on-screen preview; the physical house needs USB and no `--no-serial`.

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| `o` | Lights on |
| `f` | Lights off |
| `1` / `2` / `3` | Fan speed 1 / 2 / 3 |
| `0` | Fan stop |
| `d` | Door toggle |
| `s` | Security arm / disarm |
| `q` | Quit |

Keyboard commands use the same cooldown as gestures.

## Command-line options

```bash
python home_controller.py --port /dev/ttyUSB0    # explicit USB port
python home_controller.py --no-serial            # camera only, no board
python home_controller.py --camera 1             # second webcam
python home_controller.py --self-test            # headless quick check
GESTURE_HOME_PORT=/dev/ttyACM0 python home_controller.py
```

## Branches

| Branch | Stack | How to run |
|--------|-------|------------|
| **`main`** | Python + Arduino | `python home_controller.py` |
| **`legacy/web-bridge`** | Chrome + FastAPI + Arduino | `python bridge/bridge.py` -> http://127.0.0.1:8090/ |
| **`upgrade/booth`** | Browser booth UI + API | See `upgrade/README.md` on that branch |

See [BRANCHES.md](BRANCHES.md).

## Architecture

```text
   YOU + WEBCAM
        |
        v
+-------------------+
| home_controller.py|  OpenCV + MediaPipe + gesture rules
| (conda env home)  |
+---------+---------+
          | USB serial (9600)
          v
+-------------------+
| gesture_home.ino  |  D13 lights, D7/D6 fan, D9 door,
| (Keyestudio)      |  D3 buzzer, D2 PIR, D5 yellow LED, I2C LCD
+-------------------+
```

## Serial protocol

- **Baud:** 9600
- **Format:** ASCII line + newline
- **Commands sent by Python:**

  `LIGHTS_ON`, `LIGHTS_OFF`, `HOLD_ON`, `HOLD_OFF`,  
  `FAN_SPEED_1`, `FAN_SPEED_2`, `FAN_SPEED_3`, `FAN_STOP`,  
  `DOOR_TOGGLE`, `SECURITY_ON`, `SECURITY_OFF`

- **Diagnostics:** `STATUS`, `HELP`
- **Typical reply:** `OK LIGHTS_ON`, `OK FAN_SPEED_2`, etc.

## Tuning gestures

Edit constants at the top of `home_controller.py`:

| Constant | Default | Meaning |
|----------|---------|---------|
| `HOLD_S` | `3.0` | Hold time for lights (seconds) |
| `FAN_HOLD_S` | `2.0` | Hold time for fan gestures |
| `DOOR_HOLD_S` | `2.0` | Hold time for door toggle |
| `SEC_HOLD_S` | `2.0` | Hold time for security arm/disarm |
| `COOLDOWN_S` | `0.5` | Gap between commands |
| `WAVE_MIN_AMP` | `0.07` | Wave detection sensitivity |
| `WAVE_MIN_SWINGS` | `3` | Swings needed for wave gesture |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No USB port | `ls /dev/ttyUSB* /dev/ttyACM*`, replug cable, re-upload firmware |
| Permission denied on USB | `sudo chmod a+rw /dev/ttyUSB0` |
| `No USB serial port found` | Use `--no-serial` to test camera; plug board in |
| Camera won't open | Close other apps; try `--camera 1` |
| Gestures hard to trigger | Good lighting; test with keyboard keys first |
| Model download slow | Needs internet on first run; check `models/hand_landmarker.task` |
| Wrong port auto-selected | Set `--port` or `GESTURE_HOME_PORT` |
| LED works in Serial Monitor but not Python | Close Serial Monitor (port is exclusive); same baud 9600 |
| Fan or door no response | Re-check wiring in [ARDUINO_LED.md](ARDUINO_LED.md) |

## Repo layout

```text
GestureHome/
├── home_controller.py              # Main app
├── firmware/gesture_home/
│   ├── gesture_home.ino            # Main firmware
│   └── ks0085_pins.h               # Pin map
├── docs/
│   ├── MANUAL.md                   # This file
│   ├── ARDUINO_LED.md              # Hardware setup
│   ├── assets/                     # Wiring diagram + kit photos
│   └── BRANCHES.md
├── environment.yml
├── requirements.txt
├── bridge/                         # legacy/web-bridge branch
└── web/                            # legacy/web-bridge branch
```
