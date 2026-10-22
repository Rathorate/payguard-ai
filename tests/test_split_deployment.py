"""Exercise real frontend-to-backend HTTP, including cookies and PDF upload."""
import io
import os
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn
from reportlab.pdfgen import canvas


def unused_port():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        return listener.getsockname()[1]


def test_separate_frontend_full_workflow(app):
    node = shutil.which('node')
    if not node:
        pytest.fail('Node.js is required to test the separately deployed frontend')
    backend_port, frontend_port = unused_port(), unused_port()
    frontend_origin = f'http://127.0.0.1:{frontend_port}'
    app.state.settings.origin = frontend_origin
    server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=backend_port, log_level='error'))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, 'FRONTEND_PORT':str(frontend_port), 'BACKEND_ORIGIN':f'http://127.0.0.1:{backend_port}'}
    process = subprocess.Popen([node, str(root/'frontend/dev-server.mjs')], cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    try:
        deadline = time.monotonic() + 20
        with httpx.Client(base_url=frontend_origin, headers={'Origin':frontend_origin}, timeout=10, trust_env=False) as client:
            while True:
                try:
                    if server.started and client.get('/').status_code == 200: break
                except httpx.HTTPError: pass
                if process.poll() is not None: pytest.fail('Frontend failed: ' + process.communicate()[1].decode())
                if time.monotonic() > deadline: pytest.fail('Separate servers did not become ready')
                time.sleep(.05)
            assert client.get('/static/app.js').status_code == 200
            login = client.post('/api/v1/auth/demo')
            assert login.status_code == 200
            assert 'HttpOnly' in login.headers['set-cookie']
            client.headers['X-CSRF-Token'] = login.json()['csrf']
            assert client.get('/api/v1/auth/me').status_code == 200
            item = client.get('/api/v1/disputes').json()['items'][0]
            url = '/api/v1/disputes/' + item['id']
            buffer = io.BytesIO(); pdf = canvas.Canvas(buffer); pdf.drawString(50, 750, 'Merchant invoice: payment received for order 100.'); pdf.save()
            uploaded = client.post(url+'/upload', data={'version':item['version']}, files={'file':('invoice.pdf',buffer.getvalue(),'application/pdf')})
            assert uploaded.status_code == 201
            current = client.get(url).json()
            draft = client.post(url+'/draft', json={'version':current['version']}).json()
            approved = client.post(url+'/approve', json={'version':draft['version'],'reviewed':True}).json()
            sent = client.post(url+'/submit', json={'version':approved['version'],'confirmed':True}, headers={'Idempotency-Key':'split-deployment-workflow'})
            assert sent.status_code == 200 and sent.json()['state'] == 'SIMULATED'
            assert client.get(url).json()['status'] == 'SUBMITTED'
            assert any(x['action']=='SUBMISSION_SIMULATED' for x in client.get('/api/v1/audit').json()['items'])
            assert client.post('/api/v1/auth/logout', headers={'Origin':'https://untrusted.test'}).status_code == 403
            assert client.post('/api/v1/auth/logout').status_code == 204
            assert client.get('/api/v1/auth/me').status_code == 401
    finally:
        process.terminate()
        try: process.communicate(timeout=5)
        except subprocess.TimeoutExpired: process.kill(); process.communicate()
        server.should_exit = True
        thread.join(timeout=10)
