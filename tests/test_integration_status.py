def test_paypal_status_distinguishes_mapping_and_credentials_without_disclosing_secrets(merchant, app):
    settings = app.state.settings
    settings.paypal_tenant_id = 'other-merchant'
    settings.paypal_client_id = 'private-client'
    settings.paypal_secret = 'private-secret'
    response = merchant.get('/api/v1/integrations')
    assert response.json()['paypal_status'] == 'workspace_unlinked'
    assert response.json()['paypal_configured'] is False
    assert all(value not in response.text for value in ['other-merchant', 'private-client', 'private-secret'])
    assert merchant.post('/api/v1/integrations/paypal/check').status_code == 409
    settings.paypal_tenant_id = merchant.get('/api/v1/auth/me').json()['tenant_id']
    assert merchant.get('/api/v1/integrations').json()['paypal_status'] == 'configured'
    settings.paypal_secret = ''
    data = merchant.get('/api/v1/integrations').json()
    assert data['paypal_status'] == 'credentials_missing'
    assert data['paypal_configured'] is False
