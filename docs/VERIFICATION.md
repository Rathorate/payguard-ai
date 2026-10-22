# Human review hardening and live Groq rehearsal - 22 October 2026

- The user verified a real Groq connection from Ubuntu. A separate browser test on port 3001 confirmed the running app selected Groq and generated a real response for a fresh synthetic case.
- The draft remained In review. Unchecked approval was blocked. The response was edited to remove irrelevant requests, saved, approved, withdrawn, reapproved, and then submitted only after a separate simulation acknowledgement. The final response was locked, with nothing sent to PayPal.
- This sample requested an unnecessary tax ID. Drafting instructions were tightened to avoid irrelevant sensitive-data requests and provider-role confusion. The revised instructions pass adapter regressions; wider live quality evaluation remains open.
- Browser checks of the updated local frontend verified manual evidence saving, Keep editing preserving unsaved text, saving that text, unchecked-review rejection, and deliberate Discard edits preserving the prior saved server response. Case actions now lock editing during pending requests and ignore superseded case loads.
- Full local API regression: **67 passed, 2 skipped**, 91% line coverage. Both skips require disposable PostgreSQL. The new PostgreSQL regression covers long accepted email addresses in the audit trail; the actor column and fresh schema were widened to 254, with a repair SQL script for older PostgreSQL installations.
- A later targeted provider regression passed **19 tests** after the prompt update. Four Node tests, JavaScript syntax, frontend build/config checks, contract export and whitespace checks passed. No failing local checks remain in the completed runs.
- Live PayPal submission and cloud hosting remain unverified. See READINESS.md for the prioritized gaps and current product limits. No deployment was performed.

Earlier records below describe previous builds.

# AI visibility and local retest - 22 October 2026

- Latest full Python suite: **67 passed, 1 skipped**, 91% line coverage. The skip needs disposable PostgreSQL. One non-failing Starlette/httpx deprecation warning remains.
- Four Node tests, JavaScript syntax, frontend build/config checks, Bash syntax for both launchers, dependency compatibility and whitespace checks passed.
- Port 3001 was reachable with HTTP 200 during diagnosis. Its actual Integrations screen reported **Selected provider: template**, so no live Groq verification is claimed for that process. WSL command execution and the Ubuntu .env were inaccessible; no key was read or displayed.
- An actual new interactive-demo login loaded four sample cases. The empty state is reproducible for regular registered accounts. Their global demo-mode label previously also called them Interactive demo; this misleading label is fixed.
- The inbox now has an AI assistant panel, running provider/model status, a synthetic connection test with explicit errors, and an empty-workspace-only fixture loader. A key present while AI_PROVIDER=template is explicitly diagnosed.
- Groq HTTP 401/403/404/429 failures now provide specific, sanitized next steps. Tests verify errors do not leak upstream messages or secrets, alter disputes, approve drafts or submit responses. AI connection checks are authenticated, CSRF-protected and rate limited.
- Browser retest: registered an empty fixture account, saw the AI panel and sample loader, verified the missing-configuration error, loaded four cases, generated a template, blocked unchecked approval, blocked approval while unsaved, saved/approved/withdrew/reapproved, blocked unchecked submission, then simulated submission successfully. The response was locked afterward.
- The actual launcher preflight was executed against free and occupied ports. It reports occupied ports before starting services and never prints API keys. Explicit FRONTEND_PORT/BACKEND_PORT arguments take precedence over .env port settings.
- No cloud deployment or real PayPal submission occurred. Real Groq validation still requires the running backend to load the user's saved key and select Groq. scripts/verify-ai.sh offers a safe synthetic live check in Ubuntu.

Earlier records below describe previous builds.

# Human review and Groq verification - 22 October 2026

- Complete local Python suite: **57 passed, 1 skipped**, 91% line coverage. PostgreSQL requires a disposable database and was skipped; no local Docker/PostgreSQL executable was available.
- **4 Node tests passed**; frontend build/config check, JavaScript syntax and dependency compatibility checks passed.
- Added explicit boolean acknowledgement validation, approval withdrawal, approved-version packet export, Groq provider selection and failure handling, and simultaneous-submission coverage.
- Real browser checks used separate local Node and Uvicorn processes on ports 3101 and 8101: login, open case, generate template, block unchecked approval, change draft, disable approval while unsaved, save and re-review, approve, download JSON packet, withdraw approval, reapprove, block unchecked submission, simulate submission and verify locked response.
- Browser packet download returned an actual local JSON file. Screenshot: human-review-verified.png. The browser download observer was slow; API attachment content and headers are independently tested.
- Groq tests mock successful, malformed, truncated, timed-out, rate-limited and failed responses. No real Groq call was made because no key was provided. Factual quality still needs a credentialed rehearsal with synthetic evidence.
- PayPal is simulated, including when credentials exist in demo mode. Real PayPal calls, cloud deployment, Docker startup, managed PostgreSQL and load capacity remain unverified. Nothing was deployed.
- Starlette emits one non-failing TestClient/httpx deprecation warning. It is not the cause of a frontend connection reset.
- Ubuntu cannot be controlled from this session (WSL access denied); the verified servers run locally on Windows. Pull the code and run the same test launcher in Ubuntu to validate that environment.

Earlier verification records below are historical.

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
