# PayPal sandbox setup

The application has its own database. Access to PayPal data is through an authorized API, not a direct PayPal database connection. Use sandbox credentials and test accounts only.

## 1. Save credentials privately

Open https://developer.paypal.com/dashboard/applications/sandbox and use the existing Default Application. Copy its Client ID and Secret using the page controls. In Ubuntu:

```bash
cd ~/projects/payguard-ai
nano .env
```

Fill PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET. Preserve Groq settings and keep PAYPAL_ENVIRONMENT=sandbox and DEMO_MODE=true. Save with Ctrl+O, Enter, Ctrl+X. Never send credentials in chat, commit them or place them in frontend settings. The dev launcher and diagnostic script load this trusted local file.

## 2. Verify authentication

```bash
git pull --ff-only
bash scripts/verify-paypal.sh
```

This makes an actual sandbox OAuth request and prints credential-presence booleans and a sanitized result. It creates no payment or dispute and submits no evidence. Authentication success does not prove dispute access. A 401 suggests an incorrect pair/environment; a 403 requires account/permission investigation. Do not substitute live credentials.

The diagnostic also prints a short SHA-256 fingerprint of the Client ID and whether the returned token advertises the seller dispute-read scope. The fingerprint cannot authenticate to PayPal; compare it locally with the intended app to spot a stale credential pair. A listed scope does not prove access to a particular merchant's case. Missing scope information is reported as unknown, not success. Protocol error codes and debug references are whitelisted; raw upstream messages/tokens are never printed.

To separate account access from case ownership:

```bash
bash scripts/verify-paypal.sh --list-disputes
```

Only up to ten dispute IDs/statuses are printed; no buyer details. This is the first page only. A successful empty list does not establish that a particular case belongs to the app's merchant. If list access fails with 403, confirm the app's Customer disputes feature and token scope with PayPal support before enabling writes.

## 3. Map the merchant workspace

```bash
BACKEND_PORT=8001 FRONTEND_PORT=3001 bash scripts/dev.sh
```

Keep the terminal open. Open http://127.0.0.1:3001 and sign into the workspace you intend to connect. Integrations displays its workspace ID. Save that ID as PAYPAL_TENANT_ID in the backend .env. Stop both servers with Ctrl+C and restart with the same command. Test sandbox authentication from Integrations. One deployment supports one configured PayPal merchant; never map unrelated merchant accounts together.

## 4. Verify an actual dispute read

The buyer must be a different sandbox account from the seller. If checkout asks for another account while the Business seller is signed in, use a separate browser profile/private window and sign in with the Personal sandbox email and its generated password. The Developer Dashboard login, sandbox Business account and sandbox Personal account serve different roles. Do not use real credentials or real card data to work around a test login error.

Credentials do not create a dispute. Use the matching sandbox business/seller account and a sandbox personal/buyer account. A sandbox purchase and a dispute supported by the account/test environment may be necessary. Use official sandbox/Resolution Center guidance. A webhook simulator or invented ID does not create a retrievable dispute. If this flow or API access is unavailable, ask PayPal developer support or hackathon organizers for an eligible scenario and report the sanitized error.

For a dispute belonging to the app's seller:

```bash
bash scripts/verify-paypal.sh --dispute-id YOUR-REAL-SANDBOX-DISPUTE-ID
```

This validates a remote response without importing it. Integrations > Import sandbox dispute creates a local case and minimal source snapshot. Duplicate IDs are rejected without overwriting evidence or approval. Missing deadlines remain unknown and block submission. Only supported currencies are accepted. A snapshot proves dispute metadata, not delivery or authorization.

## 5. Rehearse AI and human review

Open the imported case, add relevant synthetic sandbox evidence, and generate a Groq draft. Check every claim, edit and save. Unchecked review and unsaved changes must block approval. Approve the saved version, withdraw and reapprove it, and export the approved packet. Separately acknowledge simulated submission. DEMO_MODE=true never sends evidence, even with PayPal credentials configured. Inspect the audit log.

Record authentication, actual dispute read/import, AI generation, human corrections and simulated submission as separate results. Mocked tests and OAuth success do not prove evidence acceptance. Real sandbox submission, verified webhooks and uncertain-result reconciliation require further validation before enabling writes.

## Hosting and hackathon

Meaningful PayPal platform integration is required; simulation alone should not be assumed sufficient. Check current [hackathon rules](https://paypalaihackathon.devpost.com/rules) and confirm eligibility with organizers. A hosted demo should retain DEMO_MODE=true, exact HTTPS APP_ORIGIN, SECURE_COOKIES=true, managed PostgreSQL and backend-only keys. Verify hosting before recording the final video.

Official references: [sandbox accounts](https://developer.paypal.com/tools/sandbox/accounts/), [sandbox starter](https://github.com/paypaldev/getting-started-with-paypal-sandbox), [disputes API](https://developer.paypal.com/docs/api/customer-disputes/v1/).
