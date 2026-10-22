#!/usr/bin/env bash
# Read-only authentication / optional dispute lookup. No keys or tokens printed.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
if [[ ! -x .venv/bin/python ]]; then echo 'Run bash scripts/bootstrap.sh first.' >&2; exit 1; fi
if [[ -f .env ]]; then set -a; source .env; set +a; fi
.venv/bin/python -m app.check_paypal "$@"
