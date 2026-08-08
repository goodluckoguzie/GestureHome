# GestureHome Phase 1

## Goal

One gesture → one actuator: **both hands up/down** controls the **white LED** on pin 13 (typical KS0085 wiring).

## Two codes only

```text
home_controller.py  ←→  gesture_home.ino  ←→  LED (pin 13)
     (laptop)              (Keyestudio)
```

## Hardware checklist

| Item | Required |
|------|----------|
| Keyestudio PLUS + sensor shield | Yes |
| USB cable | Yes |
| Laptop webcam | Yes |
| White LED module on D13 | Yes (usually pre-wired on shield) |
| Fan, servo, relay, LCD, PIR, MQ-2 | No (Phase 2+) |

Confirm kit model on the box (assumed **KS0085**).

## Phase 0 (optional)

Upload `firmware/phase0_led_blink/phase0_led_blink.ino` for Keyestudio blink test. See `docs/ARDUINO_LED.md`.

## Phase 1 test script

1. Upload `firmware/gesture_home/gesture_home.ino`.
2. Serial Monitor: `LIGHTS_ON` → LED on; `LIGHTS_OFF` → off.
3. `conda activate home`
4. `python home_controller.py`
5. OpenCV window: test keys `o` / `f`, then both-hands-up / both-hands-down.

## Python environment

```bash
conda activate home
pip install -r requirements.txt
```

## Serial protocol

Line-based ASCII, 9600 baud, newline-terminated:

- `LIGHTS_ON`
- `LIGHTS_OFF`

Arduino responds with `OK LIGHTS_ON` or `OK LIGHTS_OFF`.

## Tuning gestures

In `home_controller.py`:

- `HANDS_UP_Y`, default `0.42`
- `HANDS_DOWN_Y`, default `0.58`
- `COOLDOWN_S`, default `1.5`
- `STABLE_FRAMES`, default `4`

## Docs

- **`docs/ARDUINO_LED.md`**, Keyestudio KS0085 wiring and Arduino upload (LED)
- **`docs/MANUAL.md`**, full user manual (setup, run, gestures, manual controls)
- `docs/PHASE1.md`, hardware checklist
- `docs/BRANCHES.md`, branch guide

## Next (Phase 2)

Right pinch → door servo; left pinch → fan; fist hold → away mode; wide hands → brightness.
