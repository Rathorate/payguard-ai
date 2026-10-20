"""Business transitions shared by API and worker."""
import hashlib
import time
from fastapi import HTTPException
from sqlalchemy import select, update
from .models import Dispute, Evidence, Audit


TERMINAL = {'SUBMITTED', 'SUBMITTING', 'SUBMISSION_UNKNOWN', 'RESOLVED'}


def audit(db, tenant, actor, action, resource):
    db.add(Audit(tenant_id=tenant, actor=actor, action=action, resource_id=resource))


def get_dispute(db, tenant, identity):
    item = db.scalar(select(Dispute).where(Dispute.id == identity, Dispute.tenant_id == tenant))
    if item is None:
        raise HTTPException(404, 'Dispute not found')
    return item


def evidence_for(db, tenant, identity):
    return list(db.scalars(select(Evidence).where(Evidence.tenant_id == tenant, Evidence.dispute_id == identity).order_by(Evidence.created_at, Evidence.id)))


def transition(db, item, version, **values):
    result = db.execute(update(Dispute).where(Dispute.id == item.id, Dispute.tenant_id == item.tenant_id, Dispute.version == version).values(**values, version=version + 1))
    if result.rowcount != 1:
        raise HTTPException(409, 'This dispute changed. Refresh and review the latest version.')


def editable(item):
    if item.status in TERMINAL:
        raise HTTPException(409, 'Dispute is locked; reconcile pending submissions before further changes')


def add_evidence(db, tenant, actor, item, title, kind, content, version):
    editable(item)
    existing = evidence_for(db, tenant, item.id)
    if len(existing) >= 20 or sum(len(e.content) for e in existing) + len(content) > 24000:
        raise HTTPException(422, 'Evidence budget reached: maximum 20 items / 24000 characters')
    transition(db, item, version, draft='', draft_source='', status='OPEN')
    record = Evidence(tenant_id=tenant, dispute_id=item.id, title=title, kind=kind, content=content, sha256=hashlib.sha256(content.encode()).hexdigest())
    db.add(record)
    audit(db, tenant, actor, 'EVIDENCE_ADDED', item.id)
    db.commit()
    return record


def serialize(item):
    return {column.name: getattr(item, column.name) for column in item.__table__.columns}


def demo_seed(db, tenant):
    now = int(time.time())
    samples = [('PP-D-DEMO-1001', 'Alex Morgan', 'MERCHANDISE_OR_SERVICE_NOT_RECEIVED', 24900, 2),
               ('PP-D-DEMO-1002', 'Jordan Lee', 'MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED', 8950, 4),
               ('PP-D-DEMO-1003', 'Sam Rivera', 'UNAUTHORIZED_TRANSACTION', 12900, 1),
               ('PP-D-DEMO-1004', 'Taylor Chen', 'MERCHANDISE_OR_SERVICE_NOT_RECEIVED', 37900, 7)]
    for provider_id, customer, reason, amount, days in samples:
        d = Dispute(tenant_id=tenant, paypal_id=provider_id, customer=customer, reason=reason, amount_cents=amount, due_at=now + days * 86400)
        db.add(d)
        db.flush()
        db.add(Evidence(tenant_id=tenant, dispute_id=d.id, title='Demo order receipt', kind='INVOICE', content=f'SYNTHETIC DEMO DATA. Order for {customer}; paid {amount / 100:.2f} USD. Imported from sample merchant records.', sha256='demo'))
        audit(db, tenant, 'demo', 'DEMO_DISPUTE_CREATED', d.id)
    db.commit()

