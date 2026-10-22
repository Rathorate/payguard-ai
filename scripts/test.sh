#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
.venv/bin/python -m pip check
.venv/bin/python -m pytest --cov=app --cov-report=term-missing
node --check frontend/public/static/app.js
node --check frontend/public/static/review-ui.js
node --check frontend/public/static/questions-ui.js
node --check frontend/public/static/workflow-ui.js
node --test frontend/tests/*.test.mjs
