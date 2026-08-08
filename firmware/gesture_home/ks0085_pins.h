/*
 * KS0085 Keyestudio Smart Home Kit - pin map (sensor shield)
 *
 * White LED module: G, V, S -> shield G, V, D13 (house slot 1)
 * Yellow LED module: G, V, S -> shield G, V, D5 (slot 12)
 * PIR module: G, V, S -> shield G, V, D2
 * Fan module: GND/VCC/INA/INB -> G/V/D7/D6 (slot 15)
 * LCD1602 I2C: GND/VCC/SDA/SCL -> GND/5V/SDA/SCL (slot 2)
 * Buzzer module: G, V, S -> shield G, V, D3
 *
 * https://docs.keyestudio.com/projects/KS0085/
 */

#ifndef KS0085_PINS_H
#define KS0085_PINS_H

// White LED (house slot 1)
#define PIN_WHITE_LED 13
#define PIN_YELLOW_LED 5

// Fan driver (house slot 15)
#define PIN_FAN_INA 7
#define PIN_FAN_INB 6

// Door, sensors, and optional modules
#define PIN_BUTTON_1 4
#define PIN_BUTTON_2 2
#define PIN_DOOR_SERVO 9
#define PIN_WINDOW_SERVO 10
#define PIN_RELAY 8
#define PIN_BUZZER 3
#define PIN_PIR 2
#define PIN_GAS A0
#define PIN_STEAM A1
#define PIN_PHOTOCELL A2
#define PIN_SOIL A3

#endif
