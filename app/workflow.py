"""Deterministic preparation guidance; never an eligibility or win prediction."""
import re
import time
from urllib.parse import urlsplit
from .paypal_import import snapshot
from .providers import ProviderError
from .review import citation_report

ACTIONS = {
    'provide-evidence': 'Provide evidence', 'send-message': 'Message the other party',
    'provide-supporting-info': 'Provide supporting information',
    'make-offer': 'Make an offer', 'accept-claim': 'Accept the claim',
    'appeal': 'Appeal', 'escalate': 'Escalate to a claim',
    'accept-offer': 'Accept an offer', 'deny-offer': 'Decline an offer',
    'acknowledge-return-item': 'Acknowledge a returned item',
}


def observe(resource, identity, environment):
    fields, _ = snapshot(resource, identity)
    stage = resource.get('dispute_life_cycle_stage', 'UNKNOWN')
    if not isinstance(stage, str) or not re.fullmatch(r'[A-Z_]{1,64}', stage):
        raise ProviderError('PayPal returned an invalid lifecycle stage; previous observation was kept.')
    host = 'api-m.sandbox.paypal.com' if environment == 'sandbox' else 'api-m.paypal.com'
    links = resource.get('links', [])
    if not isinstance(links, list) or len(links) > 100:
        raise ProviderError('PayPal returned invalid action links; previous observation was kept.')
    actions = set()
    # Store allowlisted names only. Never follow a provider-supplied URL.
    for link in links:
        if not isinstance(link, dict):
            continue
        action = link.get('rel')
        if not isinstance(action, str) or action not in ACTIONS or link.get('method') != 'POST':
            continue
        href = link.get('href')
        if not isinstance(href, str) or len(href) > 1024:
            continue
        try:
            url = urlsplit(href)
            valid = (url.scheme == 'https' and url.netloc == host and not url.query and not url.fragment
                     and url.path == f'/v1/customer/disputes/{identity}/{action}')
        except ValueError:
            valid = False
        if valid:
            actions.add(action)
    return {'environment': environment, 'stage': stage, 'provider_status': resource.get('status', 'UNKNOWN'),
            'due_at': fields['due_at'], 'provider_updated': fields['provider_updated'],
            'reason': fields['reason'], 'amount_cents': fields['amount_cents'], 'currency': fields['currency'],
            'actions': sorted(actions)}


def preparation(item, records, observation, analysis, demo, connected):
    now = int(time.time())
    provider = observation
    stale = not provider or now - provider['observed_at'] > 300
    mismatch = bool(provider and any(provider[k] != getattr(item, k) for k in ('due_at', 'reason', 'amount_cents', 'currency')))
    citations = citation_report(item.draft, records)
    findings = analysis.get('findings', []) if analysis else []
    checks = []
    def add(label, state, detail, ids=None):
        checks.append({'label': label, 'state': state, 'detail': detail, 'evidence_ids': ids or []})
    add('PayPal case checked', 'ATTENTION' if stale or mismatch else 'RECORDED',
        'Refresh PayPal status. Recorded observations do not update case evidence or approval.' if stale else
        'PayPal facts differ from the saved case. Withdraw approval and reconcile in PayPal before sending.' if mismatch else
        'Recent read-only observation. Actions can change; sending requires another provider check.')
    deadline = provider['due_at'] if provider else item.due_at
    add('Response deadline', 'ATTENTION' if not deadline or deadline <= now else 'RECORDED',
        'Deadline unavailable; check PayPal.' if not deadline else 'Deadline has passed; check PayPal.' if deadline <= now else
        'Date recorded. Confirm it in PayPal before responding.')
    required = [('INVOICE', 'Order / transaction record')]
    if item.reason == 'MERCHANDISE_OR_SERVICE_NOT_RECEIVED':
        required += [('TRACKING', 'Delivery / fulfillment record'), ('COMMUNICATION', 'Buyer communication')]
    elif item.reason == 'MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED':
        required += [('OTHER', 'Product description / condition record'), ('COMMUNICATION', 'Buyer communication')]
    else:
        required += [('OTHER', 'Records relevant to the dispute reason')]
    for kind, label in required:
        matches = [r.id for r in records if r.kind == kind and r.title != 'PayPal sandbox dispute snapshot']
        add(label, 'REVIEW' if matches else 'MISSING',
            'Record attached; review its contents and relevance. Type alone does not verify the claim.' if matches else
            'No record of this type attached. Suggested preparation, not a PayPal requirement.', matches)
    add('AI evidence checks', 'REVIEW' if analysis else 'MISSING',
        f"{sum(f['category']=='MISSING' for f in findings)} gaps and {sum(f['category']=='CONFLICT' for f in findings)} conflicts flagged. Inspect the source-linked findings below." if analysis else
        'Run evidence checks for the current saved version; findings still require human judgment.')
    add('Saved response citations', 'ATTENTION' if citations['unknown_ids'] or not item.draft else 'REVIEW',
        'Generate or save a response, then inspect its references.' if not item.draft else
        'Unknown references must be corrected.' if citations['unknown_ids'] else
        'Inspect each factual assertion. Valid reference IDs do not establish accuracy.')
    add('Human approval', 'RECORDED' if item.status == 'APPROVED' else 'REVIEW',
        'Current saved version approved by the merchant. Provider acceptance remains unverified.' if item.status == 'APPROVED' else
        'Read, correct and approve the exact saved response. AI never approves it.')
    if item.status in {'SUBMITTING', 'SUBMISSION_UNKNOWN'}:
        next_step = 'Reconcile the existing submission in PayPal. Do not retry an uncertain send.'
    elif item.status in {'SUBMITTED', 'RESOLVED'}:
        next_step = 'Review the recorded outcome. A simulated submission is not PayPal acceptance.'
    elif not provider:
        next_step = 'Refresh PayPal status to discover this case’s available actions.' if connected else 'Prepare the evidence and response locally. Connect the matching seller to check PayPal actions.'
    elif mismatch or stale:
        next_step = 'Refresh and reconcile the PayPal case facts before deciding on a response.'
    elif not deadline or deadline <= now:
        next_step = 'Check the response deadline in PayPal before proceeding. Submission is blocked locally.'
    elif provider['provider_status'] != 'WAITING_FOR_SELLER_RESPONSE':
        next_step = 'PayPal is not waiting for seller evidence. Review the case status and available actions in PayPal.'
    elif not provider['actions']:
        next_step = 'No supported action link was returned. Check the case in PayPal; do not assume evidence submission is available.'
    elif item.status != 'APPROVED':
        next_step = 'Review missing facts and source excerpts, save corrections, then approve the response.'
    elif 'provide-evidence' not in provider['actions']:
        next_step = 'Evidence submission is not available in this observation. Review the other available actions in PayPal.'
    else:
        next_step = 'Review the approved packet, then explicitly confirm simulation.' if demo else 'Review the approved packet before explicitly confirming a PayPal send.'
    return {'provider': provider, 'stale': stale, 'facts_changed': mismatch, 'connected': connected,
            'next_step': next_step, 'checks': checks, 'demo': demo,
            'notice': 'Preparation guidance only. No completeness score, eligibility decision or win prediction. Refresh sends no response to PayPal.'}
