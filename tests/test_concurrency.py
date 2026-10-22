from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from conftest import first_case


def test_simultaneous_edits_only_one_wins(merchant, app):
    item=first_case(merchant)
    url='/api/v1/disputes/'+item['id']+'/draft'
    cookie=merchant.cookies.get('pg_session')
    csrf=merchant.headers['X-CSRF-Token']
    def edit(index):
        with TestClient(app) as client:
            client.cookies.set('pg_session',cookie)
            return client.put(url,headers={'X-CSRF-Token':csrf},json={'version':item['version'],'text':f'Merchant response number {index} backed by the attached order records.'}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        codes=list(pool.map(edit,[1,2]))
    assert sorted(codes)==[200,409]


def test_simultaneous_submissions_only_one_intent(merchant, app):
    item = first_case(merchant)
    url = '/api/v1/disputes/' + item['id']
    draft = merchant.post(url+'/draft', json={'version':item['version']}).json()
    approved = merchant.post(url+'/approve', json={'version':draft['version'],'reviewed':True}).json()
    cookie, csrf = merchant.cookies.get('pg_session'), merchant.headers['X-CSRF-Token']
    def submit(index):
        with TestClient(app) as client:
            client.cookies.set('pg_session', cookie)
            return client.post(url+'/submit', headers={'X-CSRF-Token':csrf,'Idempotency-Key':f'concurrent-submit-{index}'}, json={'version':approved['version'],'confirmed':True}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = list(pool.map(submit, [1,2]))
    assert sorted(codes) == [200,409]
    assert len(merchant.get('/api/v1/submissions').json()['items']) == 1
