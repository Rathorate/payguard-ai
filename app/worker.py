"""Durable webhook inbox worker. Run separately: python -m app.worker."""
import json
import logging
import time
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select, update, or_
from .config import Settings
from .models import Webhook, Dispute, database
from .providers import PayPal
from .service import audit

log = logging.getLogger('payguard.worker')


def timestamp(value):
    if not value:
        return 0
    return int(datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp())


def process_one(sessions, paypal):
    now = int(time.time())
    with sessions() as db:
        event = db.scalar(select(Webhook).where(Webhook.state.in_(['PENDING', 'PROCESSING']), Webhook.available_at <= now).order_by(Webhook.available_at, Webhook.id).limit(1))
        if not event:
            return False
        attempt = event.attempts + 1
        claimed = db.execute(update(Webhook).where(Webhook.id == event.id, Webhook.attempts == event.attempts, Webhook.available_at <= now).values(state='PROCESSING', attempts=attempt, available_at=now + 120))
        db.commit()
        if claimed.rowcount != 1:
            return True
        event_id, tenant, payload = event.id, event.tenant_id, event.payload
    try:
        # Fetch authoritative state, so delayed/out-of-order events cannot revert a dispute.
        resource = paypal.details(json.loads(payload)['resource']['dispute_id'])
        with sessions() as db:
            lease = db.scalar(select(Webhook).where(Webhook.id == event_id, Webhook.attempts == attempt, Webhook.state == 'PROCESSING').with_for_update())
            if not lease:
                return True
            paypal_id = resource['dispute_id']
            item = db.scalar(select(Dispute).where(Dispute.tenant_id == tenant, Dispute.paypal_id == paypal_id))
            amount = resource['dispute_amount']
            # MVP only supports currencies with two decimal minor units. No silent JPY/KWD conversion.
            if amount['currency_code'] not in {'USD', 'EUR', 'GBP', 'CAD', 'AUD'}:
                raise ValueError('Unsupported currency for provider import')
            cents = Decimal(amount['value']) * 100
            if cents != cents.to_integral_value() or cents <= 0:
                raise ValueError('Invalid dispute amount')
            provider_updated = resource.get('update_time', resource.get('create_time', ''))
            if item is None:
                transaction = next(iter(resource.get('disputed_transactions', [])), {})
                customer = transaction.get('buyer', {}).get('name', 'PayPal customer')
                if isinstance(customer, dict):
                    customer = ' '.join(str(v) for v in customer.values())
                item = Dispute(tenant_id=tenant, paypal_id=paypal_id, customer=str(customer)[:100], reason=resource['reason'], amount_cents=int(cents), currency=amount['currency_code'], due_at=timestamp(resource.get('seller_response_due_date')))
                db.add(item)
                db.flush()
            elif provider_updated and item.provider_updated and timestamp(provider_updated) < timestamp(item.provider_updated):
                lease.state = 'DONE'
                db.commit()
                return True
            values = dict(provider_updated=provider_updated, due_at=timestamp(resource.get('seller_response_due_date')), amount_cents=int(cents), currency=amount['currency_code'], reason=resource['reason'])
            if resource.get('status') in {'RESOLVED', 'CLOSED'}:
                values['status'] = 'RESOLVED'
            elif item.reason != resource['reason'] or item.amount_cents != int(cents) or item.currency != amount['currency_code']:
                if item.status not in {'SUBMITTING', 'SUBMITTED', 'SUBMISSION_UNKNOWN'}:
                    values.update(status='OPEN', draft='', draft_source='')
            elif item.due_at != values['due_at'] and item.status == 'APPROVED':
                # A reviewer explicitly acknowledged the deadline; a changed deadline needs another review.
                values['status'] = 'REVIEW'
            updated = db.execute(update(Dispute).where(Dispute.id == item.id, Dispute.version == item.version).values(**values, version=item.version + 1))
            if updated.rowcount != 1:
                raise ValueError('Concurrent dispute edit; retry ingestion')
            lease.state = 'DONE'
            audit(db, tenant, 'paypal-webhook', 'PAYPAL_EVENT_PROCESSED', item.id)
            db.commit()
    except Exception:
        log.exception('webhook_processing_failed event_id=%s attempt=%d', event_id, attempt)
        with sessions() as db:
            db.execute(update(Webhook).where(Webhook.id == event_id, Webhook.attempts == attempt).values(state='DEAD' if attempt >= 5 else 'PENDING', available_at=now + min(3600, 2 ** attempt * 10)))
            db.commit()
    return True


def main():
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    settings.validate()
    _, sessions = database(settings.database_url)
    paypal = PayPal(settings)
    while True:
        if not process_one(sessions, paypal):
            time.sleep(2)


if __name__ == '__main__':
    main()
