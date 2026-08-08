"""
GestureHome bridge - FastAPI HTTP API → USB serial → Keyestudio house.

Phase 1 commands: LIGHTS_ON, LIGHTS_OFF

This file is the "mail carrier" on your laptop:
  Browser sends JSON  →  this script  →  USB serial  →  Arduino LED
"""

import argparse  # Read command-line flags like --port and --no-serial
import os        # Read environment variables (e.g. GESTURE_HOME_PORT)
import sys       # Exit the program if USB is missing
import time      # Sleep after opening USB (Arduino resets)
from pathlib import Path  # Easy file paths to web folder
from typing import Optional  # Type hints for optional values

from fastapi import FastAPI, HTTPException  # Web framework + error responses
from fastapi.middleware.cors import CORSMiddleware  # Let browser talk to API
from fastapi.responses import FileResponse  # Send index.html as a file
from fastapi.staticfiles import StaticFiles  # Serve css/ and js/ folders
from pydantic import BaseModel, Field  # Validate JSON bodies (cmd field)

try:
    import serial  # pyserial - talk to Arduino over USB
    from serial import SerialException  # Error when port won't open
except ImportError:
    serial = None  # pyserial not installed
    SerialException = OSError

# Folder paths: bridge/ is inside GestureHome/, web/ is sibling folder
ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"

# Only these two words are allowed from the browser (Phase 1)
VALID_COMMANDS = frozenset({"LIGHTS_ON", "LIGHTS_OFF"})

# Create the FastAPI application (the "mailbox" with URL slots)
app = FastAPI(
    title="GestureHome Bridge",
    description="Phase 1: webcam gestures → serial → Keyestudio smart home kit.",
    version="0.1.0",
)

# Allow any website origin to POST (needed for local dev; browser security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state: USB connection and last command sent
_serial = None  # pyserial Serial object once USB is open
_last_cmd: Optional[str] = None  # e.g. "LIGHTS_ON"
_last_cmd_at: float = 0.0  # Unix time when last command was sent


class CommandBody(BaseModel):
    """JSON body for POST /command - browser sends {"cmd": "LIGHTS_ON"}"""
    cmd: str = Field(..., examples=["LIGHTS_ON"])


class HealthResponse(BaseModel):
    """JSON shape returned by GET /health"""
    ok: bool
    serial_connected: bool
    port: Optional[str] = None
    last_command: Optional[str] = None
    last_command_at: float = 0.0


class CommandResponse(BaseModel):
    """JSON shape returned by POST /command on success"""
    ok: bool
    cmd: Optional[str] = None
    error: Optional[str] = None


def open_serial(port: str, baud: int = 9600) -> None:
    """Open USB serial port to the Keyestudio board."""
    global _serial
    if serial is None:
        raise RuntimeError(
            "pyserial not installed. Run: conda activate home && pip install pyserial"
        )
    _serial = serial.Serial(port, baud, timeout=0.1)  # Open port at 9600 baud
    time.sleep(2.0)  # Arduino resets when USB opens - wait for it to boot
    _serial.reset_input_buffer()  # Clear junk bytes from reset


def send_command(cmd: str) -> None:
    """Write one line like LIGHTS_ON\n down the USB cable."""
    global _last_cmd, _last_cmd_at
    if _serial is None or not _serial.is_open:
        raise RuntimeError("Serial port not open")
    line = (cmd.strip().upper() + "\n").encode("ascii")  # Arduino reads until newline
    _serial.write(line)  # Send bytes to board
    _serial.flush()  # Make sure they leave the laptop immediately
    _last_cmd = cmd.strip().upper()  # Remember for /health
    _last_cmd_at = time.time()


@app.get("/")
def index():
    """Serve the main web page (camera + gestures UI)."""
    return FileResponse(WEB_DIR / "index.html")


# Mount folders so /css/styles.css and /js/gestures.js are served
app.mount("/css", StaticFiles(directory=WEB_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=WEB_DIR / "js"), name="js")


@app.get("/health", response_model=HealthResponse)
def health():
    """Browser asks: is USB plugged in? what was the last command?"""
    connected = _serial is not None and _serial.is_open
    return HealthResponse(
        ok=True,
        serial_connected=connected,
        port=_serial.port if connected else None,
        last_command=_last_cmd,
        last_command_at=_last_cmd_at,
    )


@app.post("/command", response_model=CommandResponse)
def command(body: CommandBody):
    """Browser sends {"cmd":"LIGHTS_ON"} - we forward it to serial."""
    cmd = body.cmd.strip().upper()
    if cmd not in VALID_COMMANDS:
        raise HTTPException(status_code=400, detail=f"Invalid command: {cmd}")

    try:
        send_command(cmd)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return CommandResponse(ok=True, cmd=cmd)


def list_serial_ports():
    """List USB serial devices (e.g. /dev/ttyUSB0)."""
    if serial is None:
        return []
    from serial.tools import list_ports

    return [p.device for p in list_ports.comports()]


def main():
    """Parse args, open USB, start web server on port 8090."""
    parser = argparse.ArgumentParser(description="GestureHome serial bridge (FastAPI)")
    parser.add_argument(
        "--port",
        default=os.environ.get("GESTURE_HOME_PORT", ""),
        help="Serial device (e.g. /dev/ttyUSB0). Auto-pick first USB if omitted.",
    )
    parser.add_argument("--host", default="127.0.0.1")  # Listen on localhost
    parser.add_argument("--port-http", type=int, default=8090, dest="http_port")  # Web port
    parser.add_argument("--baud", type=int, default=9600)  # Serial speed (match Arduino)
    parser.add_argument("--no-serial", action="store_true", help="Run web UI only (gesture test)")
    args = parser.parse_args()

    port = args.port
    if not args.no_serial:
        ports = list_serial_ports()
        if not port and ports:
            port = ports[0]  # Auto-pick first USB device
            print(f"Auto-selected serial port: {port}")
        if not port:
            print("No serial port found. Plug in Keyestudio USB or set GESTURE_HOME_PORT.")
            print("Available:", ports or "none")
            sys.exit(1)
        try:
            open_serial(port, args.baud)
            print(f"Serial open: {port} @ {args.baud}")
        except SerialException as exc:
            print(f"Failed to open {port}: {exc}")
            sys.exit(1)
    else:
        print("Running without serial (--no-serial). Manual buttons will not reach the house.")

    print(f"GestureHome: http://{args.host}:{args.http_port}/")
    print(f"API docs:    http://{args.host}:{args.http_port}/docs")

    import uvicorn  # ASGI server (like KickHub uses)

    uvicorn.run(app, host=args.host, port=args.http_port, log_level="info")


if __name__ == "__main__":
    main()  # Run when you execute: python bridge/bridge.py
