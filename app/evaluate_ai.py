"""Synthetic, read-only AI rehearsal. Never reads customer cases or submits evidence."""
import argparse
import json
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from .config import Settings
from .providers import ProviderError, generate_draft
from .review import AnalysisValidationError, analyze_evidence, citation_report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='.artifacts/ai-evaluation.json')
    args=parser.parse_args()
    settings=Settings()
    if not settings.ai_status()['ai_configured']:
        parser.exit(1,'Configure Groq or OpenAI on the backend first. No request sent.\n')
    cases=json.loads((Path(__file__).resolve().parents[1]/'docs/evaluation-cases.json').read_text())
    results=[]
    print('Running four synthetic cases (eight AI calls). No customer data, approval or PayPal requests.',flush=True)
    for case in cases:
        start=perf_counter()
        item=SimpleNamespace(paypal_id='SYNTHETIC-'+case['name'],**{k:case[k] for k in ('reason','amount_cents','currency')})
        records=[SimpleNamespace(**e) for e in case['evidence']]
        result={'case':case['name'],'human_checks':case['human_checks'],'human_pass':None,'human_notes':'','evidence':case['evidence']}
        try:
            text,source=generate_draft(settings,item,records)
            result.update(draft=text,source=source,citations=citation_report(text,records))
            report,_=analyze_evidence(settings,item,records)
            result['analysis']=report
            result['mechanical_checks_passed']=not result['citations']['unknown_ids']
        except ProviderError as exc:
            result.update(error=str(exc),mechanical_checks_passed=False)
            if isinstance(exc, AnalysisValidationError):
                # This CLI uses only the fixed synthetic fixture file. Never expose
                # rejected customer-case output through API errors or server logs.
                result.update(analysis_validation=exc.diagnostic, rejected_analysis=exc.rejected_output)
        result['elapsed_seconds']=round(perf_counter()-start,2)
        results.append(result)
        print(case['name']+': '+('mechanical checks passed; human assessment pending' if result['mechanical_checks_passed'] else result.get('error','Unknown citations found')),flush=True)
    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({'notice':'Synthetic evaluation only. Exact excerpts and known references do not establish factual entailment. Human ratings are pending.','provider':settings.drafting_provider,'model':settings.ai_status()['ai_model'],'results':results},indent=2)+'\n')
    print('Saved '+str(output)+'. Review each human checklist; no accuracy or time-saving claim has been calculated.')
    if not all(r['mechanical_checks_passed'] for r in results):
        parser.exit(1,'Some checks failed; inspect the saved report before presenting results.\n')


if __name__=='__main__':main()
