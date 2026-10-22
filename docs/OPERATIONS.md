# Deployment update

Frontend and backend now deploy independently. Follow [DEPLOYMENT.md](DEPLOYMENT.md) for the current routing, ports and hosting settings. Provider operations below still apply; descriptions of a combined static/API deployment are superseded.

# Operations and integration handoff

## Demo versus provider requests

`DEMO_MODE=true`: all submissions are simulated, even if PayPal keys exist. External webhooks still require PayPal verification. `DEMO_MODE=false`: demo login disappears and submission calls PayPal only for `PAYPAL_TENANT_ID`. No unsigned webhook bypass exists.

The PayPal adapter uses client-credential OAuth, fetches authoritative dispute state, requires `WAITING_FOR_SELLER_RESPONSE` and an advertised `provide-evidence` relation, and posts notes as `evidence_type=OTHER`. It uses a fixed trusted provider host and a validated dispute ID, never a user-provided URL. Text is bounded to 2000 characters before sending. Original PDF attachments, carrier proof formats, reason-specific evidence requirements, and partner merchant onboarding are not implemented. Use the Resolution Center for evidence that needs binary attachments. Sandbox access and required scopes depend on the merchant account; keys alone do not prove API eligibility.

Current PayPal reference: https://developer.paypal.com/api/customer-disputes/v1/disputes-provide-evidence
Webhook verification: https://developer.paypal.com/api/webhooks/v1/verify-webhook-signature-post
AI drafting: https://developers.openai.com/api/docs/guides/text

## First sandbox test with credentials

1. Create a merchant workspace and obtain its tenant ID. Configure the server environment. Keep `PAYPAL_ENVIRONMENT=sandbox`.
2. Use a disposable PostgreSQL database and run `python -m app.manage init-db`. Production schema changes need proper versioned migrations before code rollout.
3. Set a public HTTPS APP_ORIGIN and SECURE_COOKIES=true, disable demo mode, run API and worker behind TLS.
4. Register the exact HTTPS webhook endpoint in the PayPal developer app. Match webhook ID, credentials, environment and merchant workspace.
5. Send a signed sandbox event. Confirm acceptance, inbox DONE state and imported dispute. Missing deadlines are stored as zero and submission is blocked until a correct provider deadline is available; no deadline is invented.
6. Add a short genuine merchant evidence record, generate/edit a concise draft, approve it and submit. Verify the evidence in PayPal independently. Only sandbox accounts and synthetic transactions should be used in initial tests.
7. Repeat webhook delivery, confirm deduplication; test a provider outage and restart worker to verify durable recovery. Verify unknown submissions are locked rather than retried.

## Deployment

Run the provided Docker Compose profile for a single-host setup or deploy the same API image and worker image to managed compute with managed PostgreSQL. It is not published to a hosting provider by this task. The separately hosted frontend forwards /api/v1 to this API through a same-origin proxy.

Keep API containers stateless when using PostgreSQL. Run initial schema setup as a one-off release job. Configure database max connections and per-process pools together; default SQLAlchemy pools are a starting point only. The Docker command ignores forwarded headers. Only enable trusted proxy handling for explicit proxy IPs at your host, never all Internet callers. Auth throttling currently uses the actual connection IP; a proxy deployment needs edge rate limiting or correctly trusted client IPs. Database throttling alone is not a DDoS defense.

Use an external secret store, automated backups, database encryption, TLS, least-privilege DB credentials and a private network. Restrict `/docs` if internal documentation is sensitive. The repo excludes `.env`, databases and local reports. Configure request logs at INFO, collect request IDs, and alert on 5xx rates, database saturation, provider failures, oldest inbox age, DEAD inbox records and PENDING/UNKNOWN submissions. Logs contain route IDs and event IDs; apply retention/access controls. The example deployment has no monitoring vendor configured.

## Reconciliation: ambiguous submissions

There is deliberately no automatic retry or UI unlock. The merchant and operator must inspect PayPal's current evidence/activity and the submission record.

- PENDING + SUBMITTING can mean a process crashed before or after the provider accepted evidence.
- UNKNOWN + SUBMISSION_UNKNOWN means the provider did not yield a reliable locally committed success, including a validation failure or timeout.
- Check PayPal before any correction. Retain the original submission/audit records. Do not delete intent rows to retry blindly.
- A later resolved webhook may set the case to RESOLVED; it does not establish whether a particular submission succeeded.
- A dedicated reconciliation tool with explicit permissions and a reviewed recovery action is follow-on work. Until then use the PayPal Resolution Center for follow-up and a controlled operator database change only after a documented incident review.

## Worker recovery

The worker retries intake failures five times, then marks DEAD. Review errors and current provider state before requeueing a record. Worker leases are recoverable after 120 seconds; a fencing attempt number stops an expired claimant from overwriting a newer attempt. The polling loop has no external queue dependency. Container stop may interrupt processing; the lease provides recovery on restart. Under sustained volume replace polling with a queue/outbox pattern.

## Security and readiness boundaries

App controls implemented: password hashing, hashed opaque sessions, expiration and revocation, CSRF, same-origin checks, CSP and frame blocking, no browser API keys, tenant-scoped operations, bounded input/upload counts, generic 500 responses, request IDs, shared auth/drafting throttles, optimistic locking and durable intake/submission intent.

Before serving untrusted production customers, add verified identity/recovery, MFA/team RBAC as needed, database-enforced tenant isolation, invite/onboarding abuse controls, encrypted per-merchant credentials, protected document processing sandbox, audit retention/export, privacy and deletion policy, versioned migrations, sandbox acceptance tests, backup restore tests, deployment/load testing, monitoring and an incident runbook. The current PDF parser runs inside API worker processes; byte/page limits do not guarantee protection from decompression bombs or CPU-heavy documents. Put untrusted parsing behind a resource-limited worker before public uploads.

Confidence scores and win rates are intentionally absent. Evidence completeness, carrier verification and Seller Protection eligibility are separate concepts and are not inferred from generated text.
