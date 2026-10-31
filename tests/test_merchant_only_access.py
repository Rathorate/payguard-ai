from app.config import Settings


def test_guest_access_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv('PUBLIC_DEMO_ENABLED', raising=False)
    assert Settings().public_demo_enabled is False


def test_disabling_guests_preserves_merchant_cases_and_simulation(client, app):
    app.state.settings.public_demo_enabled = False
    assert client.get('/api/v1/config').json()['public_demo_enabled'] is False
    assert client.post('/api/v1/auth/demo').status_code == 404
    login = client.post('/api/v1/auth/register', json={
        'company':'Merchant only', 'email':'merchant-only@example.com', 'password':'long-merchant-test-password'
    })
    assert login.status_code == 201 and login.json()['demo'] is True
    client.headers['X-CSRF-Token'] = login.json()['csrf']
    assert client.get('/api/v1/disputes').json()['total'] == 0
    assert client.post('/api/v1/demo/seed').status_code == 404
    item = client.post('/api/v1/disputes', json={
        'paypal_id':'PP-D-MERCHANT-ONLY','customer':'Synthetic test','reason':'INQUIRY',
        'amount_cents':1000,'currency':'USD','due_at':2000000000
    })
    assert item.status_code == 201
    identity = item.json()['id']
    app.state.settings.public_demo_enabled = True
    app.state.settings.public_demo_enabled = False
    assert client.get('/api/v1/disputes/'+identity).status_code == 200
    assert client.get('/api/v1/disputes').json()['total'] == 1
    assert app.state.settings.demo is True


def test_existing_sample_session_loses_access_when_guests_are_disabled(merchant, app):
    assert merchant.get('/api/v1/auth/me').status_code == 200
    app.state.settings.public_demo_enabled = False
    for path in ['/api/v1/auth/me','/api/v1/disputes','/api/v1/integrations']:
        assert merchant.get(path).status_code == 401
    assert merchant.post('/api/v1/auth/demo').status_code == 404


def test_live_mode_never_exposes_guest_entry_even_when_opted_in(client, app):
    app.state.settings.public_demo_enabled = True
    app.state.settings.demo = False
    assert client.get('/api/v1/config').json()['public_demo_enabled'] is False
    assert client.post('/api/v1/auth/demo').status_code == 404
