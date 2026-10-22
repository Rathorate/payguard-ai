import io
import time
from reportlab.pdfgen import canvas
from app.providers import ProviderError
from conftest import first_case


def test_end_to_end_and_idempotency(merchant):
    case=first_case(merchant);url='/api/v1/disputes/'+case['id']
    assert merchant.post(url+'/approve',json={'version':case['version'],'reviewed':True}).status_code==409
    draft=merchant.post(url+'/draft',json={'version':case['version']}).json()
    assert draft['status']=='REVIEW' and draft['draft_source']=='TEMPLATE'
    assert 'not been independently verified' in draft['draft']
    assert merchant.post(url+'/approve',json={'version':draft['version'],'reviewed':False}).status_code==422
    approved=merchant.post(url+'/approve',json={'version':draft['version'],'reviewed':True}).json()
    headers={'Idempotency-Key':'submission-test-001'}
    body={'version':approved['version'],'confirmed':True}
    first=merchant.post(url+'/submit',json=body,headers=headers)
    assert first.status_code==200 and first.json()['state']=='SIMULATED'
    assert merchant.post(url+'/submit',json=body,headers=headers).json()==first.json()
    assert merchant.post(url+'/submit',json=body,headers={'Idempotency-Key':'different-test-key'}).status_code==409
    assert merchant.get(url).json()['status']=='SUBMITTED'
    assert merchant.post(url+'/draft',json={'version':approved['version']}).status_code==409
    actions=[row['action'] for row in merchant.get('/api/v1/audit').json()['items']]
    assert 'DRAFT_APPROVED' in actions and 'SUBMISSION_SIMULATED' in actions


def test_evidence_invalidates_approval_and_stale_edits(merchant):
    case=first_case(merchant);url='/api/v1/disputes/'+case['id']
    draft=merchant.post(url+'/draft',json={'version':case['version']}).json()
    assert merchant.put(url+'/draft',json={'version':case['version'],'text':'This is a stale draft edit with enough text.'}).status_code==409
    approved=merchant.post(url+'/approve',json={'version':draft['version'],'reviewed':True}).json()
    response=merchant.post(url+'/evidence',json={'version':approved['version'],'title':'Support correspondence','kind':'COMMUNICATION','content':'Customer contacted support requesting a replacement.'})
    assert response.status_code==201
    current=merchant.get(url).json()
    assert current['status']=='OPEN' and current['draft']==''
    assert merchant.post(url+'/submit',json={'version':approved['version'],'confirmed':True},headers={'Idempotency-Key':'stale-approval-key'}).status_code==409


def test_manual_edit_and_provider_failure(merchant,app):
    case=first_case(merchant);url='/api/v1/disputes/'+case['id']
    edit=merchant.put(url+'/draft',json={'version':case['version'],'text':'Merchant response supported by our recorded order invoice.'})
    assert edit.status_code==200 and edit.json()['draft_source']=='MERCHANT'
    def fail(*args):
        raise ProviderError('upstream unavailable')
    app.state.drafter=fail
    assert merchant.post(url+'/draft',json={'version':edit.json()['version']}).status_code==502
    assert merchant.get(url).json()['draft']==edit.json()['draft']


def new_case(merchant,**overrides):
    return merchant.post('/api/v1/disputes',json={'paypal_id':'PP-D-TEST','customer':'Test Customer','reason':'INQUIRY','amount_cents':1999,'due_at':int(time.time())+86400,**overrides})


def test_create_filter_pagination_validation(merchant):
    response=new_case(merchant)
    assert response.status_code==201
    assert new_case(merchant).status_code==409
    assert new_case(merchant,paypal_id='INVALID/../ID').status_code==422
    assert new_case(merchant,amount_cents=1.2).status_code==422
    assert merchant.get('/api/v1/disputes?limit=101').status_code==422
    assert merchant.get('/api/v1/disputes?page=0').status_code==422
    filtered=merchant.get('/api/v1/disputes?q=Test%20Customer&limit=1').json()
    assert filtered['total']==1 and len(filtered['items'])==1
    assert merchant.get('/api/v1/disputes?q=%25').json()['total']==0
    assert merchant.get('/api/v1/disputes?status=APPROVED').json()['items']==[]


def test_missing_evidence_and_deadline(merchant):
    case=new_case(merchant,due_at=int(time.time())-1).json();url='/api/v1/disputes/'+case['id']
    assert merchant.post(url+'/draft',json={'version':case['version']}).status_code==422
    evidence=merchant.post(url+'/evidence',json={'version':case['version'],'title':'Invoice','kind':'INVOICE','content':'Order paid in full.'})
    assert evidence.status_code==201
    current=merchant.get(url).json()
    draft=merchant.post(url+'/draft',json={'version':current['version']}).json()
    approved=merchant.post(url+'/approve',json={'version':draft['version'],'reviewed':True}).json()
    assert merchant.post(url+'/submit',json={'version':approved['version'],'confirmed':True},headers={'Idempotency-Key':'expired-deadline'}).status_code==409


def test_pdf_upload(merchant):
    case=first_case(merchant);url='/api/v1/disputes/'+case['id']
    buffer=io.BytesIO();pdf=canvas.Canvas(buffer);pdf.drawString(50,750,'Order 100: paid 129.00 USD. Merchant invoice record.');pdf.save()
    response=merchant.post(url+'/upload',data={'version':case['version']},files={'file':('invoice.pdf',buffer.getvalue(),'application/pdf')})
    assert response.status_code==201
    assert 'Order 100' in response.json()['content']
    current=merchant.get(url).json()
    assert merchant.post(url+'/upload',data={'version':current['version']},files={'file':('bad.pdf',b'bad','application/pdf')}).status_code==422
    blank=io.BytesIO();pdf=canvas.Canvas(blank);pdf.showPage();pdf.save()
    assert merchant.post(url+'/upload',data={'version':current['version']},files={'file':('blank.pdf',blank.getvalue(),'application/pdf')}).status_code==422


def test_security_headers_and_body_cap(client):
    response=client.get('/')
    assert response.status_code==200
    assert "script-src 'self'" in response.headers['content-security-policy']
    assert response.headers['x-content-type-options']=='nosniff'
    assert response.headers['x-frame-options']=='DENY'
    assert client.post('/api/v1/auth/login',content=b'x'*(6*1024*1024+1)).status_code==413


def test_unknown_submission_does_not_retry(merchant,app):
    case=first_case(merchant);url='/api/v1/disputes/'+case['id']
    draft=merchant.post(url+'/draft',json={'version':case['version']}).json()
    approved=merchant.post(url+'/approve',json={'version':draft['version'],'reviewed':True}).json()
    settings=app.state.settings;settings.demo=False;settings.paypal_tenant_id=approved['tenant_id']
    calls=[]
    def fail(*args):
        calls.append(1);raise ProviderError('timeout')
    app.state.paypal.details=lambda _: {'dispute_id':approved['paypal_id'],'reason':approved['reason'],
        'dispute_amount':{'value':str(approved['amount_cents']/100),'currency_code':approved['currency']},
        'seller_response_due_date':__import__('datetime').datetime.fromtimestamp(approved['due_at'],__import__('datetime').timezone.utc).isoformat(),
        'status':'WAITING_FOR_SELLER_RESPONSE','links':[{'rel':'provide-evidence','method':'POST',
        'href':app.state.paypal.base+'/v1/customer/disputes/'+approved['paypal_id']+'/provide-evidence'}]}
    app.state.paypal.submit=fail
    body={'version':approved['version'],'confirmed':True};headers={'Idempotency-Key':'ambiguous-submission'}
    assert merchant.post(url+'/submit',json=body,headers=headers).json()['state']=='UNKNOWN'
    assert merchant.post(url+'/submit',json=body,headers=headers).json()['state']=='UNKNOWN'
    assert len(calls)==1
    assert merchant.get(url).json()['status']=='SUBMISSION_UNKNOWN'

