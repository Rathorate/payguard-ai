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
