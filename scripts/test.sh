#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
.venv/bin/python -m pip check
.venv/bin/python -m pytest --cov=app --cov-report=term-missing
if command -v node >/dev/null 2>&1; then node --check static/app.js; else echo "Node unavailable: frontend syntax check skipped."; fi
