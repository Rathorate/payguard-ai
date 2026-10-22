# Evidence review structured output and diagnostics - 22 October 2026

- User logs and an authenticated browser inspection verified actual app import of PP-R-SLL-10194090, live Groq draft generation and saved evidence analysis. The case remains unapproved. One analysis request failed and a later one succeeded; the historical HTTP status alone does not establish the provider/validation cause. Inspection found irrelevant authorization gaps for an item-not-received case and missing delivery-gap guidance; instructions were refined accordingly.
- Browser checks on the user's running Ubuntu app confirmed unchecked approval is blocked, citation buttons open the real imported snapshot, and unsaved-edit protection offers Keep editing/Discard. The original buffer was restored without saving or changing the case. No console errors were captured in this fresh inspection. These checks did not approve or submit the imported case.
- Added case-specific read-only Q&A with exact source excerpts, bounded follow-up history, suggested prompts and conversation clearing. Questions cannot alter the draft, approve or submit. Focused backend regression: 63 passed; eight frontend tests passed including safe Q&A rendering. AI diagnostics now distinguish provider quota/server availability (503) from rejected model output (502), with safe server metadata logging. The new Q&A feature still needs a credentialed browser rehearsal after pulling and restarting the updated app.
- Complete local regression for this feature: **179 passed, 2 skipped**, 91% line coverage; eight frontend tests, syntax/build/config and dependency checks passed. Local skips require disposable PostgreSQL, exercised separately in CI. The non-failing Starlette TestClient/httpx warning remains.
- First live Q&A on the imported case was rejected with QUOTE_MISMATCH; no draft or approval changed. Q&A now selects immutable passage refs instead of asking the model to recopy JSON. The backend attaches original excerpts and revalidates them. Analysis schema quotes are also constrained to supplied exact passages, with source-ID pairing still independently checked. Ten focused Q&A regressions passed after this change. Browser-only fixture checks separately verified form submission, follow-ups and clearing with explicitly labeled UI_TEST answers; these do not count as live Groq quality verification.
- Full local regression after passage selection: **180 passed, 2 skipped**, 91% coverage. An additional explicit analysis-refresh regression verifies caching, preservation of the saved report on failure and replacement after validation without changing case version. Eight frontend tests passed. Refresh controls allow requesting new guidance after prompt improvements rather than silently returning an old report. Browser fixture testing also confirmed a saved edit clears the previous case-version conversation.
- Screenshot fixes: browser Unicode-set input patterns now escape the hyphen; a public SVG favicon and MIME mapping remove the missing-icon request on fresh loads; authentication/import feedback is separate. The import field explains case ID versus app fingerprint, and both browser and API reject a fingerprint before contacting PayPal. Actual case PP-R-SLL-10194090 was previously verified readable; the screenshot used fingerprint 4335355d648c as a case ID, causing the provider 404. A genuine upstream case-not-found result is now returned as HTTP 404 on import rather than a generic 502.
- The latest pasted live report contained two missing-link drafts, an incomplete generation and a Groq 429. Groq drafting now requests structured paragraphs with declared source IDs. The backend validates and renders exact bracket references, rejecting invented IDs or malformed output without repairing it. This does not establish claim entailment or replace human approval. GPT-OSS uses low reasoning effort with hidden reasoning; incomplete responses remain failures, with a safe finish reason.
- The evaluator defaults to 35 seconds between AI calls and stops further calls on a provider 429, marking remaining scenarios not run. Bounded Retry-After metadata is exposed when supplied. This reduces burst pressure; it does not remove account quotas or prove provider failures are eliminated.
- Local final regression: **170 passed, 2 skipped**, 91% line coverage; **7 Node tests passed**, including browser-v-pattern compilation, fingerprint rejection and SVG delivery. Frontend configuration, JavaScript syntax and dependency compatibility checks passed. One non-failing Starlette TestClient/httpx deprecation warning remains. PostgreSQL is checked separately in CI. Revised credentialed Groq drafting and the actual app import still require Ubuntu verification after restarting servers.
- The user supplied the full later four-case live report. Revalidating its structured analyses against the supplied evidence succeeded. Assistant review found two drafts with zero linked square-bracket citations, an unnecessary request for card last-four details and overly broad required-document language. This is not user approval or a human quality score; see AI_SAMPLE_REVIEW.md.
- Tightened draft instructions and added a minimum linked-source check to the evaluator. Prior zero-link outputs now fail rather than receiving a misleading mechanical pass. Focused provider/evaluator regression: 37 passed, including parenthesized IDs, non-ASCII hyphens, absent references, invented IDs and valid linked references. Revised live quality still needs credentialed verification; no source quotes were repaired or fabricated.
- Follow-up Ubuntu run: 140 Python tests and six frontend tests passed. Receipt-only, conflicting-delivery and untrusted-instructions now passed live mechanical checks; authorization-missing returned Groq HTTP 400. Human quality assessment is still pending. This does not prove the remaining failure's cause; the old HTTP handler discarded the provider code and the console omitted the task stage.
- Added allowlisted Groq HTTP error diagnostics and explicit failed-stage reporting. A --case option supports a bounded single-scenario diagnostic, labeled separately from a full evaluation. There are no automatic retries, raw upstream error bodies or fallback passes. Focused regression: 58 passed, including unknown/malformed error metadata, private-message exclusion, one-request failure behavior and draft-versus-analysis error reporting.
- User's Ubuntu regression: 134 Python tests and six Node tests passed; two PostgreSQL tests skipped locally. Live Groq evaluation then rejected receipt-only and untrusted-instructions reviews. Conflicting-delivery and authorization-missing passed mechanical checks; human ratings remained pending. The old evaluator did not retain rejected output, so the exact validation failures cannot be determined from that run.
- Added strict JSON Schema requests for Groq GPT-OSS 20B/120B evidence analysis, JSON object mode for other Groq models, and explicit verbatim excerpt instructions. Plain-text drafting is unchanged. Independent exact-quote/source validation remains mandatory; no automatic retry or acceptance of altered quotations.
- Validation errors now provide safe reason codes and field paths. Only the synthetic evaluator retains rejected model text in its local, git-excluded report. Customer-case error responses do not include that content. Duplicate JSON keys are rejected.
- Updated local regression: **140 passed, 2 skipped**, 91% line coverage, six Node tests passed, frontend deployment-config check with a test HTTPS origin, JavaScript syntax and Python dependency check passed. Both local skips need disposable PostgreSQL; CI runs those separately. One non-failing Starlette TestClient/httpx deprecation warning remains. The final safe-error assertion also passed separately.
- Live evaluation of this change requires the user's Groq configuration in Ubuntu. Preserve the previous report and run the updated evaluator to a new output path; passing mocked checks is not evidence of live model quality or factual correctness.
- User verified the correct sandbox app fingerprint 4335355d648c, seller dispute-read scope, dispute list and actual GET of PP-R-SLL-10194090 in WAITING_FOR_SELLER_RESPONSE. App import, current AI-assisted case review and actual seller evidence submission are still unverified. No deployment was performed.

Earlier records describe previous builds.

# Evidence review and human decision history - 22 October 2026

- Full local regression: **134 passed, 2 skipped**, 90% line coverage. Both PostgreSQL tests require CI's disposable database. Six Node tests passed, including escaping of untrusted model findings, quotes, identities and draft text. JavaScript/Bash syntax, frontend build/config and Python dependency checks passed.
- New evidence analysis accepts only bounded findings with exact excerpts from existing source records; conflicts require two distinct records. Tests cover hallucinated excerpts, invalid JSON, stale model results, private tenant access, CSRF, caching, limits and immutable submitted/resolved cases. Analysis never approves or submits.
- Unknown draft references block approval and submission. Paragraph source linking does not establish claim truth. Draft revisions retain generation, edits, approvals and withdrawals with version/actor/time; approved packet exports include review history. Earlier builds have no reconstructed history.
- Browser verification on separate local ports 3102/8102 confirmed offline analysis errors preserve the case, template generation creates history, citation links expand the source, human saves flag unknown references, and the original output remains visible beside the edited response. These browser checks used templates, not a live Groq analysis call.
- Added a four-case synthetic Groq/OpenAI evaluation runner, with mechanical checks and pending human ratings. Its orchestration/failure handling is mocked in tests; actual live quality evaluation remains pending on the user's configured Ubuntu environment.
- The user independently verified actual PayPal sandbox OAuth authentication. A $10 sandbox product checkout link was prepared in the seller dashboard. No completed test purchase, real dispute retrieval, evidence submission or cloud deployment has yet been verified.
- Additive migration 002_review_history.sql and refreshed schema/OpenAPI are included. Demo startup adds missing tables; non-demo installations need the explicit migration.
- A subsequent export regression rejects packets if the case changes during assembly, and history queries exclude future case versions. The additive migration is transactional.
- Later sandbox UI work completed a $10 synthetic goods/services transaction and created a clearly labeled item-not-received dispute between US test accounts. The default NG buyer rejected Send and the default NG seller rejected receiving; these were observed provider-account errors. A new approved sandbox app has Customer disputes selected. The user's credentialed dispute GET still returned 403; actual API import remains unverified. Added fingerprint/scope/list diagnostics to distinguish wrong app, missing scope and case ownership without printing credentials.
- Regression collection removes inherited application credentials/configuration so tests remain offline/disposable even from a configured developer terminal. A rate-limit test crossed a real minute boundary and failed once; rate-window tests now use a controlled clock and verify recovery in the next window. This corrects the test expectation without changing server limits.

Earlier records describe previous builds.

# PayPal sandbox integration - 22 October 2026

- Local Python regression: **96 passed, 2 skipped**, 90% line coverage. The two PostgreSQL tests require a disposable database and run separately in CI. One non-failing Starlette TestClient/httpx warning remains.
- Four Node tests, frontend build/config validation with a test HTTPS backend origin, JavaScript/Bash syntax and Python dependency checks passed.
- Added sandbox OAuth diagnostic, validated dispute import and an Integrations UI. Mocked provider tests cover authentication shape, 401/403/404/429/500, malformed amounts/deadlines, mismatched IDs, duplicate preservation, merchant mapping, CSRF, rate limits and imported-case drafting/approval/simulation.
- Provider deadline changes invalidate approval while preserving the draft; regression coverage added.
- Actual merchant authentication, dispute permissions and real sandbox retrieval remain pending credentialed verification. These tests created no payment, sent no evidence and performed no cloud deployment.
- User-approved MIT license included, copyright 2026 Rathorate.

Earlier records describe previous builds.

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
