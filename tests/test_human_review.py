"""Approval binds to saved facts; simulation never calls a payment provider."""
import json
import pytest
from fastapi.testclient import TestClient
from app.security import digest
from conftest import first_case


def draft_case(merchant):
    item = first_case(merchant)
    url = '/api/v1/disputes/' + item['id']
    draft = merchant.post(url+'/draft', json={'version':item['version']})
    assert draft.status_code == 200
    return url, draft.json()


@pytest.mark.parametrize('value', [False, 1, 'true', None])
def test_review_requires_explicit_boolean(merchant, value):
    url, draft = draft_case(merchant)
    assert merchant.post(url+'/approve', json={'version':draft['version'], 'reviewed':value}).status_code == 422
    assert merchant.get(url).json()['status'] == 'REVIEW'


@pytest.mark.parametrize('value', [False, 1, 'true', None])
def test_submit_requires_explicit_boolean(merchant, value):
    url, draft = draft_case(merchant)
    approved = merchant.post(url+'/approve', json={'version':draft['version'],'reviewed':True}).json()
    assert merchant.post(url+'/submit', json={'version':approved['version'],'confirmed':value}, headers={'Idempotency-Key':'explicit-confirmation'}).status_code == 422
    assert merchant.get(url).json()['status'] == 'APPROVED'


def test_export_withdraw_edit_and_reapprove(merchant, app):
    url, draft = draft_case(merchant)
    assert merchant.get(url+'/export', params={'version':draft['version']}).status_code == 409
    assert merchant.post(url+'/submit', json={'version':draft['version'],'confirmed':True}, headers={'Idempotency-Key':'unapproved-response'}).status_code == 409
    approved = merchant.post(url+'/approve', json={'version':draft['version'],'reviewed':True}).json()
    assert merchant.get(url+'/export', params={'version':draft['version']}).status_code == 409
    response = merchant.get(url+'/export', params={'version':approved['version']})
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['content-disposition'].startswith('attachment; filename="payguard-')
    packet = response.json()
    checksum = packet.pop('sha256')
    assert checksum == digest(json.dumps(packet, sort_keys=True))
    assert packet['case']['draft'] == approved['draft']
    assert packet['mode'] == 'demo' and packet['evidence']
    assert merchant.get(url).json()['status'] == 'APPROVED'
    with TestClient(app) as other:
        login = other.post('/api/v1/auth/demo').json()
        other.headers['X-CSRF-Token'] = login['csrf']
        assert other.get(url+'/export', params={'version':approved['version']}).status_code == 404
        assert other.post(url+'/request-changes', json={'version':approved['version']}).status_code == 404
    review = merchant.post(url+'/request-changes', json={'version':approved['version']})
    assert review.status_code == 200 and review.json()['status'] == 'REVIEW'
    assert merchant.post(url+'/submit', json={'version':approved['version'],'confirmed':True}, headers={'Idempotency-Key':'withdrawn-response'}).status_code == 409
    assert merchant.post(url+'/approve', json={'version':approved['version'],'reviewed':True}).status_code == 409
    edited = merchant.put(url+'/draft', json={'version':review.json()['version'], 'text':'Updated merchant response after a second human review of the invoice.'}).json()
    assert edited['status'] == 'REVIEW'
    approved = merchant.post(url+'/approve', json={'version':edited['version'],'reviewed':True}).json()
    # Even configured PayPal credentials cannot turn a demo submission into a real write.
    app.state.settings.paypal_client_id = 'test-client'
    app.state.settings.paypal_secret = 'test-secret'
    def forbidden(*args):
        pytest.fail('Demo called PayPal')
    app.state.paypal.submit = forbidden
    receipt = merchant.post(url+'/submit', json={'version':approved['version'],'confirmed':True}, headers={'Idempotency-Key':'human-reviewed-demo'})
    assert receipt.status_code == 200 and receipt.json()['state'] == 'SIMULATED'
    assert receipt.json()['provider_reference'].startswith('SIMULATED-')
    assert merchant.post(url+'/request-changes', json={'version':approved['version']}).status_code == 409
    actions = {row['action'] for row in merchant.get('/api/v1/audit').json()['items']}
    assert {'DRAFT_APPROVED','APPROVAL_WITHDRAWN','DRAFT_EDITED','SUBMISSION_SIMULATED'} <= actions


def test_saved_edit_always_revokes_approval(merchant):
    url, draft = draft_case(merchant)
    approved = merchant.post(url+'/approve', json={'version':draft['version'],'reviewed':True}).json()
    changed = merchant.put(url+'/draft', json={'version':approved['version'],'text':approved['draft']+' Additional merchant statement.'}).json()
    assert changed['status'] == 'REVIEW'
    assert merchant.get(url+'/export', params={'version':approved['version']}).status_code == 409
    assert merchant.post(url+'/submit', json={'version':approved['version'],'confirmed':True}, headers={'Idempotency-Key':'old-approved-draft'}).status_code == 409


def test_groq_failure_preserves_existing_approval(merchant, app):
    from app.providers import ProviderError
    url, draft = draft_case(merchant)
    approved = merchant.post(url+'/approve', json={'version':draft['version'],'reviewed':True}).json()
    def fail(*args):
        raise ProviderError('Groq unavailable; no draft was changed')
    app.state.drafter = fail
    assert merchant.post(url+'/draft', json={'version':approved['version']}).status_code == 502
    current = merchant.get(url).json()
    assert current['draft'] == approved['draft'] and current['version'] == approved['version'] and current['status'] == 'APPROVED'
