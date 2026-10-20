from types import SimpleNamespace
import httpx
import pytest
from app.config import Settings
from app.providers import PayPal, ProviderError, generate_draft


def test_paypal_oauth_verification_and_evidence_contract():
    requests=[]
    def handler(request):
        requests.append(request)
        if request.url.path.endswith('/token'):return httpx.Response(200,json={'access_token':'test-token'})
        assert request.headers['authorization']=='Bearer test-token'
        if request.url.path.endswith('verify-webhook-signature'):return httpx.Response(200,json={'verification_status':'SUCCESS'})
        if request.method=='GET':return httpx.Response(200,json={'status':'WAITING_FOR_SELLER_RESPONSE','links':[{'rel':'provide-evidence'}]})
        return httpx.Response(200,json={'links':[]})
    settings=Settings(paypal_client_id='test-client',paypal_secret='test-secret',paypal_webhook_id='hook')
    provider=PayPal(settings,httpx.MockTransport(handler))
    headers={name:'test' for name in ['paypal-auth-algo','paypal-cert-url','paypal-transmission-id','paypal-transmission-sig','paypal-transmission-time']}
    assert provider.verify(headers,{'id':'WH-TEST'})
    assert not provider.verify({}, {})
    provider.submit('PP-D-123','Merchant response',[SimpleNamespace(id='e1',title='Invoice',content='Order paid')])
    import json
    assert json.loads(requests[-1].content)['evidences'][0]['evidence_type']=='OTHER'
    assert requests[-1].url.host=='api-m.sandbox.paypal.com'
    with pytest.raises(ProviderError):provider.details('../../oops')


def test_paypal_failure_and_unconfigured():
    with pytest.raises(ProviderError):PayPal(Settings()).details('PP-D-123')
    settings=Settings(paypal_client_id='test',paypal_secret='test')
    provider=PayPal(settings,httpx.MockTransport(lambda r:httpx.Response(500,json={})))
    with pytest.raises(ProviderError):provider.details('PP-D-123')
    provider=PayPal(settings,httpx.MockTransport(lambda r:httpx.Response(200,json={'access_token':'test','status':'RESOLVED'})))
    with pytest.raises(ProviderError):provider.submit('PP-D-123','test',[])


def test_ai_drafting_contract_and_errors():
    import json
    dispute=SimpleNamespace(paypal_id='PP-D-123',reason='INQUIRY',amount_cents=1000,currency='USD')
    evidence=[SimpleNamespace(id='e1',title='Receipt',content='Order paid')]
    def handler(request):
        body=json.loads(request.content)
        assert body['store'] is False
        assert 'untrusted' in body['instructions']
        assert json.loads(body['input'])['evidence'][0]['id']=='e1'
        return httpx.Response(200,json={'output':[{'type':'message','content':[{'type':'output_text','text':'Draft based on receipt [e1].'}]}]})
    settings=Settings(openai_key='test',openai_model='test-model')
    text,source=generate_draft(settings,dispute,evidence,httpx.MockTransport(handler))
    assert source=='OPENAI' and '[e1]' in text
    with pytest.raises(ProviderError):generate_draft(settings,dispute,evidence,httpx.MockTransport(lambda r:httpx.Response(429,json={})))
    with pytest.raises(ProviderError):generate_draft(settings,dispute,evidence,httpx.MockTransport(lambda r:httpx.Response(200,json={'output':[]})))
    with pytest.raises(ProviderError):generate_draft(Settings(openai_key='test'),dispute,evidence)


def test_production_config():
    with pytest.raises(ValueError):Settings(demo=False).validate()
    with pytest.raises(ValueError):Settings(paypal_environment='typo').validate()
    Settings(demo=False,secure_cookies=True,origin='https://example.com').validate()

