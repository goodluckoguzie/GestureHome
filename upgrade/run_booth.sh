#!/usr/bin/env bash
# Start GestureHome booth bridge for event LAN (HTTPS for iPhone cameras).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${GESTURE_HOME_PORT:-/dev/ttyUSB0}"
HTTP_PORT="${BOOTH_HTTP_PORT:-8090}"
BIND_HOST="${BOOTH_BIND_HOST:-0.0.0.0}"
CERT_DIR="${BOOTH_CERT_DIR:-$ROOT/upgrade/.local}"
KEY_FILE="$CERT_DIR/booth-key.pem"
CERT_FILE="$CERT_DIR/booth-cert.pem"

cd "$ROOT"
mkdir -p "$CERT_DIR"

if [[ ! -f "$KEY_FILE" || ! -f "$CERT_FILE" ]]; then
  echo "Creating self-signed HTTPS cert (for iPhone camera) in $CERT_DIR"
  openssl req -x509 -newkey rsa:2048 \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -days 365 -nodes \
    -subj "/CN=gesturehome-booth" 2>/dev/null
fi

SSL_ARGS="--ssl-keyfile \"$KEY_FILE\" --ssl-certfile \"$CERT_FILE\""
export BOOTH_SSL_KEY="$KEY_FILE"
export BOOTH_SSL_CERT="$CERT_FILE"

if command -v conda >/dev/null 2>&1; then
  RUN="conda run -n home python upgrade/booth_bridge.py --port \"$PORT\" --host \"$BIND_HOST\" --port-http \"$HTTP_PORT\" $SSL_ARGS"
else
  RUN="python upgrade/booth_bridge.py --port \"$PORT\" --host \"$BIND_HOST\" --port-http \"$HTTP_PORT\" $SSL_ARGS"
fi

echo "Binding $BIND_HOST:$HTTP_PORT with HTTPS (phones need https for camera)"
eval "$RUN" &
PID=$!
sleep 3

LAN_IP="$(python3 -c "
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    print(s.getsockname()[0])
    s.close()
except OSError:
    print('127.0.0.1')
" 2>/dev/null || echo "127.0.0.1")"

HOST_URL="https://${LAN_IP}:${HTTP_PORT}/host.html"
PHONE_URL="https://${LAN_IP}:${HTTP_PORT}/booth.html"

echo ""
echo "Projector (QR):  $HOST_URL"
echo "Phone (gestures): $PHONE_URL"
echo "iPhone: accept certificate warning, then Start camera"
echo ""

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$HOST_URL" >/dev/null 2>&1 || true
fi

echo "Bridge PID $PID - Ctrl+C to stop"
wait $PID
