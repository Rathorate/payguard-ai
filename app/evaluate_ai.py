"""Synthetic, read-only AI rehearsal. Never reads customer cases or submits evidence."""
import argparse
import json
from pathlib import Path
from time import perf_counter, sleep
from types import SimpleNamespace
from .config import Settings
from .providers import ProviderError, ProviderHTTPError, generate_draft
from .review import AnalysisValidationError, analyze_evidence, citation_report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='.artifacts/ai-evaluation.json')
    parser.add_argument('--pause-seconds',type=int,choices=range(0,61),default=35,
                        metavar='0..60',help='Pause between AI requests (default 35 seconds).')
    cases=json.loads((Path(__file__).resolve().parents[1]/'docs/evaluation-cases.json').read_text())
    parser.add_argument('--case', choices=[case['name'] for case in cases],
                        help='Diagnose one scenario only; this is not a full evaluation.')
    args=parser.parse_args()
    settings=Settings()
    if not settings.ai_status()['ai_configured']:
        parser.exit(1,'Configure Groq or OpenAI on the backend first. No request sent.\n')
    if args.case:
        cases=[case for case in cases if case['name']==args.case]
    results=[]
    call_count=0
    rate_limited=False
    def invoke(stage, function, *values):
        nonlocal call_count
        if call_count and args.pause_seconds:
            print(f'Waiting {args.pause_seconds}s before {stage} to reduce quota pressure…',flush=True)
            sleep(args.pause_seconds)
        call_count+=1
        return function(*values)
    print(f'Running {len(cases)} synthetic cases (up to {len(cases)*2} AI calls). No customer data, approval or PayPal requests.',flush=True)
    for case in cases:
        start=perf_counter()
        item=SimpleNamespace(paypal_id='SYNTHETIC-'+case['name'],**{k:case[k] for k in ('reason','amount_cents','currency')})
        records=[SimpleNamespace(**e) for e in case['evidence']]
        result={'case':case['name'],'human_checks':case['human_checks'],'human_pass':None,'human_notes':'','evidence':case['evidence']}
        if rate_limited:
            result.update(error='Not run: an earlier request hit the provider quota. Resume only after the limit resets.',
                          failed_stage='not_run',mechanical_checks_passed=False,elapsed_seconds=0)
            results.append(result)
            print(case['name']+': '+result['error'],flush=True)
            continue
        stage='draft'
        try:
            text,source=invoke('draft',generate_draft,settings,item,records)
            result.update(draft=text,source=source,citations=citation_report(text,records))
            stage='analysis'
            report,_=invoke('analysis',analyze_evidence,settings,item,records)
            result['analysis']=report
            failures=[]
            if result['citations']['unknown_ids']:
                failures.append('UNKNOWN_DRAFT_CITATIONS')
            if records and not any(p['evidence_ids'] for p in result['citations']['paragraphs']):
                failures.append('NO_LINKED_DRAFT_SOURCE')
            result['mechanical_failures']=failures
            result['mechanical_checks_passed']=not failures
            if failures:
                result.update(failed_stage='draft_citations',error='Draft citation checks failed: '+', '.join(failures))
        except ProviderError as exc:
            result.update(error=str(exc),failed_stage=stage,mechanical_checks_passed=False)
            if isinstance(exc, ProviderHTTPError):
                result['provider_diagnostic']=exc.diagnostic
                rate_limited=exc.diagnostic.get('status')==429
            if isinstance(exc, AnalysisValidationError):
                # This CLI uses only the fixed synthetic fixture file. Never expose
                # rejected customer-case output through API errors or server logs.
                result.update(analysis_validation=exc.diagnostic, rejected_analysis=exc.rejected_output)
        result['elapsed_seconds']=round(perf_counter()-start,2)
        results.append(result)
        failure=(('['+result['failed_stage']+'] ') if result.get('failed_stage') else '')+result.get('error','Unknown citations found')
        print(case['name']+': '+('mechanical checks passed; human assessment pending' if result['mechanical_checks_passed'] else failure),flush=True)
    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({'notice':'Synthetic evaluation only. Exact excerpts and known references do not establish factual entailment. Human ratings are pending.',
        'evaluation_scope':'single_scenario' if args.case else 'full_suite',
        'ai_calls':call_count,'pause_seconds':args.pause_seconds,
        'provider':settings.drafting_provider,'model':settings.ai_status()['ai_model'],'results':results},indent=2)+'\n')
    print('Saved '+str(output)+'. Review each human checklist; no accuracy or time-saving claim has been calculated.')
    if not all(r['mechanical_checks_passed'] for r in results):
        parser.exit(1,'Some checks failed; inspect the saved report before presenting results.\n')


if __name__=='__main__':main()
