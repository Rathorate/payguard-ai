import json
import httpx
import pytest
from types import SimpleNamespace
from app.config import Settings
from app.providers import ProviderHTTPError, generate_draft
from app.review import AnalysisValidationError, analyze_evidence


CASE = SimpleNamespace(paypal_id='SYNTHETIC-RECOVERY',reason='INQUIRY',amount_cents=1000,currency='USD')
RECORDS = [SimpleNamespace(id='e1',title='Synthetic receipt',content='SYNTHETIC: payment recorded only; no delivery verified.')]


def rejected(status=400, code='json_validate_failed'):
    return httpx.Response(status,json={'error':{'code':code,'failed_generation':'PRIVATE rejected content'}})


def test_recovery_is_bounded_explicit_and_keeps_server_owned_sources(caplog):
    calls=[]
    def respond(request):
        calls.append(json.loads(request.content))
        if len(calls)==1:return rejected()
        assert calls[-1]['response_format']=={'type':'json_object'}
        assert 'Return JSON matching this schema:' in calls[-1]['messages'][0]['content']
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'findings':[
            {'category':'RECORDED','statement':'The source records a synthetic payment only.','source_refs':['S1']}]})}}]})
    report,_=analyze_evidence(Settings(ai_provider='groq',groq_key='PRIVATE key',groq_schema_recovery=True),CASE,RECORDS,httpx.MockTransport(respond))
    assert len(calls)==2
    assert report['findings'][0]['sources']==[{'evidence_id':'e1','quote':RECORDS[0].content}]
    assert 'one validated JSON-mode recovery' in caplog.text and 'PRIVATE' not in caplog.text


@pytest.mark.parametrize('status,code',[(400,'tool_use_failed'),(401,'invalid_api_key'),(429,'rate_limit_exceeded'),(500,'json_validate_failed')])
def test_other_failures_never_trigger_recovery(status,code):
    calls=[]
    def respond(request):
        calls.append(request)
        return rejected(status,code)
    with pytest.raises(ProviderHTTPError):
        generate_draft(Settings(ai_provider='groq',groq_key='test',groq_schema_recovery=True),CASE,RECORDS,httpx.MockTransport(respond))
    assert len(calls)==1


def test_recovery_failure_stops_after_two_calls():
    calls=[]
    def respond(request):
        calls.append(request)
        return rejected()
    with pytest.raises(ProviderHTTPError):
        generate_draft(Settings(ai_provider='groq',groq_key='test',groq_schema_recovery=True),CASE,RECORDS,httpx.MockTransport(respond))
    assert len(calls)==2


def test_recovery_output_cannot_bypass_unknown_source_validation():
    calls=[]
    def respond(request):
        calls.append(request)
        if len(calls)==1:return rejected()
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'findings':[
            {'category':'RECORDED','statement':'Untrusted claim.','source_refs':['invented']}]})}}]})
    with pytest.raises(AnalysisValidationError):
        analyze_evidence(Settings(ai_provider='groq',groq_key='test',groq_schema_recovery=True),CASE,RECORDS,httpx.MockTransport(respond))
    assert len(calls)==2


def test_json_mode_models_do_not_recover_again():
    calls=[]
    def respond(request):
        calls.append(request)
        return rejected()
    with pytest.raises(ProviderHTTPError):
        generate_draft(Settings(ai_provider='groq',groq_key='test',groq_model='other-model',groq_schema_recovery=True),CASE,RECORDS,httpx.MockTransport(respond))
    assert len(calls)==1
