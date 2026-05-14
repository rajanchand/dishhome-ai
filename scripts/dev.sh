#!/usr/bin/env bash
# DishHome AI Call Center — one-shot dev launcher.
# Starts backend (uvicorn :8000), frontend (vite :3000), and an ngrok tunnel
# to backend :8000 so Twilio can reach your local webhooks.
#
# Usage:
#   ./scripts/dev.sh                 # backend + frontend + ngrok
#   ./scripts/dev.sh --no-ngrok      # local only
#
# Requirements (one-time):
#   brew install ngrok && ngrok config add-authtoken <token>
#   cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt
#   cd frontend && npm install

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

USE_NGROK=1
for arg in "$@"; do
  case "$arg" in
    --no-ngrok) USE_NGROK=0 ;;
  esac
done

mkdir -p .dev
LOG_BACKEND=".dev/backend.log"
LOG_FRONTEND=".dev/frontend.log"
LOG_NGROK=".dev/ngrok.log"

cleanup() {
  echo
  echo "--- shutting down ---"
  [[ -n "${BACKEND_PID:-}" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  [[ -n "${FRONTEND_PID:-}" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
  [[ -n "${NGROK_PID:-}" ]] && kill "$NGROK_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "→ Backend (uvicorn :8000) → $LOG_BACKEND"
( cd backend && exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload ) \
  >"$LOG_BACKEND" 2>&1 &
BACKEND_PID=$!

echo "→ Frontend (vite :3000)   → $LOG_FRONTEND"
( cd frontend && exec npm run dev -- --port 3000 ) >"$LOG_FRONTEND" 2>&1 &
FRONTEND_PID=$!

if [[ "$USE_NGROK" == "1" ]]; then
  if ! command -v ngrok >/dev/null 2>&1; then
    echo "!! ngrok not installed. Install with: brew install ngrok"
    echo "   Skipping tunnel — Twilio webhooks will not reach this machine."
  else
    echo "→ ngrok http 8000          → $LOG_NGROK"
    ngrok http 8000 --log=stdout --log-format=logfmt >"$LOG_NGROK" 2>&1 &
    NGROK_PID=$!
    echo "   Waiting for tunnel URL…"
    for i in {1..20}; do
      sleep 0.5
      URL=$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null \
        | python3 -c 'import sys,json
try:
  d=json.load(sys.stdin)
  for t in d.get("tunnels",[]):
    if t.get("proto")=="https": print(t["public_url"]); break
except Exception: pass' 2>/dev/null || true)
      if [[ -n "${URL:-}" ]]; then
        echo
        echo "   ngrok https URL: $URL"
        echo "   Paste this into backend/.env as PUBLIC_BASE_URL=$URL then restart backend."
        break
      fi
    done
  fi
fi

echo
echo "============================================================"
echo "  Backend  http://localhost:8000   (docs /docs)"
echo "  Frontend http://localhost:3000"
echo "  Tail logs:   tail -f .dev/*.log"
echo "  Ctrl-C to stop everything."
echo "============================================================"

wait
