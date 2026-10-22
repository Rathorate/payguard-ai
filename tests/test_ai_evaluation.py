import json
import sys
import pytest
from app import evaluate_ai
from app.config import Settings
from app.providers import ProviderError
from app.review import AnalysisValidationError


def test_synthetic_evaluation_retains_failures_and_pending_human_assessment(tmp_path,monkeypatch):
    output=tmp_path/'report.json';seen=[]
    monkeypatch.setattr(evaluate_ai,'Settings',lambda:Settings(ai_provider='groq',groq_key='test'))
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
