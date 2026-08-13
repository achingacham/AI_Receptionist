#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PORT="8000"
HEALTH_URL="http://127.0.0.1:${PORT}/health"

cd "$PROJECT_DIR"

if [ -d "$VENV_DIR" ]; then
  echo "Activating virtual environment: $VENV_DIR"
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
else
  echo "Virtual environment not found at $VENV_DIR"
  echo "Create it first: python3 -m venv .venv"
  exit 1
fi

echo "Stopping any existing uvicorn process..."
pkill -f "uvicorn.*backend.app.main:app" || true
pkill -f "python.*backend.app.main" || true

echo "Starting FastAPI service..."
nohup uvicorn backend.app.main:app --host 0.0.0.0 --port "$PORT" > service.log 2>&1 &

for i in {1..20}; do
  if curl -fsS "$HEALTH_URL" >/tmp/restart_service_health.json 2>/dev/null; then
    echo "Verification successful: $HEALTH_URL is responding."
    cat /tmp/restart_service_health.json
    echo
    echo "Service started successfully. Log file: $PROJECT_DIR/service.log"
    exit 0
  fi
  sleep 1
done

echo "ERROR: service did not become healthy on $HEALTH_URL within 20 seconds." >&2
if [ -f service.log ]; then
  echo "---- last log output ----" >&2
  tail -n 50 service.log >&2
fi
exit 1
