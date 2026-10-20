#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
if [[ ! -x .venv/bin/python ]]; then echo "Run bash scripts/bootstrap.sh first." >&2; exit 1; fi
# Source only your own trusted local .env; never commit it.
if [[ -f .env ]]; then set -a; source .env; set +a; fi
export DEMO_MODE="${DEMO_MODE:-true}"
export APP_ORIGIN="${APP_ORIGIN:-http://127.0.0.1:8000}"
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "${PORT:-8000}" --reload
