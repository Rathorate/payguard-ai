"""Execute the launcher's actual preflight against free and occupied ports."""
import os
from pathlib import Path
import socket
import subprocess
import sys


def test_launcher_reports_occupied_ports_and_masks_key():
    root = Path(__file__).resolve().parents[1]
    script = (root/'scripts/dev.sh').read_text(encoding='utf-8').split("<<'PY'\n",1)[1].split('\nPY',1)[0]
    env = {**os.environ,'DEMO_MODE':'true','AI_PROVIDER':'groq','GROQ_API_KEY':'never-print-this-test-key','APP_ORIGIN':'http://127.0.0.1:3001'}
    with socket.socket() as occupied, socket.socket() as unused:
        occupied.bind(('127.0.0.1',0));occupied.listen()
        unused.bind(('127.0.0.1',0))
        busy,free = occupied.getsockname()[1],unused.getsockname()[1]
        unused.close()
        failed = subprocess.run([sys.executable,'-c',script,str(busy),str(free)],cwd=root,env=env,capture_output=True,text=True,timeout=10)
        assert failed.returncode != 0 and f'Port {busy} is already in use' in failed.stderr
        assert 'never-print' not in failed.stdout+failed.stderr
        assert 'Groq key loaded: True' in failed.stdout
    with socket.socket() as second:
        second.bind(('127.0.0.1',0));other = second.getsockname()[1]
    passed = subprocess.run([sys.executable,'-c',script,str(free),str(other)],cwd=root,env=env,capture_output=True,text=True,timeout=10)
    assert passed.returncode == 0 and f'Open http://127.0.0.1:{other}' in passed.stdout
