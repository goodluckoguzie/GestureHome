#!/usr/bin/env bash
# Quick smoke test for booth bridge (run while bridge is up on 8090 HTTPS).
set -euo pipefail
BASE="${BOOTH_TEST_URL:-https://127.0.0.1:8090}"
CURL_OPTS=(-sk)

echo "Testing $BASE"

curl "${CURL_OPTS[@]}" "$BASE/health" | python3 -m json.tool
echo "--- booth-info ---"
curl "${CURL_OPTS[@]}" "$BASE/booth-info" | python3 -m json.tool
echo "--- pages ---"
for path in host.html booth.html; do
  code=$(curl -sk -o /dev/null -w "%{http_code}" "$BASE/$path")
  echo "$path -> HTTP $code"
done
echo "--- command LIGHTS_ON ---"
curl "${CURL_OPTS[@]}" -X POST "$BASE/command" \
  -H "Content-Type: application/json" \
  -d '{"cmd":"LIGHTS_ON"}' | python3 -m json.tool
sleep 1
echo "--- command LIGHTS_OFF ---"
curl "${CURL_OPTS[@]}" -X POST "$BASE/command" \
  -H "Content-Type: application/json" \
  -d '{"cmd":"LIGHTS_OFF"}' | python3 -m json.tool
echo "--- house-status ---"
curl "${CURL_OPTS[@]}" "$BASE/house-status" | python3 -m json.tool
echo "PASS: booth smoke test"
