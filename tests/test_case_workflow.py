import json
import time
from types import SimpleNamespace
import pytest
from sqlalchemy import select
from app.models import ProviderObservation
from app.providers import ProviderError
from app.workflow import observe, preparation
from test_paypal_import import connect, resource

ID = 'PP-D-SANDBOX-42'


def linked(**changes):
    return resource(dispute_life_cycle_stage='INQUIRY', links=[{'rel':'provide-evidence','method':'POST',
        'href':f'https://api-m.sandbox.paypal.com/v1/customer/disputes/{ID}/provide-evidence'}], **changes)


def imported(merchant, app):
    connect(merchant, app)
    app.state.paypal.details = lambda identity: linked()
    response = merchant.post('/api/v1/paypal/disputes/import',json={'paypal_id':ID})
    assert response.status_code==201
    return response.json(), '/api/v1/disputes/'+response.json()['id']


def test_read_only_refresh_preserves_approved_response_and_snapshot(merchant, app):
    case,url=imported(merchant,app)
    draft=merchant.post(url+'/draft',json={'version':case['version']}).json()
    approved=merchant.post(url+'/approve',json={'version':draft['version'],'reviewed':True}).json()
    before=merchant.get(url).json()
    app.state.paypal.details=lambda _:linked(status='WAITING_FOR_BUYER_RESPONSE')
    refreshed=merchant.post(url+'/workflow/refresh',json={'version':approved['version']})
    assert refreshed.status_code==200
    result=refreshed.json()
    assert result['provider']['provider_status']=='WAITING_FOR_BUYER_RESPONSE'
    assert result['provider']['actions']==['provide-evidence']
    assert merchant.get(url).json()==before
    assert any(c['label']=='Delivery / fulfillment record' for c in preparation(
        SimpleNamespace(**{**case,'reason':'MERCHANDISE_OR_SERVICE_NOT_RECEIVED','draft':''}),[],None,None,True,True)['checks'])


def test_refresh_failure_retains_previous_observation(merchant, app):
    case,url=imported(merchant,app)
    before=merchant.get(url+'/workflow').json()
    def fail(_):raise ProviderError('Provider unavailable')
    app.state.paypal.details=fail
    assert merchant.post(url+'/workflow/refresh',json={'version':case['version']}).status_code==502
    assert merchant.get(url+'/workflow').json()==before
    assert merchant.post(url+'/workflow/refresh',json={'version':99}).status_code==409
    assert merchant.post(url+'/workflow/refresh',json={'version':case['version']},headers={'X-CSRF-Token':'bad'}).status_code==403


def test_observation_is_tenant_scoped_and_refresh_limited(merchant, app, frozen_app_clock):
    case,url=imported(merchant,app)
    for _ in range(5):assert merchant.post(url+'/workflow/refresh',json={'version':1}).status_code==200
    assert merchant.post(url+'/workflow/refresh',json={'version':1}).status_code==429
    merchant.post('/api/v1/auth/logout')
    assert merchant.get(url+'/workflow').status_code==401
    login=merchant.post('/api/v1/auth/register',json={'email':'second@example.invalid','password':'another-long-password','company':'Second shop'}).json()
    merchant.headers['X-CSRF-Token']=login['csrf']
    assert merchant.get(url+'/workflow').status_code==404
    assert merchant.post(url+'/workflow/refresh',json={'version':1}).status_code==404


@pytest.mark.parametrize('href',[
    'https://evil.example/v1/customer/disputes/'+ID+'/provide-evidence',
    'https://api-m.sandbox.paypal.com.evil.example/v1/customer/disputes/'+ID+'/provide-evidence',
    '/v1/customer/disputes/'+ID+'/provide-evidence',
    'https://api-m.sandbox.paypal.com/v1/customer/disputes/WRONG/provide-evidence',
    'https://api-m.sandbox.paypal.com/v1/customer/disputes/'+ID+'/provide-evidence?token=secret',
    'https://api-m.paypal.com/v1/customer/disputes/'+ID+'/provide-evidence',
])
def test_action_requires_matching_trusted_url(href):
    data=linked();data['links'][0]['href']=href
    assert observe(data,ID,'sandbox')['actions']==[]


@pytest.mark.parametrize('changes',[{'links':None},{'dispute_life_cycle_stage':'<script>'},{'dispute_id':'wrong'}])
def test_malformed_observations_fail(changes):
    data=linked();data.update(changes)
    with pytest.raises(ProviderError):observe(data,ID,'sandbox')


@pytest.mark.parametrize('change',[{'links':[]},{'status':'RESOLVED'},{'seller_response_due_date':'2027-02-01T00:00:00Z'}])
def test_real_send_preflight_blocks_changed_or_unavailable_action(merchant, app, change):
    case,url=imported(merchant,app)
    draft=merchant.post(url+'/draft',json={'version':1}).json()
    approved=merchant.post(url+'/approve',json={'version':draft['version'],'reviewed':True}).json()
    before=merchant.get(url).json()
    data=linked();data.update(change)
    app.state.paypal.details=lambda _:data
    def forbidden(*args):pytest.fail('Submission must not be attempted')
    app.state.paypal.submit=forbidden
    app.state.settings.demo=False
    response=merchant.post(url+'/submit',json={'version':approved['version'],'confirmed':True},headers={'Idempotency-Key':'preflight-blocked'})
    assert response.status_code==409
    assert merchant.get(url).json()==before
    assert merchant.get('/api/v1/submissions').json()['items']==[]


def test_old_cases_have_honest_empty_state_and_relevant_records(merchant):
    case=merchant.get('/api/v1/disputes').json()['items'][0]
    result=merchant.get('/api/v1/disputes/'+case['id']+'/workflow').json()
    assert result['provider'] is None and result['stale']
    assert 'win prediction' in result['notice']
    assert not any(c['state']=='VERIFIED' for c in result['checks'])


def test_observation_age_and_fact_change():
    case=SimpleNamespace(due_at=int(time.time())+3600,reason='INQUIRY',amount_cents=1000,currency='USD',draft='',status='APPROVED')
    data={'observed_at':int(time.time())-301,'due_at':case.due_at+1,'reason':'INQUIRY','amount_cents':1000,'currency':'USD','actions':[]}
    result=preparation(case,[],data,None,True,True)
    assert result['stale'] and result['facts_changed']


def test_submitted_checklist_uses_actual_matching_approval_history(merchant,app):
    case,url=imported(merchant,app)
    draft=merchant.post(url+'/draft',json={'version':case['version']}).json()
    approved=merchant.post(url+'/approve',json={'version':draft['version'],'reviewed':True}).json()
    assert merchant.post(url+'/submit',json={'version':approved['version'],'confirmed':True},headers={'Idempotency-Key':'checklist-simulated'}).status_code==200
    result=merchant.get(url+'/workflow').json()
    checks={c['label']:c for c in result['checks']}
    assert checks['Human approval']['state']=='RECORDED'
    assert f"version {approved['version']}" in checks['Human approval']['detail']
    assert 'locked' in checks['AI evidence checks']['detail']
    assert 'simulated submission is not PayPal acceptance' in result['next_step']


def test_locked_legacy_case_does_not_invent_approval_history():
    case=SimpleNamespace(due_at=int(time.time())+3600,reason='INQUIRY',amount_cents=1000,currency='USD',draft='',status='SUBMITTED')
    checks={c['label']:c for c in preparation(case,[],None,None,True,False)['checks']}
    assert checks['Human approval']['state']=='REVIEW'
    assert 'no approval record' in checks['Human approval']['detail']


@pytest.mark.parametrize('status',['OPEN','REVIEW','APPROVED'])
def test_missing_evidence_action_is_explained_before_approval(status):
    case=SimpleNamespace(due_at=int(time.time())+3600,reason='INQUIRY',amount_cents=1000,currency='USD',draft='',status=status)
    data={'observed_at':int(time.time()),'due_at':case.due_at,'reason':'INQUIRY','amount_cents':1000,'currency':'USD',
          'provider_status':'WAITING_FOR_SELLER_RESPONSE','actions':['escalate']}
    result=preparation(case,[],data,None,True,True)
    assert 'not currently offering evidence submission' in result['next_step']
    assert 'then approve' not in result['next_step']
