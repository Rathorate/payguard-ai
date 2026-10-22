#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
if [[ ! -x .venv/bin/python ]]; then echo "Run bash scripts/bootstrap.sh first." >&2; exit 1; fi
command -v node >/dev/null || { echo 'Node.js 22.18+ is required for the frontend.' >&2; exit 1; }
requested_frontend_port="${FRONTEND_PORT:-}"
requested_backend_port="${BACKEND_PORT:-}"
# Source only your own trusted local .env; never commit it.
if [[ -f .env ]]; then set -a; source .env; set +a; fi
export DEMO_MODE="${DEMO_MODE:-true}"
export FRONTEND_PORT="${requested_frontend_port:-${FRONTEND_PORT:-3000}}"
backend_port="${requested_backend_port:-${BACKEND_PORT:-${PORT:-8000}}}"
# Local dev deliberately overrides old .env origins to match the frontend port.
export APP_ORIGIN="http://127.0.0.1:${FRONTEND_PORT}"
export BACKEND_ORIGIN="http://127.0.0.1:${backend_port}"
.venv/bin/python - "$backend_port" "$FRONTEND_PORT" <<'PY'
import socket
import sys
from app.config import Settings
settings = Settings()
settings.validate()
print('AI provider:', settings.drafting_provider, '| Groq key loaded:', bool(settings.groq_key), flush=True)
print(settings.ai_status()['ai_message'], flush=True)
try:
    ports = [int(value) for value in sys.argv[1:]]
    if len(set(ports)) != 2 or any(not 1 <= port <= 65535 for port in ports):
        raise ValueError('Choose two different ports between 1 and 65535.')
    for port in ports:
        with socket.socket() as listener:
            try:
                listener.bind(('127.0.0.1', port))
            except OSError:
                raise ValueError(f'Port {port} is already in use. Keep the existing server, or choose different BACKEND_PORT / FRONTEND_PORT values.') from None
except ValueError as exc:
    sys.exit(str(exc))
print(f'Open http://127.0.0.1:{ports[1]} and keep this terminal open. Ctrl+C stops both servers.', flush=True)
PY
api_pid=''
frontend_pid=''
cleanup() {
  trap - EXIT INT TERM
  if [[ -n "$api_pid" ]]; then kill "$api_pid" 2>/dev/null || true; fi
  if [[ -n "$frontend_pid" ]]; then kill "$frontend_pid" 2>/dev/null || true; fi
  wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "$backend_port" &
api_pid=$!
node frontend/dev-server.mjs &
frontend_pid=$!
wait -n "$api_pid" "$frontend_pid"
