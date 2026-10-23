import os
import pytest

# Regressions are offline and disposable even when launched from a configured
# developer terminal. Intentional environment tests set their own values later.
# Keep TEST_POSTGRES_URL: CI explicitly points it at a disposable database.
for name in ('DATABASE_URL', 'DEMO_MODE', 'APP_ORIGIN', 'SECURE_COOKIES',
             'AI_PROVIDER', 'GROQ_API_KEY', 'GROQ_MODEL', 'GROQ_SCHEMA_RECOVERY', 'OPENAI_API_KEY', 'OPENAI_MODEL',
             'PAYPAL_ENVIRONMENT', 'PAYPAL_CLIENT_ID', 'PAYPAL_CLIENT_SECRET',
             'PAYPAL_WEBHOOK_ID', 'PAYPAL_TENANT_ID'):
    os.environ.pop(name, None)
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app


@pytest.fixture
def app(tmp_path):
    return create_app(Settings(database_url='sqlite:///' + (tmp_path / 'test.db').as_posix(), demo=True))


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client


@pytest.fixture
def merchant(client):
    data = client.post('/api/v1/auth/demo').json()
    client.headers['X-CSRF-Token'] = data['csrf']
    return client


def first_case(client):
    return client.get('/api/v1/disputes').json()['items'][0]


@pytest.fixture
def frozen_app_clock(monkeypatch):
    """Fixed-window rate tests must not straddle a real minute boundary."""
    from types import SimpleNamespace
    import app.main as main
    clock=SimpleNamespace(now=main.time.time(),monotonic=main.time.monotonic)
    clock.time=lambda:clock.now
    monkeypatch.setattr(main,'time',clock)
    return clock
