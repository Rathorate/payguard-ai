import httpx
import pytest
from app.providers import generate_draft, ProviderError
from app.config import Settings


def test_empty_account_can_load_samples_once(client):
    login = client.post('/api/v1/auth/register',json={'company':'Empty test shop','email':'empty@example.com','password':'a-long-test-password'})
    assert login.status_code == 201 and not login.json()['sample_workspace']
    client.headers['X-CSRF-Token'] = login.json()['csrf']
    assert client.get('/api/v1/disputes').json()['total'] == 0
    assert client.post('/api/v1/demo/seed',headers={'X-CSRF-Token':'wrong'}).status_code == 403
    assert client.post('/api/v1/demo/seed').json() == {'status':'seeded','count':4}
    first = client.get('/api/v1/disputes').json()
    assert first['total'] == 4
    assert client.post('/api/v1/demo/seed').status_code == 409
    assert client.get('/api/v1/disputes').json() == first


def test_sample_loader_not_available_in_live_mode(merchant, app):
    app.state.settings.demo = False
    assert merchant.post('/api/v1/demo/seed').status_code == 404


def test_demo_login_is_labeled_as_sample_workspace(merchant):
    assert merchant.get('/api/v1/auth/me').json()['sample_workspace']
    assert merchant.get('/api/v1/disputes').json()['total'] == 4


@pytest.mark.parametrize('provider,key', [('template','secret-test-value'),('groq','')])
def test_disabled_or_missing_key_is_visible_and_check_does_not_call_provider(merchant,app,provider,key):
    app.state.settings.ai_provider, app.state.settings.groq_key = provider,key
    status = merchant.get('/api/v1/integrations').json()
    assert status['ai_provider'] == provider and not status['ai_configured']
    assert status['groq_key_present'] == bool(key)
    assert 'restart' in status['ai_message']
    assert key == '' or key not in str(status)
    def forbidden(*args): pytest.fail('Unconfigured AI provider was called')
    app.state.drafter = forbidden
    assert merchant.post('/api/v1/integrations/ai/check').status_code == 409


def test_ai_connection_check_uses_synthetic_data_without_changing_cases(merchant, app, frozen_app_clock):
    settings = app.state.settings
    settings.ai_provider,settings.groq_key,settings.groq_model = 'groq','test-key','test-model'
    requests = []
    def handler(request):
        requests.append(request)
        assert b'SYNTHETIC CONNECTION TEST' in request.content
        assert b'PP-D-CONNECTION-TEST' in request.content
        assert b'@demo.invalid' not in request.content
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':__import__('json').dumps({'paragraphs':[{'text':'Synthetic receipt records payment. Delivery and authorization remain unverified.','evidence_ids':['SAMPLE-RECEIPT']}],'missing_facts':[]})}}]})
    app.state.drafter = lambda settings,item,records:generate_draft(settings,item,records,httpx.MockTransport(handler))
    before = merchant.get('/api/v1/disputes').json()
    assert merchant.post('/api/v1/integrations/ai/check',headers={'X-CSRF-Token':'wrong'}).status_code == 403
    result = merchant.post('/api/v1/integrations/ai/check')
    assert result.status_code == 200 and result.json()['provider'] == 'GROQ'
    assert result.json()['model'] == 'test-model'
    assert merchant.get('/api/v1/disputes').json() == before
    assert merchant.get('/api/v1/submissions').json()['items'] == []
    assert any(x['action']=='AI_CONNECTION_VERIFIED_GROQ' for x in merchant.get('/api/v1/audit').json()['items'])
    assert len(requests) == 1
    for _ in range(2): assert merchant.post('/api/v1/integrations/ai/check').status_code == 200
    assert merchant.post('/api/v1/integrations/ai/check').status_code == 429
    assert len(requests) == 3


def test_failed_ai_check_preserves_state(merchant, app):
    app.state.settings.ai_provider,app.state.settings.groq_key = 'groq','test-key'
    before = merchant.get('/api/v1/disputes').json()
    def fail(*args): raise ProviderError('Groq rate limit; no draft was changed')
    app.state.drafter = fail
    assert merchant.post('/api/v1/integrations/ai/check').status_code == 502
    assert merchant.get('/api/v1/disputes').json() == before
    assert merchant.get('/api/v1/submissions').json()['items'] == []


def test_ai_check_requires_auth(client):
    assert client.post('/api/v1/integrations/ai/check').status_code == 401
    assert client.post('/api/v1/demo/seed').status_code == 401


def test_configuration_can_detect_key_disabled_by_template_selection():
    status = Settings(ai_provider='template',groq_key='test-only-secret').ai_status()
    assert not status['ai_configured'] and status['groq_key_present']
    assert 'AI_PROVIDER=template disables AI' in status['ai_message']
    assert 'test-only-secret' not in str(status)
