/*
 * KS0085 Phase 0 - LED blink (Keyestudio Project 1)
 *
 * Use this BEFORE gesture_home.ino to verify:
 *   - USB cable works
 *   - Sensor shield stacked correctly
 *   - White LED wired to D13 (G, V, S → G, V, 13)
 *
 * Expected: white LED blinks on 1 second, off 1 second, forever.
 * No serial commands needed.
 */

#define LED_PIN 13

void setup() {
  pinMode(LED_PIN, OUTPUT);
}

void loop() {
  digitalWrite(LED_PIN, HIGH);
  delay(1000);
  digitalWrite(LED_PIN, LOW);
  delay(1000);
}
