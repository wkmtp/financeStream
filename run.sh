#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${UVICORN_WORKERS:-2}"
LOG_LEVEL="${UVICORN_LOG_LEVEL:-info}"

exec uvicorn app.main:app \
  --host "${HOST}" \
  --port "${PORT}" \
  --workers "${WORKERS}" \
  --log-level "${LOG_LEVEL}" \
  --proxy-headers
