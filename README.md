# PayGuard AI

For the local hackathon workflow, Groq setup, review/approval checks and PayPal-free demonstration, see [HACKATHON.md](docs/HACKATHON.md). The frontend and backend remain independently deployable; this rehearsal stays local.

See [readiness and remaining gaps](docs/READINESS.md) for the verified human review flow, real Groq rehearsal, current limits and the work needed before public deployment or real PayPal submission.

A hackathon MVP for merchant dispute operations: accounts, demo fixtures, searchable dispute inbox, evidence text/PDF import, template or optional AI drafting, merchant review, simulated/PayPal submission and audit history.

**Status:** tested MVP with production-oriented controls. Provider acceptance, cloud deployment and scale still require validation. Recorded merchant evidence is not independently carrier-verified.

## Separate frontend and backend

| Component | Source | Deployment |
|---|---|---|
| Frontend | `frontend/` | Vercel, static UI and native API rewrite |
| Backend | `app/`, deployment root is the repository root | Render or Railway, FastAPI |
| Database | Managed PostgreSQL | Backend and optional worker only |
| Optional PayPal worker | `app/worker.py` | Separate backend process |

All existing features remain. See [deployment setup](docs/DEPLOYMENT.md) for the two hosting projects, API routing and session/CSRF configuration. The browser calls `/api/v1` on the frontend origin; its host forwards those requests to the independently deployed backend. Provider keys remain on the backend.

## Run locally in Ubuntu / WSL

Requires Python 3.12+ and Node.js 22.18+. Keep your existing `.env` and database; bootstrap does not overwrite them.

```bash
bash scripts/bootstrap.sh
bash scripts/test.sh
BACKEND_PORT=8001 FRONTEND_PORT=3000 bash scripts/dev.sh
```

Open http://127.0.0.1:3000 and select **Open interactive demo**. Two separate processes run; Ctrl+C stops both. The launcher sets the local frontend Origin correctly even if an older `.env` contains port 8000. Demo mode needs no API keys and simulates every submission. Each demo workspace gets four synthetic disputes; regular account registration starts an empty workspace.

On Windows, create/install a Python virtual environment, then run the backend and frontend in two PowerShell terminals:

```powershell
# Terminal 1, at repository root
$env:APP_ORIGIN='http://127.0.0.1:3000'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001

# Terminal 2, at repository root
$env:BACKEND_ORIGIN='http://127.0.0.1:8001'
node frontend/dev-server.mjs
```

## Test

```bash
bash scripts/test.sh
```

The Python suite includes a real two-process HTTP workflow: cookies, CSRF, PDF upload, drafting, approval, simulated submission, audit and logout. Existing auth, tenant isolation, optimistic locking, provider and worker tests remain. Node tests verify assets, deployment configuration, streaming proxy headers/bodies and backend failures. `TEST_POSTGRES_URL` must point at a disposable database to run the PostgreSQL smoke test. CI provisions one; written CI configuration alone is not evidence of a successful run.

## Deploy

- **Vercel:** root `frontend`, preset Other, set `BACKEND_ORIGIN` to your backend HTTPS origin. `vercel.ts` configures the native rewrite and publishes `public/`.
- **Render/Railway:** use the repository root and root Dockerfile, or native Python build/start commands from [DEPLOYMENT.md](docs/DEPLOYMENT.md). Set managed `DATABASE_URL`, the exact frontend `APP_ORIGIN`, and `SECURE_COOKIES=true`.
- **PayPal:** add an inbox worker when sandbox access is ready; webhook requests go directly to the backend.

For a local PostgreSQL/containers setup, copy `.env.example` to `.env`, add a URL-safe random `POSTGRES_PASSWORD`, and run `docker compose up --build`. The frontend is port 3000, API port 8000. The Node Compose service is a local development proxy; production uses Vercel. This initializes a fresh database but does not provide future schema migrations.

## API keys later

The dev script loads the trusted local `.env`. Direct Python commands read process environment variables. Never commit `.env`, databases or keys.

Optional AI drafting supports Groq (`AI_PROVIDER=groq`, `GROQ_API_KEY`, `GROQ_MODEL`) and the existing OpenAI adapter. Set `AI_PROVIDER=template` for offline drafting. With the default `auto`, a configured Groq key takes priority, then OpenAI, otherwise a deterministic template. The adapter boundary is `generate_draft` in `app/providers.py`; retain its return shape, failure handling and mandatory human review. Real model quality requires credentialed evaluation.

PayPal sandbox configuration needs `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID`, `PAYPAL_TENANT_ID` and `PAYPAL_ENVIRONMENT=sandbox`. Find the merchant tenant via authenticated `/api/v1/auth/me` or `python -m app.manage tenants`. Keep `DEMO_MODE=true` until ready: all submissions remain simulated in that mode. Real sandbox requests require `DEMO_MODE=false`, HTTPS frontend Origin and secure cookies. See [operations](docs/OPERATIONS.md).

Existing MVP limits remain: one connected PayPal merchant per deployment, notes-only submission, manual source evidence, text-PDF extraction without image OCR/original-file retention, no carrier integration, no auto-submission, no email recovery/team RBAC, and no reconciliation UI. These are follow-on features.

## Design and verification

- [Separate deployment and migration guide](docs/DEPLOYMENT.md)
- [Architecture, schema, API and scale plan](docs/ARCHITECTURE.md)
- [Operations and provider setup](docs/OPERATIONS.md)
- [WSL guide](docs/WSL.md)
- [API specification](docs/openapi.json) and [SQL schema](docs/schema.sql)
- [Verification record](docs/VERIFICATION.md)

Official hosting references: [Vercel programmatic configuration](https://vercel.com/docs/project-configuration/vercel-ts), [external rewrites](https://vercel.com/docs/routing/rewrites), [Render web services](https://render.com/docs/web-services), [Railway FastAPI](https://docs.railway.com/guides/fastapi).
