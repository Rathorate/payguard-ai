# Free-first hackathon hosting plan

Preference confirmed by the user on 22 October 2026: use free services where possible, accepting cold starts and quota limits. This document prepares configuration; it does not create any cloud resource.

| Component | Proposed service | Configuration |
|---|---|---|
| Frontend | Vercel free eligible plan | GitHub Rathorate/payguard-ai, root frontend, Other preset, BACKEND_ORIGIN = resulting backend HTTPS origin |
| API | Render Free web service | Repository root, Python 3.12+, build pip install -r requirements.txt, start uvicorn app.main:app --host 0.0.0.0 --port $PORT --no-proxy-headers, readiness /health/ready |
| Data | Separate Neon Free PostgreSQL project | Dedicated PayGuard database, SSL connection URL stored only as backend DATABASE_URL |
| Case synchronization | Manual authenticated Refresh PayPal status | No claim of automatic live synchronization; do not provision a paid worker in this free-first phase |

Neon Free is a proposed external database choice, not an already configured account/project. Its current published plan is $0/month with compute/storage/network allowances and scale-to-zero. Render's existing free database belongs to CropGrid and must not be reused. Render free web services share a workspace's free usage allowance and sleep after inactivity; cloud latency and availability must be tested. A free Render Postgres database also expires after 30 days, making it a poor choice for preserving a judging demo across a longer period.

Official references checked on 22 October 2026:
- https://neon.com/docs/introduction/plans
- https://render.com/docs/free

## Private backend configuration

DATABASE_URL must be the actual new database connection string with SSL required. APP_ORIGIN must be the actual production frontend HTTPS origin. Set SECURE_COOKIES=true, DEMO_MODE=true, PAYPAL_ENVIRONMENT=sandbox, AI_PROVIDER=groq and the current GROQ_MODEL. Save the existing Groq key and sandbox Client ID/Secret privately on Render; never in Vercel settings, source, screenshots or chat. Create/sign into the hosted PayGuard merchant account, then use its newly created workspace ID for PAYPAL_TENANT_ID. Local SQLite accounts, sessions and workspace IDs do not automatically appear in PostgreSQL.

Keep only synthetic/sandbox evidence in the public hackathon demo. The demo login creates synthetic fixtures; the connected merchant account is separate. Configure a fixed frontend production URL before final session/CSRF tests; previews need separate isolated origin/data configuration.

## Rollout order

1. Finish the current source-reference repair's actual Groq rehearsal and human review of the version actually saved.
2. Confirm access to the proposed free Neon/Vercel accounts and resource choices. Review account agreements/permissions if prompted; no paid upgrade is authorized.
3. Create a separate PayGuard Free database, then the Render Free API and Vercel frontend. Match all real origins and private environment settings.
4. Verify hosted readiness, login/session reload, upload, AI checks, draft edits, approval, export and explicitly simulated submission; restart the backend and verify data persists.
5. Re-import the sandbox case to the hosted connected workspace and recheck allowed provider actions. Synthetic records must remain clearly labelled.
6. Configure and test external webhook delivery only if introducing a processing strategy. Until a worker is deliberately enabled and tested, describe synchronization as manual refresh. A paid worker is outside the chosen free-first scope.
7. Provide judge access, retain a working build for judging, and record the video only after hosted verification.
