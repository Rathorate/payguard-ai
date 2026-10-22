import json
from unittest.mock import Mock
from sqlalchemy import select, update
from app.models import Webhook, Dispute
from app.providers import ProviderError
from app.worker import process_one


def setup_provider(merchant,app):
    tenant=merchant.get('/api/v1/auth/me').json()['tenant_id']
    app.state.settings.paypal_tenant_id=tenant
    app.state.paypal.verify=lambda headers,event:True
    return tenant


def event():
    return {'id':'WH-TEST','event_type':'CUSTOMER.DISPUTE.CREATED','resource':{'dispute_id':'PP-D-WEBHOOK'}}


def resource(**overrides):
    return {'dispute_id':'PP-D-WEBHOOK','reason':'INQUIRY','status':'WAITING_FOR_SELLER_RESPONSE','dispute_amount':{'value':'100.00','currency_code':'USD'},'seller_response_due_date':'2027-01-01T00:00:00Z','update_time':'2026-10-20T12:00:00Z',**overrides}


def test_invalid_webhook(client,app):
    assert client.post('/api/v1/webhooks/paypal',json=event()).status_code==503
    app.state.settings.paypal_tenant_id='unconfigured'
    assert client.post('/api/v1/webhooks/paypal',json=event()).status_code==401


def test_verify_outage(merchant,app):
    setup_provider(merchant,app)
    def fail(*args):raise ProviderError('unavailable')
    app.state.paypal.verify=fail
    assert merchant.post('/api/v1/webhooks/paypal',json=event()).status_code==503


def test_durable_dedupe_and_worker(merchant,app):
    tenant=setup_provider(merchant,app)
    assert merchant.post('/api/v1/webhooks/paypal',json=event()).json()['status']=='accepted'
    assert merchant.post('/api/v1/webhooks/paypal',json=event()).json()['status']=='duplicate'
    provider=Mock();provider.details.return_value=resource()
    assert process_one(app.state.sessions,provider)
    assert not process_one(app.state.sessions,provider)
    with app.state.sessions() as db:
        dispute=db.scalar(select(Dispute).where(Dispute.paypal_id=='PP-D-WEBHOOK'))
        assert dispute.tenant_id==tenant and dispute.amount_cents==10000
        assert db.scalar(select(Webhook)).state=='DONE'
    assert merchant.post('/api/v1/webhooks/paypal',json={'id':'bad','event_type':'CUSTOMER.DISPUTE.CREATED','resource':{}}).status_code==422
    assert merchant.post('/api/v1/webhooks/paypal',json={'event_type':'OTHER'}).json()['status']=='ignored'


def test_retries_and_dead_letter(merchant,app):
    setup_provider(merchant,app);merchant.post('/api/v1/webhooks/paypal',json=event())
    provider=Mock();provider.details.side_effect=ProviderError('upstream unavailable')
    for attempt in range(5):
        with app.state.sessions() as db:
            db.execute(update(Webhook).values(available_at=0));db.commit()
        assert process_one(app.state.sessions,provider)
    with app.state.sessions() as db:
        row=db.scalar(select(Webhook));assert row.state=='DEAD' and row.attempts==5


def test_resolved_event_and_old_snapshot(merchant,app):
    setup_provider(merchant,app)
    provider=Mock();provider.details.return_value=resource(status='RESOLVED')
    merchant.post('/api/v1/webhooks/paypal',json=event());process_one(app.state.sessions,provider)
    another=event();another['id']='WH-OLDER'
    provider.details.return_value=resource(update_time='2026-10-19T00:00:00Z')
    merchant.post('/api/v1/webhooks/paypal',json=another);process_one(app.state.sessions,provider)
    with app.state.sessions() as db:
        assert db.scalar(select(Dispute).where(Dispute.paypal_id=='PP-D-WEBHOOK')).status=='RESOLVED'


def test_provider_deadline_change_requires_new_human_review(merchant,app):
    setup_provider(merchant,app)
    provider=Mock();provider.details.return_value=resource()
    merchant.post('/api/v1/webhooks/paypal',json=event());process_one(app.state.sessions,provider)
    item=merchant.get('/api/v1/disputes?q=PP-D-WEBHOOK').json()['items'][0]
    url='/api/v1/disputes/'+item['id']
    merchant.post(url+'/evidence',json={'version':item['version'],'title':'Merchant receipt','kind':'INVOICE','content':'Synthetic merchant receipt records payment only.'})
    current=merchant.get(url).json()
    draft=merchant.post(url+'/draft',json={'version':current['version']}).json()
    approved=merchant.post(url+'/approve',json={'version':draft['version'],'reviewed':True}).json()
    changed=event();changed['id']='WH-NEW-DEADLINE'
    provider.details.return_value=resource(seller_response_due_date='2027-02-01T00:00:00Z',update_time='2026-10-22T12:00:00Z')
    merchant.post('/api/v1/webhooks/paypal',json=changed);process_one(app.state.sessions,provider)
    current=merchant.get(url).json()
    assert current['status']=='REVIEW' and current['draft']==approved['draft'] and current['version']>approved['version']
    assert merchant.post(url+'/submit',json={'version':current['version'],'confirmed':True},headers={'Idempotency-Key':'changed-deadline'}).status_code==409
