import json
from types import SimpleNamespace
import httpx
import pytest
from app.config import Settings
from app.providers import ProviderHTTPError
from app.review import AnalysisValidationError, analyze_evidence


def run(raw, records):
    case=SimpleNamespace(reason='MERCHANDISE_OR_SERVICE_NOT_RECEIVED',amount_cents=1000,currency='USD')
    return analyze_evidence(Settings(ai_provider='groq',groq_key='test'),case,records,
        httpx.MockTransport(lambda _:httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':raw}}]})))


def record(identity='e1', content=None):
    return SimpleNamespace(id=identity,title='Synthetic source',content=content or 'Synthetic tracking only. No carrier scan or delivery has been verified.')


def test_analysis_attaches_original_unicode_excerpts_without_model_copying():
    records=[record(content='SYNTHETIC record: “fictional” tracking — no delivery.\n' + 'Repeated source text. '*60)]
    raw=json.dumps({'findings':[{'category':'RECORDED','statement':'The source explicitly describes fictional tracking.','source_refs':['S1']},
        {'category':'MISSING','statement':'Actual delivery is not established by the record.','source_refs':['S2']}]})
    report,provider=run(raw,records)
    assert provider=='GROQ'
    assert report['findings'][0]['sources']==[{'evidence_id':'e1','quote':records[0].content[:700]}]
    assert report['findings'][1]['sources'][0]['quote']==records[0].content[700:1400]


@pytest.mark.parametrize('refs',[['invented'],['e1'],['S999'],['S1','S1'],[None],{'S1':True}])
def test_analysis_rejects_unknown_duplicate_or_malformed_passage_refs(refs):
    raw=json.dumps({'findings':[{'category':'RECORDED','statement':'Untrusted model assertion remains unaccepted.','source_refs':refs}]})
    with pytest.raises(AnalysisValidationError) as error:run(raw,[record()])
    assert error.value.diagnostic['code']=='SOURCE_REFS'
    assert error.value.rejected_output==raw
    assert 'Untrusted model assertion' not in str(error.value)


def test_two_passages_from_one_record_cannot_create_a_conflict():
    raw=json.dumps({'findings':[{'category':'CONFLICT','statement':'These sources allegedly contradict each other.','source_refs':['S1','S2']}]})
    with pytest.raises(AnalysisValidationError) as error:run(raw,[record(content='One source only. '*100)])
    assert error.value.diagnostic['code']=='CONFLICT_SOURCES'


def test_provider_json_validation_failure_remains_safe_and_is_not_silently_retried():
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(400,json={'error':{'code':'json_validate_failed','failed_generation':'PRIVATE rejected text'}})
    case=SimpleNamespace(reason='INQUIRY',amount_cents=1000,currency='USD')
    with pytest.raises(ProviderHTTPError) as error:
        analyze_evidence(Settings(ai_provider='groq',groq_key='test'),case,[record()],httpx.MockTransport(handler))
    assert len(calls)==1 and 'PRIVATE' not in str(error.value)
