"""
GestureHome booth bridge: FastAPI + full serial command set for upgrade/booth.

Serves upgrade/web/booth.html (HandConnect visuals + cheat sheet).
Does not modify home_controller.py or firmware on main.
"""

import argparse
import os
import re
import socket
import sys
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    import serial
    from serial import SerialException
    from serial.tools import list_ports
except ImportError:
    serial = None
    SerialException = OSError
    list_ports = None

UPGRADE_DIR = Path(__file__).resolve().parent
ROOT = UPGRADE_DIR.parent
WEB_DIR = UPGRADE_DIR / "web"

VALID_COMMANDS = frozenset(
    {
        "LIGHTS_ON",
        "LIGHTS_OFF",
        "HOLD_ON",
        "HOLD_OFF",
        "FAN_SPEED_1",
        "FAN_SPEED_2",
        "FAN_SPEED_3",
        "FAN_STOP",
        "DOOR_OPEN",
        "DOOR_CLOSE",
        "DOOR_TOGGLE",
        "SECURITY_ON",
        "SECURITY_OFF",
        "STATUS",
        "HELP",
    }
)

STATUS_RE = re.compile(
    r"lights=(?P<lights>ON|OFF)"
    r".*fan=(?P<fan>\d+)"
    r".*door=(?P<door>OPEN|CLOSE)"
    r"(?:.*security=(?P<security>ON|OFF))?"
    r"(?:.*alarm=(?P<alarm>ON|OFF))?"
)

app = FastAPI(
    title="GestureHome Booth Bridge",
    description="Event booth: browser gestures → serial → Keyestudio house.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_serial: Optional["serial.Serial"] = None
_last_cmd: Optional[str] = None
_last_cmd_at: float = 0.0
_last_status: dict[str, Any] = {}


class CommandBody(BaseModel):
    cmd: str = Field(..., examples=["LIGHTS_ON"])


class HealthResponse(BaseModel):
    ok: bool
    serial_connected: bool
    port: Optional[str] = None
    last_command: Optional[str] = None
    last_command_at: float = 0.0


class CommandResponse(BaseModel):
    ok: bool
    cmd: Optional[str] = None
    response: Optional[str] = None
    error: Optional[str] = None


def open_serial(port: str, baud: int = 9600) -> None:
    global _serial
    if serial is None:
        raise RuntimeError("pyserial not installed. pip install pyserial")
    _serial = serial.Serial(port, baud, timeout=0.15)
    time.sleep(2.0)
    _serial.reset_input_buffer()


def read_serial_lines(max_lines: int = 8) -> list[str]:
    if _serial is None or not _serial.is_open:
        return []
    lines: list[str] = []
    deadline = time.time() + 0.35
    while time.time() < deadline and len(lines) < max_lines:
        raw = _serial.readline()
        if not raw:
            time.sleep(0.02)
            continue
        text = raw.decode("utf-8", errors="replace").strip()
        if text:
            lines.append(text)
    return lines


def transact(cmd: str) -> list[str]:
    global _last_cmd, _last_cmd_at
    if _serial is None or not _serial.is_open:
        raise RuntimeError("Serial port not open")
    line = (cmd.strip().upper() + "\n").encode("ascii")
    _serial.write(line)
    _serial.flush()
    _last_cmd = cmd.strip().upper()
    _last_cmd_at = time.time()
    return read_serial_lines()


def send_command(cmd: str) -> list[str]:
    cmd = cmd.strip().upper()
    if cmd not in VALID_COMMANDS:
        raise ValueError(f"Invalid command: {cmd}")
    return transact(cmd)


def parse_status_line(line: str) -> Optional[dict[str, Any]]:
    if "OK STATUS" not in line:
        return None
    m = STATUS_RE.search(line)
    if not m:
        return {"raw": line}
    return {
        "lights": m.group("lights"),
        "fan": int(m.group("fan")),
        "door": m.group("door"),
        "security": m.group("security") or "OFF",
        "alarm": m.group("alarm") or "OFF",
        "raw": line,
    }


def poll_house_status() -> dict[str, Any]:
    global _last_status
    if _serial is None or not _serial.is_open:
        return {"connected": False, "status": _last_status}
    lines = transact("STATUS")
    for line in lines:
        parsed = parse_status_line(line)
        if parsed:
            _last_status = parsed
            break
    return {"connected": True, "status": _last_status, "lines": lines}


@app.get("/")
def root_redirect():
    return FileResponse(WEB_DIR / "host.html")


def get_lan_ip() -> str:
    """Best-effort LAN IP for phone QR codes (not 127.0.0.1)."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return "127.0.0.1"


@app.get("/host.html")
def host_page():
    return FileResponse(WEB_DIR / "host.html")


@app.get("/booth-info")
def booth_info(request: Request):
    """LAN URLs for projector QR and phone join (event Wi-Fi)."""
    connected = _serial is not None and _serial.is_open
    lan_ip = get_lan_ip()
    port = request.url.port or 8090
    scheme = request.url.scheme or "http"
    base = f"{scheme}://{lan_ip}:{port}"
    return {
        "lan_ip": lan_ip,
        "http_port": port,
        "host_url": f"{base}/host.html",
        "booth_url": f"{base}/booth.html",
        "phone_url": f"{base}/booth.html",
        "serial_connected": connected,
        "port": _serial.port if connected else None,
    }


@app.get("/booth.html")
def booth_page():
    return FileResponse(WEB_DIR / "booth.html")


app.mount("/web", StaticFiles(directory=WEB_DIR), name="web")


@app.get("/health", response_model=HealthResponse)
def health():
    connected = _serial is not None and _serial.is_open
    return HealthResponse(
        ok=True,
        serial_connected=connected,
        port=_serial.port if connected else None,
        last_command=_last_cmd,
        last_command_at=_last_cmd_at,
    )


@app.get("/house-status")
def house_status():
    try:
        return poll_house_status()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/command", response_model=CommandResponse)
def command(body: CommandBody):
    cmd = body.cmd.strip().upper()
    if cmd not in VALID_COMMANDS:
        raise HTTPException(status_code=400, detail=f"Invalid command: {cmd}")
    try:
        lines = send_command(cmd)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    response = lines[-1] if lines else None
    if cmd == "STATUS" or any("OK STATUS" in x for x in lines):
        for line in lines:
            parsed = parse_status_line(line)
            if parsed:
                _last_status.update(parsed)
                break
    return CommandResponse(ok=True, cmd=cmd, response=response)


def pick_usb_port(explicit: str) -> Optional[str]:
    if explicit:
        return explicit
    if list_ports is None:
        return None
    for prefix in ("/dev/ttyUSB", "/dev/ttyACM", "/dev/tty.usb", "/dev/cu.usb"):
        for p in list_ports.comports():
            if p.device.startswith(prefix):
                return p.device
    for p in list_ports.comports():
        if "/dev/ttyS" not in p.device:
            return p.device
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="GestureHome booth bridge")
    parser.add_argument("--port", default=os.environ.get("GESTURE_HOME_PORT", ""))
    parser.add_argument("--host", default=os.environ.get("BOOTH_BIND_HOST", "0.0.0.0"))
    parser.add_argument("--port-http", type=int, default=8090, dest="http_port")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--no-serial", action="store_true")
    parser.add_argument("--ssl-keyfile", default=os.environ.get("BOOTH_SSL_KEY", ""))
    parser.add_argument("--ssl-certfile", default=os.environ.get("BOOTH_SSL_CERT", ""))
    args = parser.parse_args()

    scheme = "https" if args.ssl_certfile and args.ssl_keyfile else "http"

    if not args.no_serial:
        port = pick_usb_port(args.port)
        if port and not args.port:
            print(f"Auto-selected serial port: {port}")
        if not port:
            print("No serial port found. Use --no-serial or set GESTURE_HOME_PORT.")
            if list_ports:
                print("Available:", [p.device for p in list_ports.comports()] or "none")
            sys.exit(1)
        try:
            open_serial(port, args.baud)
            print(f"Serial open: {port} @ {args.baud}")
        except SerialException as exc:
            print(f"Failed to open {port}: {exc}")
            sys.exit(1)
    else:
        print("Running without serial (--no-serial).")

    lan = get_lan_ip()
    print(f"Projector: {scheme}://{lan}:{args.http_port}/host.html")
    print(f"Phone QR:  {scheme}://{lan}:{args.http_port}/booth.html")
    if scheme == "https":
        print("iPhone: accept the certificate warning once, then Start camera works.")

    import uvicorn

    uvicorn.run(
        app,
        host=args.host,
        port=args.http_port,
        log_level="info",
        ssl_keyfile=args.ssl_keyfile or None,
        ssl_certfile=args.ssl_certfile or None,
    )


if __name__ == "__main__":
    main()
