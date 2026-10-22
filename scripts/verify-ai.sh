#!/usr/bin/env bash
# Sends only synthetic evidence to the selected AI provider. Never prints keys.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
if [[ ! -x .venv/bin/python ]]; then echo 'Run bash scripts/bootstrap.sh first.' >&2; exit 1; fi
if [[ -f .env ]]; then set -a; source .env; set +a; fi
.venv/bin/python - <<'PY'
from types import SimpleNamespace
from app.config import Settings
from app.providers import generate_draft, ProviderError
settings = Settings()
status = settings.ai_status()
print('Saved provider:', status['ai_provider'], '| Groq key present:', status['groq_key_present'], flush=True)
print(status['ai_message'], flush=True)
if not status['ai_configured']:
    raise SystemExit(1)
print('Testing with synthetic evidence only; no case will be approved or submitted.', flush=True)
item = SimpleNamespace(paypal_id='PP-D-CONNECTION-TEST', reason='INQUIRY', amount_cents=1000, currency='USD')
evidence = [SimpleNamespace(id='SAMPLE-RECEIPT', title='Synthetic receipt', content='SYNTHETIC CONNECTION TEST. Merchant records payment of 10.00 USD. Delivery and authorization are unverified.')]
try:
    text, source = generate_draft(settings, item, evidence)
except ProviderError as exc:
    raise SystemExit(str(exc)) from None
print('Connection verified:', source, '| Model:', status['ai_model'])
print(text)
print('Human review is required. Nothing was sent to PayPal.')
PY
