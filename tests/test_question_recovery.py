import json
from types import SimpleNamespace
import pytest
from conftest import first_case
from app.config import Settings
from app.providers import ProviderError, ProviderHTTPError
from app.questions import answer_question, validate_answer


def test_invalid_completed_answer_gets_one_fresh_validated_attempt(monkeypatch):
    records=[SimpleNamespace(id='private-record-id',title='Receipt',content='Synthetic receipt records payment only.')]
    case=SimpleNamespace(paypal_id='PP-D-TEST',reason='INQUIRY',amount_cents=1000,currency='USD')
    calls=[]
    def generate(settings,instructions,payload,*args,**kwargs):
        body=json.loads(payload)
        assert set(body['source_passages'][0]) == {'ref','title','quote'}
        assert body['source_passages'][0]['ref'] == 'S1'
        calls.append(instructions)
        ref='invented-private-output' if len(calls)==1 else 'S1'
        return json.dumps({'findings':[{'category':'RECORDED','statement':'The receipt records payment only.','source_refs':[ref]}]}),'GROQ'
    monkeypatch.setattr('app.questions.generate_text',generate)
    report,source=answer_question(Settings(ai_provider='groq'),case,records,'What does this establish?',[])
    assert source=='GROQ' and len(calls)==2
    assert 'previous response failed' in calls[1]
    assert 'invented-private-output' not in calls[1]
    assert report['findings'][0]['sources']==[{'evidence_id':'private-record-id','quote':records[0].content}]


def test_repeated_invalid_answers_fail_closed_without_changing_case(merchant,app,monkeypatch,caplog):
    item=first_case(merchant);url='/api/v1/disputes/'+item['id'];before=merchant.get(url).json();calls=[]
    app.state.settings.ai_provider='groq'
    def invalid(*args,**kwargs):
        calls.append(1)
        return json.dumps({'findings':[{'category':'RECORDED','statement':'Untrusted generated text marker.','source_refs':['invented-ref']}]}),'GROQ'
    monkeypatch.setattr('app.questions.generate_text',invalid)
    response=merchant.post(url+'/questions',json={'version':item['version'],'question':'Does this prove delivery?'})
    assert response.status_code==502 and len(calls)==2
    assert merchant.get(url).json()==before
    assert 'Untrusted generated text marker' not in response.text+caplog.text
    assert merchant.get('/api/v1/submissions').json()['items']==[]


@pytest.mark.parametrize('failure',[ProviderHTTPError('Quota exceeded',{'status':429}),ProviderError('Provider timed out')])
def test_provider_failures_do_not_trigger_answer_validation_retry(monkeypatch,failure):
    calls=[]
    def unavailable(*args,**kwargs):
        calls.append(1)
        raise failure
    monkeypatch.setattr('app.questions.generate_text',unavailable)
    case=SimpleNamespace(paypal_id='PP-D-TEST',reason='INQUIRY',amount_cents=1000,currency='USD')
    records=[SimpleNamespace(id='e1',title='Receipt',content='Synthetic payment record only.')]
    with pytest.raises(ProviderError):
        answer_question(Settings(ai_provider='groq'),case,records,'What is missing?',[])
    assert len(calls)==1


def test_payment_receipt_cannot_be_returned_as_recorded_authorization(monkeypatch):
    records=[SimpleNamespace(id='e1',title='Receipt',content='Synthetic receipt records a payment of ten dollars only.')]
    case=SimpleNamespace(paypal_id='PP-D-TEST',reason='INQUIRY',amount_cents=1000,currency='USD')
    calls=[]
    def generate(settings,instructions,*args,**kwargs):
        calls.append(instructions)
        statement='The payment was authorized and recorded.' if len(calls)==1 else 'The receipt records a payment only.'
        return json.dumps({'findings':[{'category':'RECORDED','statement':statement,'source_refs':['S1']}]}),'GROQ'
    monkeypatch.setattr('app.questions.generate_text',generate)
    report,_=answer_question(Settings(ai_provider='groq'),case,records,'What does this prove?',[])
    assert len(calls)==2 and 'does not establish authorization' in calls[1]
    assert report['findings'][0]['statement']=='The receipt records a payment only.'


def test_authorization_uncertainty_is_allowed_but_not_an_unsourced_recorded_fact():
    records=[SimpleNamespace(id='e1',title='Receipt',content='Synthetic payment receipt only.')]
    report={'findings':[{'category':'MISSING','statement':'Authorization is not established by this payment receipt.','sources':[]}]}
    assert validate_answer(report,records)==report
    report['findings'][0]={'category':'RECORDED','statement':'The payment was authorized.','sources':[{'evidence_id':'e1','quote':records[0].content}]}
    with pytest.raises(ProviderError,match='authorization absent'):
        validate_answer(report,records)
