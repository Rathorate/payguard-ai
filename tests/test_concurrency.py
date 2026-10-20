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

