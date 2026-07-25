#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export FM_HOST="${FM_HOST:-0.0.0.0}"
export FM_PORT="${1:-${FM_PORT:-8787}}"
echo "Starting free-match board on http://127.0.0.1:${FM_PORT}"
echo "UI:  http://127.0.0.1:${FM_PORT}/"
echo "API: http://127.0.0.1:${FM_PORT}/api/v1/meta"
exec python runtime/server.py --host "$FM_HOST" --port "$FM_PORT"
