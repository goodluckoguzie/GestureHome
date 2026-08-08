/*
 * GestureHome: LED + fan + door servo + LCD + buzzer cues (D3)
 *
 * Serial (9600):
 *   LIGHTS_ON / LIGHTS_OFF / HOLD_ON / HOLD_OFF
 *   FAN_SPEED_1 / FAN_SPEED_2 / FAN_SPEED_3 / FAN_STOP
 *   DOOR_OPEN / DOOR_CLOSE / DOOR_TOGGLE
 *   STATUS / HELP
 */

#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Servo.h>
#include "ks0085_pins.h"

const unsigned long SERIAL_BAUD = 9600;
const int BOOT_BLINK_MS = 200;
const unsigned long HOLD_BLINK_MS = 250;
const unsigned long FAN_CYCLE_MS = 50;
const unsigned long ALARM_BLINK_MS = 200;
const unsigned long ALARM_TONE_MS = 350;
const int DOOR_ANGLE_CLOSED = 20;
const int DOOR_ANGLE_OPEN = 90;
const uint8_t LCD_I2C_ADDR = 0x27;

LiquidCrystal_I2C lcd(LCD_I2C_ADDR, 16, 2);
Servo doorServo;

bool lightsOn = false;
bool holdBlink = false;
bool blinkPhase = false;
unsigned long lastBlinkMs = 0;

uint8_t fanSpeed = 0;
unsigned long fanPwmMs = 0;

bool doorOpen = false;

bool securityArmed = false;
bool alarmActive = false;
bool alarmBlinkPhase = false;
unsigned long alarmBlinkMs = 0;
unsigned long alarmToneMs = 0;

void playTone(unsigned int freq, unsigned int durationMs) {
  if (freq == 0 || durationMs == 0) {
    return;
  }
  tone(PIN_BUZZER, freq, durationMs);
  delay(durationMs + 8);
  noTone(PIN_BUZZER);
}

void soundLightOn() {
  playTone(523, 70);
  playTone(784, 70);
  playTone(1047, 110);
}

void soundLightOff() {
  playTone(880, 70);
  playTone(587, 70);
  playTone(392, 130);
}

void soundDoorOpen() {
  playTone(350, 90);
  playTone(500, 90);
  playTone(700, 90);
  playTone(900, 140);
}

void soundDoorClose() {
  playTone(800, 80);
  playTone(550, 80);
  playTone(400, 80);
  playTone(280, 120);
}

void soundFanSpeed(uint8_t speed) {
  if (speed == 0) {
    playTone(250, 160);
    return;
  }
  for (uint8_t i = 1; i <= speed; i++) {
    playTone(400 + (i * 180), 90);
  }
}

void clearLcdLine(uint8_t row) {
  lcd.setCursor(0, row);
  lcd.print("                ");
}

void updateLcd() {
  clearLcdLine(0);
  lcd.setCursor(0, 0);
  lcd.print("Light:");
  lcd.print(lightsOn ? "ON" : "OFF");
  if (securityArmed) {
    lcd.print(alarmActive ? " ALARM!" : " SEC:ON");
  }

  clearLcdLine(1);
  lcd.setCursor(0, 1);
  lcd.print("Door:");
  lcd.print(doorOpen ? "OPEN" : "CLOSE");
  lcd.print(" Fan:");
  if (fanSpeed == 0) {
    lcd.print("OFF");
  } else {
    lcd.print(fanSpeed);
  }
}

void soundSecurityArm() {
  playTone(660, 90);
  playTone(990, 120);
}

void soundSecurityDisarm() {
  playTone(990, 90);
  playTone(660, 120);
}

void setSecurityArmed(bool armed) {
  if (securityArmed == armed) {
    return;
  }
  securityArmed = armed;
  alarmActive = false;
  digitalWrite(PIN_YELLOW_LED, LOW);
  noTone(PIN_BUZZER);
  updateLcd();
  if (armed) {
    soundSecurityArm();
  } else {
    soundSecurityDisarm();
  }
}

void updateSecurityAlarm() {
  if (!securityArmed) {
    return;
  }

  if (digitalRead(PIN_PIR) == HIGH) {
    alarmActive = true;
  }

  if (!alarmActive) {
    digitalWrite(PIN_YELLOW_LED, LOW);
    return;
  }

  if (millis() - alarmBlinkMs >= ALARM_BLINK_MS) {
    alarmBlinkMs = millis();
    alarmBlinkPhase = !alarmBlinkPhase;
    digitalWrite(PIN_YELLOW_LED, alarmBlinkPhase ? HIGH : LOW);
    updateLcd();
  }

  if (millis() - alarmToneMs >= ALARM_TONE_MS) {
    alarmToneMs = millis();
    tone(PIN_BUZZER, alarmBlinkPhase ? 920 : 620, 200);
  }
}

void initLcd() {
  lcd.init();
  lcd.backlight();
  updateLcd();
}

void applyLedOutput() {
  if (holdBlink) {
    digitalWrite(PIN_WHITE_LED, blinkPhase ? HIGH : LOW);
  } else {
    digitalWrite(PIN_WHITE_LED, lightsOn ? HIGH : LOW);
  }
}

void setWhiteLed(bool on) {
  if (lightsOn == on) {
    return;
  }
  holdBlink = false;
  lightsOn = on;
  applyLedOutput();
  updateLcd();
  if (on) {
    soundLightOn();
  } else {
    soundLightOff();
  }
}

void startHoldBlink() {
  if (holdBlink) {
    return;
  }
  holdBlink = true;
  blinkPhase = false;
  lastBlinkMs = millis();
  applyLedOutput();
}

void stopHoldBlink() {
  holdBlink = false;
  applyLedOutput();
}

void applyFanPins(bool on) {
  if (on) {
    digitalWrite(PIN_FAN_INA, HIGH);
    digitalWrite(PIN_FAN_INB, LOW);
  } else {
    digitalWrite(PIN_FAN_INA, LOW);
    digitalWrite(PIN_FAN_INB, LOW);
  }
}

void setFanSpeed(uint8_t speed) {
  if (speed > 3) {
    speed = 3;
  }
  if (fanSpeed == speed) {
    return;
  }
  fanSpeed = speed;
  fanPwmMs = millis();
  if (speed == 0) {
    applyFanPins(false);
  } else if (speed == 3) {
    applyFanPins(true);
  }
  updateLcd();
  soundFanSpeed(speed);
}

void updateFanPwm() {
  if (fanSpeed == 0) {
    applyFanPins(false);
    return;
  }
  if (fanSpeed == 3) {
    applyFanPins(true);
    return;
  }

  unsigned long phase = millis() - fanPwmMs;
  if (phase >= FAN_CYCLE_MS) {
    fanPwmMs = millis();
    phase = 0;
  }

  unsigned long onMs = (fanSpeed == 1) ? 17 : 34;
  applyFanPins(phase < onMs);
}

void setDoor(bool open) {
  if (doorOpen == open) {
    return;
  }
  doorOpen = open;
  doorServo.write(open ? DOOR_ANGLE_OPEN : DOOR_ANGLE_CLOSED);
  updateLcd();
  if (open) {
    soundDoorOpen();
  } else {
    soundDoorClose();
  }
}

void toggleDoor() {
  setDoor(!doorOpen);
}

void bootBlink() {
  for (int i = 0; i < 2; i++) {
    digitalWrite(PIN_WHITE_LED, HIGH);
    delay(BOOT_BLINK_MS);
    digitalWrite(PIN_WHITE_LED, LOW);
    delay(BOOT_BLINK_MS);
  }
}

void printHelp() {
  Serial.println("Commands:");
  Serial.println("  LIGHTS_ON / LED_ON");
  Serial.println("  LIGHTS_OFF / LED_OFF");
  Serial.println("  HOLD_ON / HOLD_OFF");
  Serial.println("  FAN_SPEED_1 / FAN_SPEED_2 / FAN_SPEED_3");
  Serial.println("  FAN_STOP");
  Serial.println("  DOOR_OPEN / DOOR_CLOSE / DOOR_TOGGLE");
  Serial.println("  SECURITY_ON / SECURITY_OFF");
  Serial.println("  STATUS");
  Serial.println("  HELP");
}

void applyCommand(const String &cmd) {
  if (cmd == "LIGHTS_ON" || cmd == "LED_ON") {
    setWhiteLed(true);
    Serial.println("OK LIGHTS_ON");
  } else if (cmd == "LIGHTS_OFF" || cmd == "LED_OFF") {
    setWhiteLed(false);
    Serial.println("OK LIGHTS_OFF");
  } else if (cmd == "HOLD_ON") {
    startHoldBlink();
    Serial.println("OK HOLD_ON");
  } else if (cmd == "HOLD_OFF") {
    stopHoldBlink();
    Serial.println("OK HOLD_OFF");
  } else if (cmd == "FAN_SPEED_1") {
    setFanSpeed(1);
    Serial.println("OK FAN_SPEED_1");
  } else if (cmd == "FAN_SPEED_2") {
    setFanSpeed(2);
    Serial.println("OK FAN_SPEED_2");
  } else if (cmd == "FAN_SPEED_3") {
    setFanSpeed(3);
    Serial.println("OK FAN_SPEED_3");
  } else if (cmd == "FAN_STOP") {
    setFanSpeed(0);
    Serial.println("OK FAN_STOP");
  } else if (cmd == "DOOR_OPEN") {
    setDoor(true);
    Serial.println("OK DOOR_OPEN");
  } else if (cmd == "DOOR_CLOSE") {
    setDoor(false);
    Serial.println("OK DOOR_CLOSE");
  } else if (cmd == "DOOR_TOGGLE") {
    toggleDoor();
    Serial.print("OK DOOR_");
    Serial.println(doorOpen ? "OPEN" : "CLOSE");
  } else if (cmd == "SECURITY_ON") {
    setSecurityArmed(true);
    Serial.println("OK SECURITY_ON");
  } else if (cmd == "SECURITY_OFF") {
    setSecurityArmed(false);
    Serial.println("OK SECURITY_OFF");
  } else if (cmd == "STATUS") {
    Serial.print("OK STATUS lights=");
    Serial.print(lightsOn ? "ON" : "OFF");
    Serial.print(" hold=");
    Serial.print(holdBlink ? "BLINK" : "OFF");
    Serial.print(" fan=");
    Serial.print(fanSpeed);
    Serial.print(" door=");
    Serial.print(doorOpen ? "OPEN" : "CLOSE");
    Serial.print(" security=");
    Serial.print(securityArmed ? "ON" : "OFF");
    Serial.print(" alarm=");
    Serial.println(alarmActive ? "ON" : "OFF");
  } else if (cmd == "HELP") {
    printHelp();
  } else if (cmd.length() > 0) {
    Serial.println("ERR unknown:" + cmd);
  }
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  pinMode(PIN_WHITE_LED, OUTPUT);
  pinMode(PIN_FAN_INA, OUTPUT);
  pinMode(PIN_FAN_INB, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_YELLOW_LED, OUTPUT);
  pinMode(PIN_PIR, INPUT);
  doorServo.attach(PIN_DOOR_SERVO);
  lightsOn = false;
  holdBlink = false;
  fanSpeed = 0;
  doorOpen = false;
  securityArmed = false;
  alarmActive = false;
  digitalWrite(PIN_YELLOW_LED, LOW);
  applyLedOutput();
  applyFanPins(false);
  doorServo.write(DOOR_ANGLE_CLOSED);
  initLcd();
  bootBlink();
  Serial.println("OK READY GestureHome LED fan door LCD PIR D2 buzzer D3");
  printHelp();
}

void loop() {
  if (holdBlink && millis() - lastBlinkMs >= HOLD_BLINK_MS) {
    lastBlinkMs = millis();
    blinkPhase = !blinkPhase;
    applyLedOutput();
  }

  updateFanPwm();
  updateSecurityAlarm();

  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    applyCommand(line);
  }
}
