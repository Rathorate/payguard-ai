import json
import sys
import pytest
from app import evaluate_ai
from app.config import Settings
from app.providers import ProviderError, ProviderHTTPError
from app.review import AnalysisValidationError


@pytest.fixture(autouse=True)
def no_real_quota_wait(monkeypatch):
    monkeypatch.setattr(evaluate_ai,'sleep',lambda seconds:None)


def test_synthetic_evaluation_retains_failures_and_pending_human_assessment(tmp_path,monkeypatch):
    output=tmp_path/'report.json';seen=[]
    monkeypatch.setattr(evaluate_ai,'Settings',lambda:Settings(ai_provider='groq',groq_key='test',groq_schema_recovery=True))
    def draft(settings,case,records):
        seen.append(case.paypal_id)
        return 'Synthetic merchant response ['+records[0].id+'].','GROQ'
    def review(settings,case,records):
        if case.paypal_id.endswith('untrusted-instructions'):raise ProviderError('Synthetic provider failure')
        return {'findings':[{'category':'MISSING','statement':'Human assessment required.','sources':[]}]},'GROQ'
    monkeypatch.setattr(evaluate_ai,'generate_draft',draft)
    monkeypatch.setattr(evaluate_ai,'analyze_evidence',review)
    monkeypatch.setattr(sys,'argv',['evaluate-ai','--output',str(output)])
    with pytest.raises(SystemExit) as exit_info:evaluate_ai.main()
    assert exit_info.value.code==1
    report=json.loads(output.read_text())
    assert len(seen)==4 and all(s.startswith('SYNTHETIC-') for s in seen)
    assert len(report['results'])==4
    assert report['task_invocations']==report['ai_calls'] and report['schema_recovery_enabled']
    assert report['maximum_provider_requests']==report['task_invocations']*2
    assert all(r['human_pass'] is None for r in report['results'])
    assert report['results'][-1]['mechanical_checks_passed'] is False
    assert report['results'][0]['mechanical_checks_passed'] is True


def test_evaluation_without_ai_configuration_sends_nothing(monkeypatch):
    monkeypatch.setattr(evaluate_ai,'Settings',lambda:Settings(ai_provider='template'))
    monkeypatch.setattr(sys,'argv',['evaluate-ai'])
    monkeypatch.setattr(evaluate_ai,'generate_draft',lambda *a:pytest.fail('Unexpected provider call'))
    with pytest.raises(SystemExit) as exit_info:evaluate_ai.main()
    assert exit_info.value.code==1


def test_synthetic_report_retains_rejected_output_and_validation_reason(tmp_path,monkeypatch):
    output=tmp_path/'report.json'
    monkeypatch.setattr(evaluate_ai,'Settings',lambda:Settings(ai_provider='groq',groq_key='test'))
    monkeypatch.setattr(evaluate_ai,'generate_draft',lambda settings,case,records:('Merchant response ['+records[0].id+'].','GROQ'))
    def review(*args):
        raise AnalysisValidationError('QUOTE_MISMATCH','$.findings[0].sources[0]','synthetic rejected quotation')
    monkeypatch.setattr(evaluate_ai,'analyze_evidence',review)
    monkeypatch.setattr(sys,'argv',['evaluate-ai','--output',str(output)])
    with pytest.raises(SystemExit):evaluate_ai.main()
    results=json.loads(output.read_text())['results']
    assert all(r['rejected_analysis']=='synthetic rejected quotation' for r in results)
    assert all(r['analysis_validation']['code']=='QUOTE_MISMATCH' for r in results)
    assert all(r['mechanical_checks_passed'] is False and r['human_pass'] is None for r in results)


@pytest.mark.parametrize('failed_stage',['draft','analysis'])
def test_single_scenario_diagnostic_records_stage_and_is_not_a_full_pass(tmp_path,monkeypatch,failed_stage):
    output=tmp_path/'diagnostic.json';calls=[]
    monkeypatch.setattr(evaluate_ai,'Settings',lambda:Settings(ai_provider='groq',groq_key='test'))
    def fail():
        raise ProviderHTTPError('Safe synthetic HTTP failure',{'status':400,'code':'json_validate_failed'})
    def draft(settings,case,records):
        calls.append(('draft',case.paypal_id))
        if failed_stage=='draft':fail()
        return 'Recorded payment ['+records[0].id+'].','GROQ'
    def analysis(settings,case,records):
        calls.append(('analysis',case.paypal_id));fail()
    monkeypatch.setattr(evaluate_ai,'generate_draft',draft)
    monkeypatch.setattr(evaluate_ai,'analyze_evidence',analysis)
    monkeypatch.setattr(sys,'argv',['evaluate-ai','--case','authorization-missing','--output',str(output)])
    with pytest.raises(SystemExit):evaluate_ai.main()
    report=json.loads(output.read_text());result=report['results'][0]
    assert report['evaluation_scope']=='single_scenario' and len(report['results'])==1
    assert result['failed_stage']==failed_stage and result['mechanical_checks_passed'] is False
    assert result['provider_diagnostic']['code']=='json_validate_failed'
    assert all(identity=='SYNTHETIC-authorization-missing' for _,identity in calls)
    assert len(calls)==(1 if failed_stage=='draft' else 2)


@pytest.mark.parametrize('reference,expected',[
    ('(E-RECEIPT)',['NO_LINKED_DRAFT_SOURCE']),
    ('(E\u2011RECEIPT)',['NO_LINKED_DRAFT_SOURCE']),
    ('',['NO_LINKED_DRAFT_SOURCE']),
    ('[invented]',['UNKNOWN_DRAFT_CITATIONS','NO_LINKED_DRAFT_SOURCE']),
    ('[E-RECEIPT]',[]),
])
def test_evaluation_distinguishes_linked_citations_from_parentheses_or_no_references(tmp_path,monkeypatch,reference,expected):
    output=tmp_path/'citation-report.json'
    monkeypatch.setattr(evaluate_ai,'Settings',lambda:Settings(ai_provider='groq',groq_key='test'))
    monkeypatch.setattr(evaluate_ai,'generate_draft',lambda *args:('Merchant records payment '+reference+'.','GROQ'))
    monkeypatch.setattr(evaluate_ai,'analyze_evidence',lambda *args:({'findings':[
        {'category':'MISSING','statement':'Delivery is not established.','sources':[]}]},'GROQ'))
    monkeypatch.setattr(sys,'argv',['evaluate-ai','--case','receipt-only','--output',str(output)])
    if expected:
        with pytest.raises(SystemExit) as info:evaluate_ai.main()
        assert info.value.code==1
    else:
        evaluate_ai.main()
    result=json.loads(output.read_text())['results'][0]
    assert result['mechanical_failures']==expected
    assert result['mechanical_checks_passed'] is (not expected)
    assert result['human_pass'] is None


def test_evaluation_paces_requests_and_stops_after_rate_limit(tmp_path,monkeypatch):
    output=tmp_path/'limited.json';pauses=[];calls=[]
    monkeypatch.setattr(evaluate_ai,'sleep',pauses.append)
    monkeypatch.setattr(evaluate_ai,'Settings',lambda:Settings(ai_provider='groq',groq_key='test'))
    def draft(settings,case,records):
        calls.append('draft')
        return 'Merchant receipt records payment ['+records[0].id+'].','GROQ'
    def review(*args):
        calls.append('analysis')
        raise ProviderHTTPError('Groq quota reached',{'status':429,'retry_after_seconds':60})
    monkeypatch.setattr(evaluate_ai,'generate_draft',draft)
    monkeypatch.setattr(evaluate_ai,'analyze_evidence',review)
    monkeypatch.setattr(sys,'argv',['evaluate-ai','--output',str(output)])
    with pytest.raises(SystemExit):evaluate_ai.main()
    report=json.loads(output.read_text())
    assert calls==['draft','analysis'] and pauses==[35]
    assert report['ai_calls']==2 and len(report['results'])==4
    assert all(r['failed_stage']=='not_run' for r in report['results'][1:])
    assert all(not r['mechanical_checks_passed'] for r in report['results'])
