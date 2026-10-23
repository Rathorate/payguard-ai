import json
from types import SimpleNamespace
import pytest
from app.draft_output import render_draft
from app.providers import ProviderError
from app.providers import generate_draft
from app.config import Settings
import httpx
from conftest import first_case


def draft(gap):
    return json.dumps({'paragraphs':[{'text':'The merchant record states order B was delivered.','evidence_ids':['e1']}], 'missing_facts':[gap]})


@pytest.mark.parametrize('gap',[
    'No evidence of the buyer’s location at delivery time',
    'No proof of buyer’s presence at delivery address on Monday',
    "Provide the customer's whereabouts at delivery",
    'Obtain real-time GPS coordinates of the buyer',
    'Prove the buyer was present at the delivery address',
])
def test_whereabouts_requests_are_rejected_before_a_draft_can_be_saved(gap):
    with pytest.raises(ProviderError,match='unnecessary buyer whereabouts'):
        render_draft(draft(gap),[SimpleNamespace(id='e1')])


@pytest.mark.parametrize('gap',[
    'Independent carrier delivery confirmation is not supplied',
    'Existing redacted shipping records do not resolve the conflicting statements',
    'No buyer authorization record is provided',
])
def test_relevant_merchant_record_gaps_are_not_blocked(gap):
    assert gap in render_draft(draft(gap),[SimpleNamespace(id='e1')])


def test_privacy_rejection_preserves_saved_response_and_version(merchant,app):
    case=first_case(merchant);url='/api/v1/disputes/'+case['id']
    saved=merchant.put(url+'/draft',json={'version':case['version'],'text':'The existing merchant response remains available for review.'}).json()
    before=merchant.get(url).json()
    def generate(settings,item,records):
        raw=json.loads(draft('No proof of buyer’s presence at delivery address on Monday'))
        raw['paragraphs'][0]['evidence_ids']=[records[0].id]
        transport=httpx.MockTransport(lambda request:httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(raw)}}]}))
        return generate_draft(Settings(ai_provider='groq',groq_key='test'),item,records,transport)
    app.state.drafter=generate
    response=merchant.post(url+'/draft',json={'version':saved['version']})
    assert response.status_code==502 and 'unnecessary buyer whereabouts' in response.json()['detail']
    assert merchant.get(url).json()==before
