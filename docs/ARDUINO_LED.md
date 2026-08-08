# Keyestudio KS0085 hardware setup

Wiring, firmware upload, and Serial Monitor tests for the GestureHome smart home kit.

## Kit overview

The numbers etched on the wooden panels (1, 2, 3, 4, 5, 11-14) match the **house slot** column in the wiring table below.

![Assembled Keyestudio KS0085 smart home model with labeled sensors and modules](assets/ks0085-kit-overview.png)

For a pin-level wireframe (shield rows and signal pins), see the main README or [ks0085-wiring.png](assets/ks0085-wiring.png).

## Hardware checklist

| Item | Detail |
|------|--------|
| Board | Keyestudio **PLUS** (Arduino UNO compatible) |
| Shield | Keyestudio **sensor shield** (stacked on PLUS) |
| USB cable | Laptop to board |
| Modules | LED, LCD, fan, door servo, buzzer, PIR (see pin table) |

Official assembly guide: [KS0085 installation](https://docs.keyestudio.com/projects/KS0085/en/latest/docs/2.%20Product%20installation/2.%20Product%20installation.html)

## Wiring table

Plug each module into the shield: **G** (ground), **V** (5 V), and the signal pin on the same row.

| Module | House slot | Shield wires | Arduino pin | Role in GestureHome |
|--------|------------|--------------|-------------|---------------------|
| White LED | slot 1 | G, V, S | **D13** | Room lights on/off |
| LCD1602 (I2C) | slot 2 | GND, VCC, SDA, SCL | **A4/A5** (`0x27`) | Status text |
| Buzzer | - | G, V, S | **D3** | Sound cues and alarm |
| PIR motion | - | G, V, S | **D2** | Motion (security mode) |
| Yellow LED | slot 12 | G, V, S | **D5** | Alarm indicator blink |
| Fan driver | slot 15 | GND, VCC, INA, INB | **D7**, **D6** | Fan speed 1/2/3 |
| Door servo | - | signal wire | **D9** | Door open/close |

All `#define` values live in `firmware/gesture_home/ks0085_pins.h`. Edit that file if you rewire a module.

Optional modules (defined in pins header, not required for the default demo):

| Pin | Device |
|-----|--------|
| D4 | Button 1 |
| D8 | Relay |
| D10 | Window servo |
| A0 | Gas sensor |
| A1 | Steam sensor |
| A2 | Photocell |
| A3 | Soil moisture |

## Optional: LED blink test

Before the main firmware, confirm the white LED on D13 works.

1. Arduino IDE: open `firmware/phase0_led_blink/phase0_led_blink.ino`
2. Board: **Arduino UNO**, correct USB port
3. Upload
4. White LED should blink **1 s on / 1 s off**

If this fails, fix the shield, LED plug (G/V/S on D13), or USB cable before uploading `gesture_home.ino`.

## Upload main firmware

`firmware/gesture_home/gesture_home.ino` drives every module in the demo.

1. Open `firmware/gesture_home/gesture_home.ino` in Arduino IDE
2. Install libraries if prompted: **LiquidCrystal_I2C**, **Servo**
3. Board: **Arduino UNO** (Keyestudio PLUS), select USB port
4. Upload

On boot the white LED **blinks twice**, then waits for serial commands.

## Test with Serial Monitor

1. Arduino IDE -> Tools -> Serial Monitor
2. Baud: **9600**, newline ending
3. Try these commands:

| Command | Effect |
|---------|--------|
| `LIGHTS_ON` | White LED on |
| `LIGHTS_OFF` | White LED off |
| `HOLD_ON` / `HOLD_OFF` | Blink LED while Python hold timer runs |
| `FAN_SPEED_1` / `2` / `3` | Fan speed |
| `FAN_STOP` | Fan off |
| `DOOR_TOGGLE` | Door open/close |
| `SECURITY_ON` / `SECURITY_OFF` | Arm/disarm PIR alarm |
| `STATUS` | Report current state |
| `HELP` | List all commands |

While Python tracks a lights hold (`HOLD_ON`), the LED blinks like the blink test sketch. After 3 seconds it turns solid on or off.

## Connect to Python

After Serial Monitor tests pass:

```bash
conda activate home
python home_controller.py --port /dev/ttyUSB0
```

**Close Serial Monitor first.** Only one program can use USB serial at a time.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| LED never lights | Run blink test on D13; check G/V/S wiring |
| LCD blank | Check I2C address `0x27`; SDA/SCL on A4/A5 |
| Fan wrong speed | Confirm INA on D7, INB on D6 (not D11) |
| Upload fails | Board = Arduino UNO; try another USB cable |
| Serial works, Python fails | Close Serial Monitor; `ls /dev/ttyUSB*` |
| Permission denied | `sudo chmod a+rw /dev/ttyUSB0` |

See also **`docs/MANUAL.md`** for gestures, keyboard keys, and full troubleshooting.
