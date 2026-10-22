# Separate deployment verification - 22 October 2026

- Python regression suite plus real separate frontend/API HTTP workflow: **30 passed, 1 skipped**. The skipped check requires disposable PostgreSQL.
- **4 Node tests passed**: valid/invalid deployment origins, public assets/path isolation, cookie/CSRF/Origin and multipart byte forwarding, unavailable backend response.
- Frontend asset/config build check, JavaScript syntax and direct programmatic Vercel config import passed.
- New workflow exercised the real Node frontend and Uvicorn backend on different ports, including login, PDF extraction, draft, approval, simulated submission, audit and logout.
- Bash syntax checks passed for bootstrap, test and development launchers.
- Existing database and provider behavior remains covered. A local temp-folder ownership error was avoided by using a fresh workspace test directory; application tests then passed.
- Vercel/Render/Railway deployments, Docker startup, managed PostgreSQL and credentialed provider calls remain unverified. Local proxy tests do not certify a cloud deployment.
- Backend container entrypoint smoke test passed with a dynamically assigned PORT, and the separate frontend served the dashboard and forwarded API calls. Docker image construction itself remains unverified.

The previous MVP verification below is historical. Its combined-host routing and UI paths are superseded by DEPLOYMENT.md.

# Verification record

Verified locally on 20 October 2026 using Windows, Python 3.12.14 and the dependency versions in requirements.txt.

## Automated checks

- Full API/security/provider/worker suite: **26 passed, 1 skipped**. The skipped test requires a disposable PostgreSQL database. No failing tests in the completed run.
- Final backend line coverage: **91% overall**, **92% for the HTTP application**, **98% for provider adapters**. The schema management CLI was smoke tested separately rather than under coverage. Final suite duration: 65.19 seconds; one TestClient deprecation warning.
- Simultaneous edits: one HTTP 200, one HTTP 409; no silent lost update.
- Browser JavaScript syntax: `node --check static/app.js` passed.
- Installed dependency compatibility: `python -m pip check` passed.
- Initial schema CLI: `python -m app.manage init-db` passed using a separate SQLite database.
- OpenAPI and PostgreSQL schema export completed; exported files are included.
- Live server `/health/ready`: HTTP 200.

Machine-readable test results: `test-results.xml`. Coverage numbers are recorded from the final release run below; coverage is a measure of exercised lines, not proof of production safety.

## Browser checks completed

Using the actual locally served frontend and backend:

1. Opened an isolated demo workspace with four synthetic disputes.
2. Inspected desktop and narrow-panel rendering, table and case drawer. Fixed-size mobile viewport emulation was attempted but did not apply reliably; no particular mobile device size is certified.
3. Opened Alex Morgan's case, generated a template defense from the saved invoice, reviewed and approved the draft.
4. Confirmed the simulation checkbox and submitted. The browser showed **Submitted**, **Demo submission complete**, and a submitted-response count of 1.
5. Verified matching draft approval, submission started, and submission simulated activity entries.
6. Searched for Alex and confirmed exactly one matching case.
7. Checked integration cards: PayPal and AI not connected, carrier verification not connected, text PDF extraction available.
8. Saved the resulting inbox screenshot as `dashboard.png`.

## Explicitly not verified

- Real PayPal sandbox OAuth/scopes, signed event acceptance, live evidence payload acceptance or remote reconciliation. Provider contract behavior was tested with HTTP mocks, not credentials.
- OpenAI model output quality, factual grounding, latency or cost with a real model. Request/response and failure behavior were tested with mocks. Human review remains mandatory.
- PostgreSQL execution on this machine, Docker image/Compose startup, CI execution, deployment, failover, load or million-user capacity. No local PostgreSQL/Docker runtime was available. CI configuration includes a PostgreSQL smoke test, but a written CI workflow is not a completed CI run.
- Independent carrier tracking, OCR for scans/images, binary provider attachments, original-PDF retention, multi-merchant OAuth onboarding. These features are outside this MVP and are identified as such in the UI/docs.
- Comprehensive accessibility audit, every browser/device, adversarial PDF parsing or a third-party security review.

## Environment notes

The first dependency resolver stalled during package metadata fetching; installation succeeded through standard PyPI using pip's legacy resolver. No TLS verification was disabled. An early test run could not access the default Windows pytest temp directory; pytest now uses a workspace-local base directory. Neither issue is represented as an application test failure in the final test report.

The pinned Starlette TestClient emits a deprecation warning for its httpx integration. Tests pass; migration to its recommended test client can be done separately. No production code depends on TestClient.
