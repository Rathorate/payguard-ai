import hashlib
import httpx
import pytest
from app.config import Settings
from app.providers import PayPal, ProviderError


@pytest.mark.parametrize('scope,expected',[(None,None),('',False),('https://uri.paypal.com/services/disputes/read-seller',True),('https://uri.paypal.com/services/disputes/update-seller',False)])
def test_diagnostic_identifies_app_and_read_scope_without_credentials(scope,expected):
    provider=PayPal(Settings(paypal_client_id='private-client',paypal_secret='private-secret'),httpx.MockTransport(lambda r:httpx.Response(200,json={'access_token':'private-token','scope':scope})))
    result=provider.check_sandbox_auth()
    assert result['client_id_fingerprint']==hashlib.sha256(b'private-client').hexdigest()[:12]
    assert result['dispute_read_scope_present'] is expected
    assert all(secret not in str(result) for secret in ['private-client','private-secret','private-token'])


def test_error_only_exposes_protocol_codes_and_debug_reference():
    def handler(request):
        return httpx.Response(403,json={'name':'NOT_AUTHORIZED','debug_id':'abc123','message':'private-upstream-secret','details':[{'issue':'REQUIRED_SCOPE_MISSING','description':'private-description'}]})
    provider=PayPal(Settings(paypal_client_id='test',paypal_secret='test'),httpx.MockTransport(handler))
    with pytest.raises(ProviderError) as result:provider.details('PP-R-TEST')
    assert 'REQUIRED_SCOPE_MISSING' in str(result.value) and 'abc123' in str(result.value)
    assert 'private' not in str(result.value)


def test_discovery_lists_only_bounded_ids_statuses_and_uses_sandbox():
    def handler(request):
        if request.url.path.endswith('/token'):return httpx.Response(200,json={'access_token':'private-token'})
        assert request.url.host=='api-m.sandbox.paypal.com' and request.url.params['page_size']=='10'
        return httpx.Response(200,json={'items':[{'dispute_id':'PP-R-TEST','status':'WAITING_FOR_SELLER_RESPONSE','buyer':{'email':'private@example.invalid'}}]})
    result=PayPal(Settings(paypal_client_id='test',paypal_secret='test'),httpx.MockTransport(handler)).list_sandbox_disputes()
    assert result==[{'dispute_id':'PP-R-TEST','status':'WAITING_FOR_SELLER_RESPONSE'}]
    with pytest.raises(ProviderError):PayPal(Settings(paypal_environment='live')).list_sandbox_disputes()


@pytest.mark.parametrize('payload',[[],{'items':None},{'items':[None]},{'items':[{'dispute_id':'../../bad'}]},{'items':[{'dispute_id':'PP-R-TEST','status':'<script>'}]}])
def test_discovery_rejects_invalid_provider_data(payload):
    def handler(request):
        return httpx.Response(200,json={'access_token':'test'}) if request.url.path.endswith('/token') else httpx.Response(200,json=payload)
    with pytest.raises(ProviderError):PayPal(Settings(paypal_client_id='test',paypal_secret='test'),httpx.MockTransport(handler)).list_sandbox_disputes()
