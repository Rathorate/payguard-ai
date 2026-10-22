import json
from types import SimpleNamespace
import httpx
import pytest
from fastapi.testclient import TestClient
from conftest import first_case
from app.config import Settings
from app.providers import ProviderError
from app.review import analyze_evidence, citation_report, validate_analysis


def findings(records):
    return {'findings':[
        {'category':'RECORDED','statement':'A merchant receipt records the payment.','sources':[{'evidence_id':records[0].id,'quote':records[0].content[:35]}]},
        {'category':'MISSING','statement':'Delivery is not established by a payment receipt.','sources':[]}]}


def test_analysis_is_grounded_cached_versioned_and_never_approves(merchant,app):
    item=first_case(merchant);url='/api/v1/disputes/'+item['id'];calls=[]
    def reviewer(settings,case,records):
        calls.append(case.version)
        return findings(records),'GROQ'
    app.state.reviewer=reviewer
    initial=merchant.get(url+'/review').json()
    assert initial['analysis'] is None and initial['history']==[]
    response=merchant.post(url+'/analyze',json={'version':item['version']})
    assert response.status_code==200 and response.json()['source']=='GROQ'
    assert merchant.get(url).json()['status']=='OPEN'
    assert merchant.post(url+'/analyze',json={'version':item['version']}).status_code==200
    assert calls==[item['version']]
    assert merchant.get(url+'/review').json()['analysis']['report']['findings'][0]['sources']
    draft=merchant.post(url+'/draft',json={'version':item['version']}).json()
    assert merchant.get(url+'/review').json()['analysis'] is None
    assert merchant.post(url+'/analyze',json={'version':item['version']}).status_code==409
    assert merchant.post(url+'/analyze',json={'version':draft['version']}).status_code==200
    assert merchant.get(url).json()['status']=='REVIEW'


def test_original_generation_human_edit_approval_and_withdrawal_are_retained(merchant):
    item=first_case(merchant);url='/api/v1/disputes/'+item['id']
    generated=merchant.post(url+'/draft',json={'version':item['version']}).json()
    edited=merchant.put(url+'/draft',json={'version':generated['version'],'text':'Human correction: the receipt does not demonstrate delivery.'}).json()
    approved=merchant.post(url+'/approve',json={'version':edited['version'],'reviewed':True}).json()
    review=merchant.get(url+'/review').json()
    assert review['latest_generated']['text']==generated['draft']
    assert [r['action'] for r in review['history']]==['APPROVED','EDITED','GENERATED']
    assert review['history'][0]['text']==edited['draft']
    assert review['history'][0]['actor']==merchant.get('/api/v1/auth/me').json()['email']
    assert review['history'][0]['case_version']==approved['version']
    assert merchant.put(url+'/draft',json={'version':edited['version'],'text':'Stale edit must never create a saved revision.'}).status_code==409
    assert len(merchant.get(url+'/review').json()['history'])==3
    merchant.post(url+'/request-changes',json={'version':approved['version']})
    assert merchant.get(url+'/review').json()['history'][0]['action']=='WITHDRAWN'


def test_review_is_private_and_has_csrf_protection(merchant,app):
    item=first_case(merchant);url='/api/v1/disputes/'+item['id']
    assert merchant.post(url+'/analyze',json={'version':item['version']},headers={'X-CSRF-Token':'bad'}).status_code==403
    assert merchant.get(url+'/review').headers['cache-control']=='no-store'
    with TestClient(app) as other:
        assert other.get(url+'/review').status_code==401
        login=other.post('/api/v1/auth/demo').json();other.headers['X-CSRF-Token']=login['csrf']
        assert other.get(url+'/review').status_code==404
        assert other.post(url+'/analyze',json={'version':item['version']}).status_code==404


def test_hallucinated_analysis_cannot_be_saved(merchant,app):
    item=first_case(merchant);url='/api/v1/disputes/'+item['id']
    app.state.reviewer=lambda settings,case,records:({'findings':[{'category':'RECORDED','statement':'Delivery is verified.','sources':[{'evidence_id':records[0].id,'quote':'Fake carrier verification'}]}]},'GROQ')
    assert merchant.post(url+'/analyze',json={'version':item['version']}).status_code==502
    assert merchant.get(url+'/review').json()['analysis'] is None
    assert merchant.get(url).json()['status']=='OPEN'


def test_evidence_change_during_review_discards_stale_result(merchant,app):
    item=first_case(merchant);url='/api/v1/disputes/'+item['id']
    def reviewer(settings,case,records):
        from sqlalchemy import update
        from app.models import Dispute
        with app.state.sessions() as db:
            db.execute(update(Dispute).where(Dispute.id==case.id).values(version=case.version+1))
            db.commit()
        return findings(records),'GROQ'
    app.state.reviewer=reviewer
    assert merchant.post(url+'/analyze',json={'version':item['version']}).status_code==409
    assert merchant.get(url+'/review').json()['analysis'] is None


def test_citations_do_not_confuse_existence_with_truth():
    records=[SimpleNamespace(id='e1',content='Merchant says delivered.')]
    report=citation_report('Merchant says delivered [e1].\n\nDelivery independently verified [fake].\n\nMissing facts.',records)
    assert report['paragraphs'][0]['evidence_ids']==['e1']
    assert report['unknown_ids']==['fake'] and report['uncited_paragraphs']==2
    assert 'does not verify' in report['notice']


def test_unknown_references_block_approval_and_legacy_submission(merchant,app):
    item=first_case(merchant);url='/api/v1/disputes/'+item['id']
    draft=merchant.put(url+'/draft',json={'version':item['version'],'text':'Merchant claims a recorded payment [invented-source].'}).json()
    assert merchant.post(url+'/approve',json={'version':draft['version'],'reviewed':True}).status_code==422
    assert merchant.get(url).json()['status']=='REVIEW'
    from sqlalchemy import update
    from app.models import Dispute
    with app.state.sessions() as db:
        db.execute(update(Dispute).where(Dispute.id==item['id']).values(status='APPROVED'))
        db.commit()
    response=merchant.post(url+'/submit',json={'version':draft['version'],'confirmed':True},headers={'Idempotency-Key':'legacy-unknown-citation'})
    assert response.status_code==422
    assert merchant.get('/api/v1/submissions').json()['items']==[]


def test_export_rejects_a_case_changed_while_packet_is_assembled(merchant,app,monkeypatch):
    import app.main as main
    from sqlalchemy import update
    from app.models import Dispute
    item=first_case(merchant);url='/api/v1/disputes/'+item['id']
    draft=merchant.post(url+'/draft',json={'version':item['version']}).json()
    approved=merchant.post(url+'/approve',json={'version':draft['version'],'reviewed':True}).json()
    original=main.evidence_for;changed=[]
    def change_during_read(db,tenant,identity):
        records=original(db,tenant,identity)
        if not changed:
            changed.append(True)
            with app.state.sessions() as other:
                other.execute(update(Dispute).where(Dispute.id==identity).values(version=approved['version']+1,status='REVIEW'))
                other.commit()
        return records
    monkeypatch.setattr(main,'evidence_for',change_during_read)
    assert merchant.get(url+'/export',params={'version':approved['version']}).status_code==409


@pytest.mark.parametrize('change',[
    lambda r:r.update(extra='unexpected'),
    lambda r:r.update(findings=[]),
    lambda r:r['findings'][0].update(category='WIN_PROBABILITY'),
    lambda r:r['findings'][0].update(sources=[]),
    lambda r:r['findings'][0]['sources'][0].update(evidence_id='unknown'),
    lambda r:r['findings'][0]['sources'][0].update(quote='not actually in evidence'),
    lambda r:r['findings'][0].update(category='CONFLICT'),
    lambda r:r['findings'][0].update(statement=123),
    lambda r:r['findings'][0].update(sources=[None]),
])
def test_rejects_unsupported_findings(change):
    records=[SimpleNamespace(id='e1',content='Recorded payment of ten dollars in merchant invoice.')]
    report=findings(records);change(report)
    with pytest.raises(ProviderError):validate_analysis(json.dumps(report),records)


def test_groq_review_contract_and_offline_fallback():
    records=[SimpleNamespace(id='e1',title='Receipt',content='Recorded payment of ten dollars in merchant invoice.')]
    case=SimpleNamespace(reason='INQUIRY',amount_cents=1000,currency='USD')
    def handler(request):
        body=json.loads(request.content)
        assert 'untrusted' in body['messages'][0]['content']
        assert json.loads(body['messages'][1]['content'])['evidence'][0]['id']=='e1'
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(findings(records))}}]})
    report,source=analyze_evidence(Settings(ai_provider='groq',groq_key='test'),case,records,httpx.MockTransport(handler))
    assert source=='GROQ' and len(report['findings'])==2
    with pytest.raises(ProviderError):analyze_evidence(Settings(ai_provider='template'),case,records)


def test_finding_can_identify_conflicting_exact_sources():
    records=[SimpleNamespace(id='e1',content='Delivery was completed Monday.'),SimpleNamespace(id='e2',content='Delivery was not completed Monday.')]
    report={'findings':[{'category':'CONFLICT','statement':'Delivery statements conflict.','sources':[{'evidence_id':r.id,'quote':r.content} for r in records]}]}
    assert validate_analysis(json.dumps(report),records)==report


def test_analysis_no_evidence_rate_limits_and_locked_case(merchant,app,frozen_app_clock):
    item=first_case(merchant);url='/api/v1/disputes/'+item['id']
    app.state.reviewer=lambda settings,case,records:(findings(records),'GROQ')
    for _ in range(5):
        result=merchant.post(url+'/analyze',json={'version':item['version']})
        assert result.status_code==200
        # Advance a case version to request a new, uncached review.
        item=merchant.put(url+'/draft',json={'version':item['version'],'text':'Merchant states payment exists; delivery is not established.'}).json()
    assert merchant.post(url+'/analyze',json={'version':item['version']}).status_code==429
    from sqlalchemy import update
    from app.models import Dispute
    with app.state.sessions() as db:
        db.execute(update(Dispute).where(Dispute.id==item['id']).values(status='RESOLVED'))
        db.commit()
    assert merchant.post(url+'/analyze',json={'version':item['version']}).status_code==409


@pytest.mark.parametrize('text',['not json','```json\n{}\n```','null','[]','{"findings": null}'])
def test_invalid_model_json_fails_closed(text):
    with pytest.raises(ProviderError):validate_analysis(text,[])
