import time
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.models import LoginSession, User


def test_auth_required(client):
    for path in ['/disputes','/overview','/audit','/submissions','/integrations']:
        assert client.get('/api/v1' + path).status_code == 401


def test_register_login_logout(client):
    body = {'email':'owner@example.com','password':'a-long-test-password','company':'Test Shop'}
    result = client.post('/api/v1/auth/register', json=body)
    assert result.status_code == 201
    assert 'HttpOnly' in result.headers['set-cookie']
    assert 'SameSite=strict' in result.headers['set-cookie']
    client.headers['X-CSRF-Token'] = result.json()['csrf']
    assert client.get('/api/v1/auth/me').json()['email'] == body['email']
    assert client.post('/api/v1/auth/logout').status_code == 204
    assert client.get('/api/v1/auth/me').status_code == 401
    assert client.post('/api/v1/auth/login',json={k:v for k,v in body.items() if k!='company'}).status_code == 200
    assert client.post('/api/v1/auth/register',json=body).status_code == 409


def test_passwords_hashed(client, app):
    body = {'email':'owner@example.com','password':'a-long-test-password','company':'Test Shop'}
    client.post('/api/v1/auth/register',json=body)
    with app.state.sessions() as db:
        assert db.scalar(select(User)).password_hash != body['password']
    assert client.post('/api/v1/auth/login',json={'email':body['email'],'password':'wrong-long-password'}).status_code == 401
    assert client.post('/api/v1/auth/login',json={'email':'nobody@example.com','password':body['password']}).status_code == 401


def test_csrf_and_origin(merchant):
    assert merchant.post('/api/v1/auth/logout',headers={'X-CSRF-Token':'wrong'}).status_code == 403
    assert merchant.post('/api/v1/auth/logout',headers={'Origin':'https://evil.example'}).status_code == 403
    assert merchant.post('/api/v1/auth/login',json={'email':'test@example.com','password':'long-enough-password'},headers={'Origin':'https://evil.example'}).status_code == 403


def test_expired_session(merchant,app):
    with app.state.sessions() as db:
        row=db.scalar(select(LoginSession));row.expires=int(time.time())-1;db.commit()
    assert merchant.get('/api/v1/auth/me').status_code == 401


def test_tenant_isolation(merchant,app):
    identity=merchant.get('/api/v1/disputes').json()['items'][0]['id']
    tenant=merchant.get('/api/v1/auth/me').json()['tenant_id']
    with TestClient(app) as other:
        login=other.post('/api/v1/auth/demo').json();other.headers['X-CSRF-Token']=login['csrf']
        assert login['tenant_id'] != tenant
        assert other.get('/api/v1/disputes/'+identity).status_code == 404
        assert other.post('/api/v1/disputes/'+identity+'/draft',json={'version':1}).status_code == 404
        assert all(row['tenant_id']==login['tenant_id'] for row in other.get('/api/v1/audit').json()['items'])


def test_rate_limit(client):
    body={'email':'nobody@example.com','password':'long-enough-password'}
    for _ in range(10):
        assert client.post('/api/v1/auth/login',json=body).status_code == 401
    response=client.post('/api/v1/auth/login',json=body)
    assert response.status_code==429
    assert response.headers['retry-after']=='600'


def test_validation(client):
    assert client.post('/api/v1/auth/register',json={'email':'bad','password':'short','company':'X'}).status_code==422

