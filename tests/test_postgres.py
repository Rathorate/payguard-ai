"""Runs in CI with a disposable PostgreSQL database; never point at production."""
import os
import pytest
from sqlalchemy import select
from app.models import Base, Tenant, database


@pytest.mark.skipif(not os.getenv('TEST_POSTGRES_URL'), reason='No disposable PostgreSQL provided')
def test_postgres_schema_transaction():
    engine,sessions=database(os.environ['TEST_POSTGRES_URL'])
    Base.metadata.create_all(engine)
    with sessions() as db:
        tenant=Tenant(name='postgres-smoke-test');db.add(tenant);db.flush()
        assert db.scalar(select(Tenant).where(Tenant.id==tenant.id)).name=='postgres-smoke-test'
        db.rollback()
    engine.dispose()


@pytest.mark.skipif(not os.getenv('TEST_POSTGRES_URL'), reason='No disposable PostgreSQL provided')
def test_postgres_registration_preserves_long_audit_actor():
    import uuid
    from fastapi.testclient import TestClient
    from app.config import Settings
    from app.main import create_app
    from app.models import Audit
    app = create_app(Settings(database_url=os.environ['TEST_POSTGRES_URL'],demo=False,secure_cookies=True,origin='https://testserver'))
    Base.metadata.create_all(app.state.engine)
    email = 'merchant-' + uuid.uuid4().hex + '-' + 'x'*100 + '@example.invalid'
    with TestClient(app,base_url='https://testserver') as client:
        response = client.post('/api/v1/auth/register',json={'email':email,'password':'a-long-test-password','company':'Postgres audit fixture'})
        assert response.status_code == 201
        assert client.get('/api/v1/auth/me').json()['email'] == email
        with app.state.sessions() as db:
            recorded = db.scalar(select(Audit).where(Audit.tenant_id==response.json()['tenant_id'],Audit.action=='ACCOUNT_CREATED'))
            assert recorded.actor == email
        # Exercise new revision tables with the same accepted long actor value.
        import time
        client.headers.update({'X-CSRF-Token':response.json()['csrf'],'Origin':'https://testserver'})
        case=client.post('/api/v1/disputes',json={'paypal_id':'PG-'+uuid.uuid4().hex,'customer':'Synthetic buyer','reason':'INQUIRY','amount_cents':1000,'due_at':int(time.time())+3600}).json()
        url='/api/v1/disputes/'+case['id']
        evidence=client.post(url+'/evidence',json={'version':case['version'],'title':'Synthetic receipt','kind':'INVOICE','content':'Synthetic receipt records payment of ten dollars.'})
        assert evidence.status_code==201
        version=client.get(url).json()['version']
        draft=client.post(url+'/draft',json={'version':version})
        assert draft.status_code==200
        approved=client.post(url+'/approve',json={'version':draft.json()['version'],'reviewed':True})
        assert approved.status_code==200
        history=client.get(url+'/review').json()['history']
        assert [r['action'] for r in history]==['APPROVED','GENERATED']
        assert all(r['actor']==email for r in history)
        packet=client.get(url+'/export',params={'version':approved.json()['version']})
        assert packet.status_code==200 and len(packet.json()['review']['history'])==2
