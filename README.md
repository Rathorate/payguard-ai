# PayGuard AI

A runnable hackathon MVP for merchant dispute operations, based on the supplied PayGuard brief. It combines a dispute inbox, evidence records, text-PDF extraction, template/optional AI defense drafting, mandatory human review, simulated or PayPal submission, and an audit log.

**Status:** working MVP with production-oriented controls. Not a certified payment platform or proven million-user deployment. Live provider acceptance requires your sandbox credentials and testing. This repository deliberately avoids claiming that recorded tracking statements are independently verified.

## Run locally

For Ubuntu / WSL, see [the WSL development guide](docs/WSL.md).

Python 3.12 or later:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 and select **Open interactive demo**. Each demo gets an isolated workspace with four synthetic disputes. No provider keys are needed. State persists in `payguard.db`. Demo responses never go to PayPal. Creating a workspace gives you an empty account; use demo to see sample records.

On macOS/Linux, use `python3`, `.venv/bin/python`, and the same module commands.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing
node --check static/app.js
```

`tests/test_postgres.py` runs only when `TEST_POSTGRES_URL` points to a **disposable** database. CI provisions PostgreSQL and runs that test. Other tests exercise HTTP APIs, auth/session/CSRF, tenant isolation, stale-write protection, evidence extraction, review and submission, durable webhook retries, and mocked provider contracts. Test dependencies are pinned alongside runtime dependencies for one-step hackathon setup.

See [verification](docs/VERIFICATION.md) for actual local results and remaining checks.

## Design and implementation

- [System, UI, database, API, file structure and scale plan](docs/ARCHITECTURE.md)
- [Operations and provider setup](docs/OPERATIONS.md)
- Interactive API contract: `/docs` (Swagger) and `/openapi.json`
- Generated schema: [docs/schema.sql](docs/schema.sql)
- Generated API specification: [docs/openapi.json](docs/openapi.json)

## API keys later

Copy `.env.example` to `.env`. It is excluded from Git. Docker Compose loads it; local Python reads **process environment variables**, so set variables in the terminal before launching. Credentials never belong in the frontend or a commit.

Optional drafting: set `OPENAI_API_KEY` and `OPENAI_MODEL`. The model must support the Responses API and be enabled for your account. With no key, the app explicitly uses a deterministic template. Inputs include evidence text; assess data handling before using real customer records.

PayPal sandbox: set `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID`, `PAYPAL_TENANT_ID`, and `PAYPAL_ENVIRONMENT=sandbox`. The merchant workspace ID is returned by `/api/v1/auth/me`, shown in the API response after sign-in, or listed with `python -m app.manage tenants`.

To send actual sandbox requests, `DEMO_MODE` must be `false`. This requires HTTPS `APP_ORIGIN` and `SECURE_COOKIES=true`; use an HTTPS reverse proxy/tunnel. Configure the webhook URL `/api/v1/webhooks/paypal`, subscribe to `CUSTOMER.DISPUTE.CREATED`, `.UPDATED`, and `.RESOLVED`, and run `python -m app.worker`. Verification must succeed before an event is persisted.

MVP limitations: one connected PayPal merchant per deployment, notes-only evidence submission, manual source evidence, no carrier integration, no image OCR, no original-PDF retention, no auto-submission, no email verification/password reset/team RBAC, no provider reconciliation UI. These are explicit follow-on features, not simulated integrations.

## Docker / PostgreSQL

Set `.env` values and a URL-safe random `POSTGRES_PASSWORD` (at least 32 alphanumeric characters). Then:

```sh
docker compose up --build
```

This starts PostgreSQL, initializes the schema once, then starts the API and durable inbox worker. A local demo may use HTTP; production must use a TLS reverse proxy. The API port is bound to loopback. Do not expose the database publicly. PostgreSQL volumes persist data. `app.manage init-db` initializes a fresh schema; it does not upgrade an existing schema. Introduce versioned migrations before subsequent production schema changes.

## Source references

Provider adapters were checked against [PayPal evidence submission](https://developer.paypal.com/api/customer-disputes/v1/disputes-provide-evidence), [PayPal webhook verification](https://developer.paypal.com/api/webhooks/v1/verify-webhook-signature-post), [OpenAI text generation](https://developers.openai.com/api/docs/guides/text), and [FastAPI container deployment](https://fastapi.tiangolo.com/deployment/docker/). See operations for the narrower submission behavior implemented here.
