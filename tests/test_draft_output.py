import json
from types import SimpleNamespace
import httpx
import pytest
from app.config import Settings
from app.providers import ProviderError, generate_draft
from app.draft_output import render_draft


RECORDS=[SimpleNamespace(id='E-RECEIPT',title='Receipt',content='Merchant records a payment only.')]


def report():
    return {'paragraphs':[{'text':'Merchant records a payment; delivery is not established.',
                           'evidence_ids':['E-RECEIPT']}],
            'missing_facts':['A delivery record is not provided.']}


@pytest.mark.parametrize('model',['openai/gpt-oss-20b','llama-3.3-70b-versatile'])
def test_groq_draft_source_ids_render_as_exact_clickable_references(model):
    def handler(request):
        body=json.loads(request.content)
        if model=='openai/gpt-oss-20b':
            assert body['response_format']['json_schema']['strict'] is True
            assert body['reasoning_effort']=='low' and body['reasoning_format']=='hidden'
            paragraph=body['response_format']['json_schema']['schema']['properties']['paragraphs']['items']
            assert paragraph['properties']['evidence_ids']['items']['enum']==['E-RECEIPT']
        else:
            assert body['response_format']['type']=='json_object'
            assert 'reasoning_effort' not in body
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(report())}}]})
    case=SimpleNamespace(paypal_id='PP-R-TEST',reason='INQUIRY',amount_cents=1000,currency='USD')
    text,source=generate_draft(Settings(ai_provider='groq',groq_key='test',groq_model=model),case,RECORDS,httpx.MockTransport(handler))
    assert source=='GROQ' and text.startswith(report()['paragraphs'][0]['text']+' [E-RECEIPT]')
    assert text.endswith('Evidence gaps:\n- A delivery record is not provided.')


@pytest.mark.parametrize('change',[
    lambda r:r.update(extra='unknown'),
    lambda r:r.update(paragraphs=[]),
    lambda r:r['paragraphs'][0].update(evidence_ids=[]),
    lambda r:r['paragraphs'][0].update(evidence_ids=['invented']),
    lambda r:r['paragraphs'][0].update(evidence_ids=['E-RECEIPT','E-RECEIPT']),
    lambda r:r['paragraphs'][0].update(text='An invented statement [invented]'),
    lambda r:r.update(missing_facts=['x']),
])
def test_invalid_structured_drafts_are_not_repaired_or_accepted(change):
    data=report();change(data)
    with pytest.raises(ProviderError,match='no draft was changed'):
        render_draft(json.dumps(data),RECORDS)


def test_structured_draft_rejects_duplicate_keys_and_plain_text():
    for raw in ['Merchant response without declared source IDs.',
                '{"paragraphs":[],"paragraphs":[],"missing_facts":[]}']:
        with pytest.raises(ProviderError):render_draft(raw,RECORDS)
