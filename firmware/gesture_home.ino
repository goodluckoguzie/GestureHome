/*
 * GestureHome Phase 1 - serial commands → white LED (Keyestudio KS0085 pin 13)
 *
 * Upload to Keyestudio PLUS board. Open Serial Monitor at 9600 to test:
 *   LIGHTS_ON
 *   LIGHTS_OFF
 *
 * This code runs ON the board. It only listens for two words and flips pin 13.
 */

// Pin 13 = white LED on typical Keyestudio KS0085 sensor shield
#define LED_PIN 13

void setup() {
  // setup() runs once when board powers on or after USB upload
  Serial.begin(9600);           // Start listening on USB at 9600 baud (match bridge.py)
  pinMode(LED_PIN, OUTPUT);       // Pin 13 is an output (sends power to LED)
  digitalWrite(LED_PIN, LOW);   // Start with LED OFF
}

void applyCommand(const String &cmd) {
  // Decide what to do based on the text line we received
  if (cmd == "LIGHTS_ON") {
    digitalWrite(LED_PIN, HIGH);  // Turn LED ON (electricity flows)
    Serial.println("OK LIGHTS_ON"); // Reply back to laptop (optional debug)
  } else if (cmd == "LIGHTS_OFF") {
    digitalWrite(LED_PIN, LOW);   // Turn LED OFF
    Serial.println("OK LIGHTS_OFF");
  } else if (cmd.length() > 0) {
  // Unknown command - not empty, but not one of our two words
    Serial.println("ERR unknown:" + cmd);
  }
}

void loop() {
  // loop() runs forever, thousands of times per second
  if (Serial.available()) {
    // A message arrived from the laptop over USB
    String line = Serial.readStringUntil('\n');  // Read until newline character
    line.trim();                                 // Remove spaces / carriage returns
    applyCommand(line);                          // LIGHTS_ON or LIGHTS_OFF
  }
}
