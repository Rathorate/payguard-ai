import pytest
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
