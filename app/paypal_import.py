"""Validate an authoritative sandbox read before it becomes local case evidence."""
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
from .providers import ProviderError


def snapshot(resource, expected_id):
    try:
        if not isinstance(resource, dict) or resource.get('dispute_id') != expected_id:
            raise ValueError('Dispute ID mismatch')
        amount = resource['dispute_amount']
        currency = amount['currency_code']
        if currency not in {'USD','EUR','GBP','CAD','AUD'}:
            raise ValueError('Unsupported currency')
        cents = Decimal(str(amount['value'])) * 100
        if not cents.is_finite() or not 0 < cents <= 1000000000 or cents != cents.to_integral_value():
            raise ValueError('Invalid amount')
        reason = resource['reason']
        if not isinstance(reason,str) or not reason.strip() or len(reason)>100:
            raise ValueError('Invalid reason')
        deadline = resource.get('seller_response_due_date')
        due_at = 0
        if deadline:
            parsed = datetime.fromisoformat(deadline.replace('Z','+00:00'))
            if parsed.tzinfo is None: raise ValueError('Deadline needs timezone')
            due_at = int(parsed.timestamp())
            if not 0 < due_at <= 2147483647: raise ValueError('Deadline out of range')
        status = resource.get('status','UNKNOWN')
        if not isinstance(status,str) or len(status)>100: raise ValueError('Invalid provider status')
        updated = resource.get('update_time',resource.get('create_time',''))
        if not isinstance(updated,str) or len(updated)>64: raise ValueError('Invalid update time')
        transactions = resource.get('disputed_transactions') or []
        customer = 'PayPal sandbox customer'
        if transactions and isinstance(transactions,list) and isinstance(transactions[0],dict):
            buyer = transactions[0].get('buyer') or {}
            name = buyer.get('name') if isinstance(buyer,dict) else None
            if isinstance(name,str) and name.strip(): customer=name.strip()[:100]
            elif isinstance(name,dict):
                customer=' '.join(v for v in name.values() if isinstance(v,str)).strip()[:100] or customer
        fields = {'paypal_id':expected_id,'customer':customer,'reason':reason,'amount_cents':int(cents),'currency':currency,'due_at':due_at,'provider_updated':updated,'status':'RESOLVED' if status in {'RESOLVED','CLOSED'} else 'OPEN'}
        # Deliberately retain a minimal factual summary, not the entire provider response.
        content = 'PAYPAL SANDBOX TEST DATA. Imported by an authenticated dispute read.\n' + json.dumps({'dispute_id':expected_id,'reason':reason,'amount_cents':int(cents),'currency':currency,'provider_status':status,'response_deadline':deadline or 'unavailable','provider_updated':updated},sort_keys=True) + '\nThis is a dispute snapshot, not proof of delivery or authorization. No submission has been made.'
        return fields, content
    except (ValueError, KeyError, TypeError, AttributeError, InvalidOperation, OverflowError) as exc:
        raise ProviderError('PayPal returned unsupported or malformed case data; no case was imported. Check dispute ID, currency, amount and deadline.') from exc
