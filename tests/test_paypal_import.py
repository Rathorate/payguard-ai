import httpx
import pytest
from app.providers import PayPal, ProviderError
from app.paypal_import import snapshot
from app.config import Settings


def resource(**changes):
    return {'dispute_id':'PP-D-SANDBOX-42','reason':'INQUIRY','status':'WAITING_FOR_SELLER_RESPONSE','dispute_amount':{'value':'129.00','currency_code':'USD'},'seller_response_due_date':'2027-01-01T00:00:00Z','update_time':'2026-10-22T10:00:00Z','disputed_transactions':[{'buyer':{'name':{'given_name':'Test','surname':'Buyer'}}}],**changes}


def connect(merchant, app, handler=None):
    settings=app.state.settings
    settings.paypal_client_id,settings.paypal_secret='test-client','test-secret'
    settings.paypal_tenant_id=merchant.get('/api/v1/auth/me').json()['tenant_id']
    calls=[]
    def respond(request):
        calls.append(request)
        if handler:return handler(request)
        if request.url.path.endswith('/token'):return httpx.Response(200,json={'access_token':'never-expose-this-token'})
        assert request.method=='GET' and request.headers['Authorization']=='Bearer never-expose-this-token'
        return httpx.Response(200,json=resource())
    app.state.paypal=PayPal(settings,httpx.MockTransport(respond))
    return calls


def test_sandbox_auth_and_import_to_reviewed_simulation(merchant, app):
    calls=connect(merchant,app)
    auth=merchant.post('/api/v1/integrations/paypal/check')
    assert auth.status_code==200 and auth.json()['environment']=='sandbox'
    assert 'not yet verified' in auth.json()['notice']
    assert 'never-expose-this-token' not in auth.text and 'test-secret' not in auth.text
    before=merchant.get('/api/v1/disputes').json()['total']
    imported=merchant.post('/api/v1/paypal/disputes/import',json={'paypal_id':'PP-D-SANDBOX-42'})
    assert imported.status_code==201
    item=imported.json();url='/api/v1/disputes/'+item['id']
    assert item['amount_cents']==12900 and item['customer']=='Test Buyer' and item['status']=='OPEN'
    assert merchant.get('/api/v1/disputes').json()['total']==before+1
    evidence=merchant.get(url).json()['evidence']
    assert len(evidence)==1 and 'PAYPAL SANDBOX TEST DATA' in evidence[0]['content']
    draft=merchant.post(url+'/draft',json={'version':item['version']}).json()
    assert draft['status']=='REVIEW'
    assert merchant.post(url+'/submit',json={'version':draft['version'],'confirmed':True},headers={'Idempotency-Key':'sandbox-unapproved'}).status_code==409
    approved=merchant.post(url+'/approve',json={'version':draft['version'],'reviewed':True}).json()
    count=len(calls)
    assert merchant.post('/api/v1/paypal/disputes/import',json={'paypal_id':item['paypal_id']}).status_code==409
    assert len(calls)==count and merchant.get(url).json()['status']=='APPROVED'
    sent=merchant.post(url+'/submit',json={'version':approved['version'],'confirmed':True},headers={'Idempotency-Key':'sandbox-reviewed-demo'})
    assert sent.json()['state']=='SIMULATED' and len(calls)==count
    assert not any('/provide-evidence' in str(r.url) for r in calls)
    assert all(r.url.host=='api-m.sandbox.paypal.com' for r in calls)


def test_import_auth_csrf_mapping_and_environment(client, merchant, app):
    # merchant/client share a session; missing CSRF still has to fail.
    assert merchant.post('/api/v1/paypal/disputes/import',json={'paypal_id':'PP-D-SANDBOX-42'},headers={'X-CSRF-Token':'wrong'}).status_code==403
    assert merchant.post('/api/v1/integrations/paypal/check').status_code==409
    connect(merchant,app)
    app.state.settings.paypal_tenant_id='another-workspace'
    assert merchant.post('/api/v1/paypal/disputes/import',json={'paypal_id':'PP-D-SANDBOX-42'}).status_code==409
    assert merchant.post('/api/v1/integrations/paypal/check').status_code==409
    connect(merchant,app)
    app.state.settings.paypal_environment='live'
    assert merchant.post('/api/v1/paypal/disputes/import',json={'paypal_id':'PP-D-SANDBOX-42'}).status_code==409
    assert merchant.post('/api/v1/integrations/paypal/check').status_code==409


def test_import_requires_sign_in(client):
    assert client.post('/api/v1/paypal/disputes/import',json={'paypal_id':'PP-D-SANDBOX-42'}).status_code==401
    assert client.post('/api/v1/integrations/paypal/check').status_code==401


@pytest.mark.parametrize('code',[401,403,404,429,500])
def test_provider_failure_preserves_cases_and_sanitizes_errors(merchant, app, code):
    def handler(request):
        if request.url.path.endswith('/token'):return httpx.Response(200,json={'access_token':'test-token'})
        return httpx.Response(code,json={'error':'private-upstream-secret'})
    connect(merchant,app,handler)
    before=merchant.get('/api/v1/disputes').json()
    response=merchant.post('/api/v1/paypal/disputes/import',json={'paypal_id':'PP-D-SANDBOX-42'})
    assert response.status_code==502 and str(code) in response.json()['detail']
    assert 'private-upstream-secret' not in response.text
    assert merchant.get('/api/v1/disputes').json()==before


@pytest.mark.parametrize('change',[
    {'dispute_id':'different'}, {'reason':None}, {'dispute_amount':{'value':'NaN','currency_code':'USD'}},
    {'dispute_amount':{'value':'1.001','currency_code':'USD'}}, {'dispute_amount':{'value':'-1','currency_code':'USD'}},
    {'dispute_amount':{'value':'10000001','currency_code':'USD'}}, {'dispute_amount':{'value':'10','currency_code':'JPY'}},
    {'seller_response_due_date':'not-a-date'}, {'seller_response_due_date':'2027-01-01T00:00:00'},
    {'status':None}, {'update_time':123}
])
def test_import_snapshot_rejects_malformed_data(change):
    with pytest.raises(ProviderError):snapshot(resource(**change),'PP-D-SANDBOX-42')


def test_missing_deadline_and_resolved_case_are_not_invented():
    fields,content=snapshot(resource(seller_response_due_date=None,status='RESOLVED'),'PP-D-SANDBOX-42')
    assert fields['due_at']==0 and fields['status']=='RESOLVED' and 'unavailable' in content


@pytest.mark.parametrize('payload',[{},[],{'access_token':None},{'access_token':123},{'access_token':'bad\ntoken'}])
def test_auth_rejects_invalid_token_shape(payload):
    provider=PayPal(Settings(paypal_client_id='test',paypal_secret='test'),httpx.MockTransport(lambda r:httpx.Response(200,json=payload)))
    with pytest.raises(ProviderError):provider.check_sandbox_auth()


def test_auth_diagnostic_never_uses_live_or_missing_credentials():
    def forbidden(request):pytest.fail('Unexpected remote request')
    with pytest.raises(ProviderError):PayPal(Settings(paypal_environment='live'),httpx.MockTransport(forbidden)).check_sandbox_auth()
    with pytest.raises(ProviderError):PayPal(Settings(),httpx.MockTransport(forbidden)).check_sandbox_auth()


def test_import_bad_id_rejected_before_request(merchant,app):
    calls=connect(merchant,app)
    assert merchant.post('/api/v1/paypal/disputes/import',json={'paypal_id':'../../bad'}).status_code==422
    assert calls==[]


def test_auth_check_rate_limit(merchant,app,frozen_app_clock):
    calls=connect(merchant,app)
    for _ in range(3):assert merchant.post('/api/v1/integrations/paypal/check').status_code==200
    assert merchant.post('/api/v1/integrations/paypal/check').status_code==429
    assert len(calls)==3
    frozen_app_clock.now+=61
    assert merchant.post('/api/v1/integrations/paypal/check').status_code==200
    assert len(calls)==4
