#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
if [[ ! -x .venv/bin/python ]]; then echo 'Run bash scripts/bootstrap.sh first.' >&2; exit 1; fi
if [[ -f .env ]]; then set -a; source .env; set +a; fi
.venv/bin/python -m app.evaluate_ai "$@"
