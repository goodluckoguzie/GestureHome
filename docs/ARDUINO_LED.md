# Keyestudio KS0085 - Arduino LED setup (Phase 1)

Start with the **white LED only** on the smart home kit. Door, fan, buzzer, and sensors come in later phases.

## Hardware

| Item | Detail |
|------|--------|
| Board | Keyestudio **PLUS** (Arduino UNO compatible) |
| Shield | Keyestudio **sensor shield** (stacked on PLUS) |
| LED | **White LED module** (3-pin: G, V, S) |
| Wiring | G → G, V → V, S → **D13** on shield |
| House position | ① on the wooden board (Keyestudio diagram) |

Official docs: [KS0085 installation](https://docs.keyestudio.com/projects/KS0085/en/latest/docs/2.%20Product%20installation/2.%20Product%20installation.html)

## Phase 0 - blink test (factory style)

Confirms wiring before custom code.

1. Arduino IDE → Open `firmware/phase0_led_blink/phase0_led_blink.ino`
2. Board: **Arduino UNO**, correct USB port
3. Upload
4. White LED should blink **1 s on / 1 s off**

If this fails, fix shield, LED plug, or USB before continuing.

## Phase 1 - GestureHome firmware

Serial-controlled LED (for Python `home_controller.py`).

1. Open `firmware/gesture_home/gesture_home.ino`
2. Upload (same board and port)
3. Serial Monitor → **9600 baud**, newline:
   - `LIGHTS_ON` → LED on
   - `LIGHTS_OFF` → LED off
   - `STATUS` → reports on/off
   - `HELP` → command list

On boot, the LED **blinks twice** quickly, then waits for commands.

While Python tracks your hold (`HOLD_ON`), the LED **blinks** like Phase 0. After 3 seconds it turns **solid ON** or **solid OFF**.

## Pin map (for later phases)

Defined in `firmware/gesture_home/ks0085_pins.h`:

| Pin | Device | Phase |
|-----|--------|-------|
| D13 | White LED | **1** (now) |
| D5 | Yellow LED | 2 |
| D9 | Door servo | **2** |
| I2C | LCD1602 (0x27) | **2** |
| D10 | Window servo | 2 |
| D8 | Relay | 2 |
| D6 | Buzzer | 2 |
| D3 | PIR motion | 3 |
| A0 | Gas MQ-2 | 3 |

## Connect to Python

After firmware works in Serial Monitor:

```bash
conda activate home
python home_controller.py
```

Gestures: **fist 3 s** → ON, **open palm 3 s** → OFF.

Close Serial Monitor before running Python (only one program can use USB serial).

## Troubleshooting

| Problem | Fix |
|---------|-----|
| LED never lights | Run Phase 0 blink first; check G/V/S on D13 |
| Upload fails | Select **Arduino UNO**; try another USB cable |
| Serial works, Python fails | Close Serial Monitor; check `ls /dev/ttyUSB*` |
| Wrong port on Linux | `python home_controller.py --port /dev/ttyUSB0` |
