#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
command -v node >/dev/null || { echo 'Install Node.js 22.18+ before running bootstrap.' >&2; exit 1; }
node -e 'const [major,minor]=process.versions.node.split(".").map(Number); if(major<22||(major===22&&minor<18))throw Error("Node.js 22.18+ required")'
python_bin="${PYTHON_BIN:-python3}"
"$python_bin" -c 'import sys; assert sys.version_info >= (3, 12), "Python 3.12+ required. Set PYTHON_BIN if needed."'
if [[ ! -x .venv/bin/python ]]; then "$python_bin" -m venv .venv; fi
.venv/bin/python -m pip install -r requirements.txt
if [[ ! -e .env ]]; then cp -- .env.example .env; chmod 600 .env; fi
echo 'Run bash scripts/test.sh, then bash scripts/dev.sh'
