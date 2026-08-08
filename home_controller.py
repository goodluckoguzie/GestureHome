#!/usr/bin/env python3
"""
GestureHome Phase 1 - Python + Arduino only.

Webcam + MediaPipe hand tracking → USB serial → Keyestudio LED (pin 13).

Run:
  conda activate home
  python home_controller.py

Keys: o = lights on, f = lights off, q = quit
Gestures: both hands up → LIGHTS_ON, both hands down → LIGHTS_OFF
"""

import argparse
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional

import cv2
import mediapipe as mp
import serial
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import HandLandmarksConnections
from mediapipe.tasks import python as mp_tasks
from serial import SerialException
from serial.tools import list_ports

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "models"
MODEL_PATH = MODEL_DIR / "hand_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)

# --- Rules (same as the old web/gestures.js) ---
COOLDOWN_S = 1.5
STABLE_FRAMES = 4
HANDS_UP_Y = 0.42
HANDS_DOWN_Y = 0.58
VALID_COMMANDS = frozenset({"LIGHTS_ON", "LIGHTS_OFF"})
HAND_CONNECTIONS = HandLandmarksConnections.HAND_CONNECTIONS
SKELETON_COLOR = (61, 214, 195)


def ensure_model() -> Path:
    if MODEL_PATH.is_file():
        return MODEL_PATH
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading hand model to {MODEL_PATH} …")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    return MODEL_PATH


def create_landmarker() -> vision.HandLandmarker:
    model_path = ensure_model()
    options = vision.HandLandmarkerOptions(
        base_options=mp_tasks.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.6,
        min_tracking_confidence=0.6,
    )
    return vision.HandLandmarker.create_from_options(options)


def list_serial_ports() -> list[str]:
    return [p.device for p in list_ports.comports()]


def pick_usb_port(explicit: str) -> Optional[str]:
    """Prefer Keyestudio-style USB ports over virtual ttyS* on Linux."""
    if explicit:
        return explicit
    ports = list_ports.comports()
    for prefix in ("/dev/ttyUSB", "/dev/ttyACM", "/dev/tty.usb", "/dev/cu.usb"):
        for p in ports:
            if p.device.startswith(prefix):
                return p.device
    # Fallback: any port that isn't a legacy ttyS virtual serial
    for p in ports:
        if "/dev/ttyS" not in p.device:
            return p.device
    return None


def open_serial(port: str, baud: int = 9600) -> serial.Serial:
    ser = serial.Serial(port, baud, timeout=0.1)
    time.sleep(2.0)
    ser.reset_input_buffer()
    return ser


def send_command(ser: Optional[serial.Serial], cmd: str) -> bool:
    if ser is None or not ser.is_open:
        print(f"[serial] skipped (not connected): {cmd}")
        return False
    line = (cmd.strip().upper() + "\n").encode("ascii")
    ser.write(line)
    ser.flush()
    print(f"[serial] sent {cmd.strip().upper()}")
    return True


def average_wrist_y(hand_landmarks_list) -> Optional[float]:
    if not hand_landmarks_list:
        return None
    total = sum(hand[0].y for hand in hand_landmarks_list)
    return total / len(hand_landmarks_list)


def draw_hand_skeleton(frame, landmarks) -> None:
    h, w = frame.shape[:2]
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
    for conn in HAND_CONNECTIONS:
        cv2.line(frame, pts[conn.start], pts[conn.end], SKELETON_COLOR, 2, cv2.LINE_AA)
    for x, y in pts:
        cv2.circle(frame, (x, y), 3, SKELETON_COLOR, -1, cv2.LINE_AA)


def draw_status(frame, lines: list[str]) -> None:
    y = 28
    for line in lines:
        cv2.putText(
            frame,
            line,
            (12, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            SKELETON_COLOR,
            2,
            cv2.LINE_AA,
        )
        y += 26


def run_self_test(camera_index: int) -> None:
    """Headless smoke test: camera + model + 30 frames."""
    landmarker = create_landmarker()
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"FAIL: cannot open camera index {camera_index}")
        sys.exit(1)

    max_hands = 0
    start_ms = int(time.time() * 1000)
    for i in range(30):
        ok, frame = cap.read()
        if not ok:
            print(f"FAIL: frame {i} read failed")
            sys.exit(1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect_for_video(mp_image, start_ms + i * 33)
        max_hands = max(max_hands, len(result.hand_landmarks or []))

    cap.release()
    landmarker.close()
    print(f"PASS: self-test 30 frames, max_hands_seen={max_hands}")
    print(f"opencv={cv2.__version__} mediapipe={mp.__version__}")
    print(f"model={MODEL_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="GestureHome Phase 1 (Python + Arduino)")
    parser.add_argument(
        "--port",
        default=os.environ.get("GESTURE_HOME_PORT", ""),
        help="Serial device (e.g. /dev/ttyUSB0). Auto-pick first USB if omitted.",
    )
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--camera", type=int, default=0, help="Webcam index (usually 0)")
    parser.add_argument("--no-serial", action="store_true", help="Camera + skeleton only (no Arduino)")
    parser.add_argument("--no-mirror", action="store_true", help="Disable mirrored preview")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run headless smoke test (camera + model) and exit",
    )
    args = parser.parse_args()

    if args.self_test:
        run_self_test(args.camera)
        return

    ser: Optional[serial.Serial] = None
    if not args.no_serial:
        port = pick_usb_port(args.port)
        if port and not args.port:
            print(f"Auto-selected serial port: {port}")
        if not port:
            print("No USB serial port found. Plug in Keyestudio or use --no-serial.")
            print("Available:", list_serial_ports() or "none")
            sys.exit(1)
        try:
            ser = open_serial(port, args.baud)
            print(f"Serial open: {port} @ {args.baud}")
        except SerialException as exc:
            print(f"Failed to open {port}: {exc}")
            sys.exit(1)
    else:
        print("Running without serial (--no-serial).")

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"Could not open camera index {args.camera}")
        sys.exit(1)

    landmarker = create_landmarker()

    lights_on = False
    last_command_at = 0.0
    stable_up = 0
    stable_down = 0
    status_msg = "Raise both hands to turn lights on"
    window = "GestureHome Phase 1 (q=quit, o=on, f=off)"
    frame_start_ms = int(time.time() * 1000)
    frame_idx = 0

    print(window)
    print("Gestures: both hands UP → on, both hands DOWN → off")

    while True:
        ok, frame = cap.read()
        if not ok:
            print("Camera frame failed")
            break

        if not args.no_mirror:
            frame = cv2.flip(frame, 1)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = frame_start_ms + frame_idx * 33
        frame_idx += 1
        result = landmarker.detect_for_video(mp_image, timestamp_ms)

        hand_list = result.hand_landmarks or []
        for hand_lm in hand_list:
            draw_hand_skeleton(frame, hand_lm)

        now = time.time()
        cooled_down = (now - last_command_at) >= COOLDOWN_S

        if len(hand_list) < 2:
            stable_up = 0
            stable_down = 0
            status_msg = "Show both hands"
        else:
            avg_y = average_wrist_y(hand_list)
            if avg_y is not None and avg_y < HANDS_UP_Y:
                stable_down = 0
                stable_up += 1
                status_msg = (
                    "Lights on!"
                    if stable_up >= STABLE_FRAMES and cooled_down
                    else f"Hands up ({stable_up}/{STABLE_FRAMES})"
                )
                if stable_up >= STABLE_FRAMES and cooled_down and not lights_on:
                    if send_command(ser, "LIGHTS_ON"):
                        lights_on = True
                        last_command_at = now
                        stable_up = 0
            elif avg_y is not None and avg_y > HANDS_DOWN_Y:
                stable_up = 0
                stable_down += 1
                status_msg = (
                    "Lights off!"
                    if stable_down >= STABLE_FRAMES and cooled_down
                    else f"Hands down ({stable_down}/{STABLE_FRAMES})"
                )
                if stable_down >= STABLE_FRAMES and cooled_down and lights_on:
                    if send_command(ser, "LIGHTS_OFF"):
                        lights_on = False
                        last_command_at = now
                        stable_down = 0
            else:
                stable_up = 0
                stable_down = 0
                status_msg = "Neutral - raise or lower both hands"

        led_label = "LED: ON" if lights_on else "LED: OFF"
        serial_label = "USB: OK" if ser and ser.is_open else "USB: --"
        draw_status(frame, [status_msg, led_label, serial_label, "o=on  f=off  q=quit"])

        cv2.imshow(window, frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("o") and cooled_down:
            if send_command(ser, "LIGHTS_ON"):
                lights_on = True
                last_command_at = time.time()
        if key == ord("f") and cooled_down:
            if send_command(ser, "LIGHTS_OFF"):
                lights_on = False
                last_command_at = time.time()

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()
    if ser and ser.is_open:
        ser.close()
    print("Done.")


if __name__ == "__main__":
    main()
