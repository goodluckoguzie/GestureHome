#!/usr/bin/env python3
"""
GestureHome: Python + Arduino.

Webcam + MediaPipe → USB serial → Keyestudio LED (D13) + fan (D7/D6).

Run:
  conda activate home
  python home_controller.py

Keys: o/f = lights, 1/2/3 = fan speed, 0 = fan stop, d = door toggle, q = quit
Gestures (two hands):
  two closed fists 2s → door open/close (toggle)
Gestures (one hand):
  fist 3s → lights ON | open palm 3s → lights OFF
  1/2/3 fingers held 2s → fan speed 1/2/3 | thumbs up 2s → fan STOP
  wave 2s OR two open palms (10 fingers) 2s → security ON/OFF (PIR alarm)
"""

import argparse
import math
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

# --- Gesture rules ---
HOLD_S = 3.0          # Hold pose this many seconds for lights
FAN_HOLD_S = 2.0      # Hold pose for fan speed / stop
DOOR_HOLD_S = 2.0     # Hold two closed fists for door toggle
SEC_HOLD_S = 2.0      # Wave or 10 fingers to arm/disarm security
COOLDOWN_S = 0.5      # Brief gap after a command before next trigger
WAVE_WINDOW = 24
WAVE_MIN_AMP = 0.07
WAVE_MIN_SWINGS = 3
VALID_COMMANDS = frozenset({"LIGHTS_ON", "LIGHTS_OFF", "HOLD_ON", "HOLD_OFF"})
HAND_CONNECTIONS = HandLandmarksConnections.HAND_CONNECTIONS
SKELETON_COLOR = (61, 214, 195)

# MediaPipe hand landmark indices
LM_WRIST = 0
LM_THUMB_TIP = 4
LM_INDEX_MCP = 5
LM_INDEX_TIP = 8
LM_MIDDLE_MCP = 9
LM_MIDDLE_TIP = 12
LM_RING_MCP = 13
LM_RING_TIP = 16
LM_PINKY_MCP = 17
LM_PINKY_TIP = 20
FINGER_TIP_MCP_PAIRS = [
    (LM_INDEX_TIP, LM_INDEX_MCP),
    (LM_MIDDLE_TIP, LM_MIDDLE_MCP),
    (LM_RING_TIP, LM_RING_MCP),
    (LM_PINKY_TIP, LM_PINKY_MCP),
]


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


def send_command(
    ser: Optional[serial.Serial],
    cmd: str,
    *,
    simulate_ok: bool = False,
) -> bool:
    """Send to serial, or update UI-only when simulate_ok (--no-serial preview)."""
    cmd = cmd.strip().upper()
    if ser is None or not ser.is_open:
        if simulate_ok:
            print(f"[preview] {cmd} (no USB, on-screen LED only)")
            return True
        print(f"[serial] skipped (not connected): {cmd}")
        return False
    line = (cmd + "\n").encode("ascii")
    ser.write(line)
    ser.flush()
    print(f"[serial] sent {cmd}")
    return True


def landmark_dist(a, b) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def is_fist(landmarks) -> bool:
    """Four fingers curled toward wrist (closed hand)."""
    wrist = landmarks[LM_WRIST]
    curled = 0
    for tip_i, mcp_i in FINGER_TIP_MCP_PAIRS:
        if landmark_dist(landmarks[tip_i], wrist) < landmark_dist(landmarks[mcp_i], wrist):
            curled += 1
    return curled >= 4


def is_open_palm(landmarks) -> bool:
    """Fingers and thumb extended (open palm facing camera)."""
    wrist = landmarks[LM_WRIST]
    extended = 0
    for tip_i, mcp_i in FINGER_TIP_MCP_PAIRS:
        if landmark_dist(landmarks[tip_i], wrist) > landmark_dist(landmarks[mcp_i], wrist) * 1.02:
            extended += 1
    thumb_open = landmark_dist(landmarks[LM_THUMB_TIP], wrist) > landmark_dist(
        landmarks[LM_INDEX_MCP], wrist
    ) * 0.85
    return extended >= 4 and thumb_open


def count_extended_fingers(landmarks) -> int:
    """Count extended index/middle/ring/pinky (thumb excluded)."""
    wrist = landmarks[LM_WRIST]
    count = 0
    for tip_i, mcp_i in FINGER_TIP_MCP_PAIRS:
        if landmark_dist(landmarks[tip_i], wrist) > landmark_dist(landmarks[mcp_i], wrist) * 1.02:
            count += 1
    return count


def is_thumbs_up(landmarks) -> bool:
    """Thumb pointing up, other fingers curled."""
    wrist = landmarks[LM_WRIST]
    thumb_tip = landmarks[LM_THUMB_TIP]
    index_mcp = landmarks[LM_INDEX_MCP]
    if thumb_tip.y >= wrist.y - 0.04:
        return False
    if thumb_tip.y >= index_mcp.y - 0.02:
        return False
    curled = 0
    for tip_i, mcp_i in FINGER_TIP_MCP_PAIRS:
        if landmark_dist(landmarks[tip_i], wrist) < landmark_dist(landmarks[mcp_i], wrist):
            curled += 1
    return curled >= 3


def is_ten_fingers(hand_list) -> bool:
    """Both hands open: 10 fingers (5 per hand)."""
    if len(hand_list) < 2:
        return False
    return is_open_palm(hand_list[0]) and is_open_palm(hand_list[1])


def update_wave_history(landmarks, history: list) -> None:
    history.append(landmarks[LM_WRIST].x)
    if len(history) > WAVE_WINDOW:
        history.pop(0)


def is_waving(history: list) -> bool:
    if len(history) < WAVE_WINDOW:
        return False
    min_x = min(history)
    max_x = max(history)
    if max_x - min_x < WAVE_MIN_AMP:
        return False
    swings = 0
    for i in range(2, len(history)):
        d1 = history[i - 1] - history[i - 2]
        d2 = history[i] - history[i - 1]
        if d1 * d2 < 0 and abs(d1) > 0.008 and abs(d2) > 0.008:
            swings += 1
    return swings >= WAVE_MIN_SWINGS


def is_security_gesture(hand_list, wave_history: list) -> bool:
    if is_ten_fingers(hand_list):
        return True
    if len(hand_list) >= 1:
        update_wave_history(hand_list[0], wave_history)
        return is_waving(wave_history)
    return False


def detect_two_hand_pose(hand_list) -> Optional[str]:
    """Two-hand poses (need both hands visible)."""
    if len(hand_list) < 2:
        return None
    if is_fist(hand_list[0]) and is_fist(hand_list[1]):
        return "two_fists"
    return None


def detect_single_hand_pose(landmarks) -> Optional[str]:
    """Return active pose id or None."""
    if is_thumbs_up(landmarks):
        return "thumb_stop"
    fist = is_fist(landmarks)
    palm = is_open_palm(landmarks)
    if fist and not palm:
        return "fist"
    if palm and not fist:
        return "palm"
    finger_count = count_extended_fingers(landmarks)
    if finger_count == 1:
        return "fan1"
    if finger_count == 2:
        return "fan2"
    if finger_count == 3:
        return "fan3"
    return None


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
    parser = argparse.ArgumentParser(description="GestureHome LED + fan control")
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
    fan_speed = 0
    door_open = False
    last_command_at = 0.0
    fist_since: Optional[float] = None
    palm_since: Optional[float] = None
    fan_since: Optional[float] = None
    fan_pose: Optional[str] = None
    door_since: Optional[float] = None
    security_since: Optional[float] = None
    wave_history: list[float] = []
    hold_blink_sent = False
    security_armed = False
    status_msg = "Wave/10 fingers→SEC | 2 fists→door"
    window = "GestureHome (q=quit)"
    frame_start_ms = int(time.time() * 1000)
    frame_idx = 0
    simulate = args.no_serial

    print(window)
    print("Two closed fists 2s → door open/close (toggle)")
    print("Open palm 3s → lights OFF | Closed fist 3s → lights ON")
    print("1/2/3 fingers held 2s → fan speed | Thumbs up 2s → fan STOP")
    print("Wave 2s OR two open palms 2s → security ON/OFF (PIR → alarm)")
    if simulate:
        print("Preview mode: on-screen status only. Omit --no-serial for real hardware.")

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

        if len(hand_list) < 1:
            if hold_blink_sent:
                send_command(ser, "HOLD_OFF", simulate_ok=simulate)
                hold_blink_sent = False
            fist_since = None
            palm_since = None
            fan_since = None
            fan_pose = None
            door_since = None
            security_since = None
            wave_history.clear()
            status_msg = "Show your hand(s) to the camera"
        elif len(hand_list) >= 2 and detect_two_hand_pose(hand_list) == "two_fists":
            fist_since = None
            palm_since = None
            fan_since = None
            fan_pose = None
            security_since = None
            wave_history.clear()
            if hold_blink_sent:
                send_command(ser, "HOLD_OFF", simulate_ok=simulate)
                hold_blink_sent = False
            if door_since is None:
                door_since = now
            held = now - door_since
            next_state = "CLOSE" if door_open else "OPEN"
            status_msg = f"2 fists {held:.1f}s / {DOOR_HOLD_S}s → door {next_state}"
            if held >= DOOR_HOLD_S and cooled_down:
                if send_command(ser, "DOOR_TOGGLE", simulate_ok=simulate):
                    door_open = not door_open
                    last_command_at = now
                    door_since = None
                    status_msg = f"Door {'OPEN' if door_open else 'CLOSE'}!"
        elif is_security_gesture(hand_list, wave_history):
            fist_since = None
            palm_since = None
            fan_since = None
            fan_pose = None
            door_since = None
            if hold_blink_sent:
                send_command(ser, "HOLD_OFF", simulate_ok=simulate)
                hold_blink_sent = False
            if security_since is None:
                security_since = now
            held = now - security_since
            gesture_hint = "10 fingers" if is_ten_fingers(hand_list) else "wave"
            next_state = "OFF" if security_armed else "ON"
            status_msg = f"{gesture_hint} {held:.1f}s / {SEC_HOLD_S}s SEC {next_state}"
            if held >= SEC_HOLD_S and cooled_down:
                cmd = "SECURITY_OFF" if security_armed else "SECURITY_ON"
                if send_command(ser, cmd, simulate_ok=simulate):
                    security_armed = not security_armed
                    last_command_at = now
                    security_since = None
                    wave_history.clear()
                    status_msg = f"Security {'ON' if security_armed else 'OFF'}!"
        else:
            security_since = None
            wave_history.clear()
            lm = hand_list[0]
            door_since = None
            pose = detect_single_hand_pose(lm)

            if pose == "fist":
                palm_since = None
                fan_since = None
                fan_pose = None
                if fist_since is None:
                    fist_since = now
                if not lights_on and not hold_blink_sent:
                    send_command(ser, "HOLD_ON", simulate_ok=simulate)
                    hold_blink_sent = True
                held = now - fist_since
                status_msg = f"Fist {held:.1f}s / {HOLD_S}s blink→ON"
                if held >= HOLD_S and cooled_down and not lights_on:
                    if send_command(ser, "LIGHTS_ON", simulate_ok=simulate):
                        lights_on = True
                        hold_blink_sent = False
                        last_command_at = now
                        fist_since = None
                        status_msg = "Lights ON!"
            elif pose == "palm":
                fist_since = None
                fan_since = None
                fan_pose = None
                if palm_since is None:
                    palm_since = now
                if lights_on and not hold_blink_sent:
                    send_command(ser, "HOLD_ON", simulate_ok=simulate)
                    hold_blink_sent = True
                held = now - palm_since
                status_msg = f"Open palm {held:.1f}s / {HOLD_S}s blink→OFF"
                if held >= HOLD_S and cooled_down and lights_on:
                    if send_command(ser, "LIGHTS_OFF", simulate_ok=simulate):
                        lights_on = False
                        hold_blink_sent = False
                        last_command_at = now
                        palm_since = None
                        status_msg = "Lights OFF!"
            elif pose in ("fan1", "fan2", "fan3", "thumb_stop"):
                fist_since = None
                palm_since = None
                if hold_blink_sent:
                    send_command(ser, "HOLD_OFF", simulate_ok=simulate)
                    hold_blink_sent = False
                if fan_pose != pose:
                    fan_pose = pose
                    fan_since = now
                held = now - (fan_since or now)
                if pose == "thumb_stop":
                    status_msg = f"Thumbs up {held:.1f}s / {FAN_HOLD_S}s → fan STOP"
                    if held >= FAN_HOLD_S and cooled_down and fan_speed != 0:
                        if send_command(ser, "FAN_STOP", simulate_ok=simulate):
                            fan_speed = 0
                            last_command_at = now
                            fan_since = None
                            fan_pose = None
                            status_msg = "Fan STOP!"
                else:
                    target = int(pose[-1])
                    status_msg = f"{target} finger(s) {held:.1f}s / {FAN_HOLD_S}s → speed {target}"
                    if held >= FAN_HOLD_S and cooled_down and fan_speed != target:
                        cmd = f"FAN_SPEED_{target}"
                        if send_command(ser, cmd, simulate_ok=simulate):
                            fan_speed = target
                            last_command_at = now
                            fan_since = None
                            fan_pose = None
                            status_msg = f"Fan speed {target}!"
            else:
                if hold_blink_sent:
                    send_command(ser, "HOLD_OFF", simulate_ok=simulate)
                    hold_blink_sent = False
                fist_since = None
                palm_since = None
                fan_since = None
                fan_pose = None
                status_msg = "2 fists=door | fist/palm=lights | 1/2/3=fan | thumb up=stop"

        sec_label = f"SEC: {'ARM' if security_armed else 'OFF'}"
        door_label = f"Door: {'OPEN' if door_open else 'CLOSE'}"
        hands_label = f"Hands: {len(hand_list)}"
        fan_label = f"Fan: {'OFF' if fan_speed == 0 else f'SPEED {fan_speed}'}"
        led_label = "LED: ON" if lights_on else "LED: OFF"
        serial_label = "USB: OK" if ser and ser.is_open else "USB: --"
        draw_status(
            frame,
            [
                status_msg,
                hands_label,
                led_label,
                fan_label,
                door_label,
                sec_label,
                serial_label,
                "s=sec d=door o/f 1/2/3/0 q",
            ],
        )

        cv2.imshow(window, frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("o") and cooled_down:
            if send_command(ser, "LIGHTS_ON", simulate_ok=simulate):
                lights_on = True
                last_command_at = time.time()
        if key == ord("f") and cooled_down:
            if send_command(ser, "LIGHTS_OFF", simulate_ok=simulate):
                lights_on = False
                last_command_at = time.time()
        if key == ord("1") and cooled_down:
            if send_command(ser, "FAN_SPEED_1", simulate_ok=simulate):
                fan_speed = 1
                last_command_at = time.time()
        if key == ord("2") and cooled_down:
            if send_command(ser, "FAN_SPEED_2", simulate_ok=simulate):
                fan_speed = 2
                last_command_at = time.time()
        if key == ord("3") and cooled_down:
            if send_command(ser, "FAN_SPEED_3", simulate_ok=simulate):
                fan_speed = 3
                last_command_at = time.time()
        if key == ord("0") and cooled_down:
            if send_command(ser, "FAN_STOP", simulate_ok=simulate):
                fan_speed = 0
                last_command_at = time.time()
        if key == ord("d") and cooled_down:
            if send_command(ser, "DOOR_TOGGLE", simulate_ok=simulate):
                door_open = not door_open
                last_command_at = time.time()
        if key == ord("s") and cooled_down:
            cmd = "SECURITY_OFF" if security_armed else "SECURITY_ON"
            if send_command(ser, cmd, simulate_ok=simulate):
                security_armed = not security_armed
                last_command_at = time.time()

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()
    if ser and ser.is_open:
        ser.close()
    print("Done.")


if __name__ == "__main__":
    main()
