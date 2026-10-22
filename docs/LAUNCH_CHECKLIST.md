# PayGuard hackathon launch checklist

## Completed locally

- [x] Actual sandbox OAuth, dispute list/read and import with matching seller app.
- [x] Read-only workflow refresh shows INQUIRY and supported escalate action for PP-R-SLL-10194090. No provide-evidence action was returned in that observation.
- [x] User added clearly labelled synthetic tracking, clearing the old draft and invalidating review at case version 3.
- [x] Actual Groq evidence checks identified missing shipment/delivery proof, not verified delivery.
- [x] Actual Groq draft at case version 4 explicitly describes fictional tracking and does not establish delivery.
- [x] Actual Groq Q&A explains that the tracking reference demonstrates a workflow, with links to both sources.
- [x] Unchecked human review acknowledgement blocks approval. The imported case remains unapproved.
- [x] Previous application release 40c8762 passed GitHub Actions 39802191339, including PostgreSQL. Each later release requires its own CI result.

A later analysis request failed safely with provider code json_validate_failed and left the saved draft intact. The follow-up release shares the simpler passage-reference protocol already used by Q&A. Its live provider verification remains separate from offline regressions.

## Human review gate

- [ ] Read the exact latest saved draft and its source excerpts. Synthetic tracking is demonstration data, never evidence for a real dispute.
- [ ] Correct inaccurate or irrelevant assertions; save before acknowledging approval.
- [ ] Approve only the version actually reviewed. Then test packet download and, if desired, clearly simulated submission with DEMO_MODE=true.
- [ ] Do not automatically escalate the sandbox case to unlock a feature. Escalation and available follow-up actions must be deliberately reviewed in PayPal.

## Deployment configuration, before creating resources

Frontend: existing repository, root frontend, Vercel Other preset, server-side deployment BACKEND_ORIGIN set to the resulting backend HTTPS origin. Never put provider keys or database credentials in the frontend project.

Backend: existing repository root, Python 3.12+, pip install -r requirements.txt, start uvicorn app.main:app --host 0.0.0.0 --port $PORT --no-proxy-headers, readiness /health/ready. DEMO_MODE=true, PAYPAL_ENVIRONMENT=sandbox, SECURE_COOKIES=true, APP_ORIGIN exactly the resulting frontend HTTPS origin. Use a separate managed PostgreSQL database, not local SQLite or another project's database. Preserve Groq settings privately on the backend. Map the newly hosted merchant workspace ID after account creation; the local SQLite workspace ID is not automatically the hosted workspace ID.

The confirmed Render workspace is My Workspace. Its existing free database cropgrid-staging-db belongs to another project. No PayGuard resource was present during read-only discovery. Choose a separate durable database and review any paid resource before creation. Render free web services can sleep and share workspace usage limits; free Render Postgres has a one-instance limit and 30-day expiry. A judge demo must remain available for the judging period. Current reference: https://render.com/docs/free

- [ ] Choose hosting/database plan and review concrete recurring charges, if any.
- [ ] Create isolated PayGuard services/database after configuration and funding decisions.
- [ ] Add secrets privately; initialize new schema. Existing non-demo databases need versioned migrations, including 003.
- [ ] Verify backend readiness, then frontend HTTPS login and session reload.
- [ ] Verify exact Origin and CSRF enforcement through the hosted rewrite, upload, AI, edits, approval, packet export and simulated submission.
- [ ] Verify restart persistence in managed PostgreSQL and provider quota/error states.
- [ ] Provide an isolated judge account or explicit demo access with synthetic data, tools disclosure and instructions.

## Webhook and actual PayPal writes

Signed webhook acceptance and worker processing have offline transport regression coverage. Actual external delivery cannot be certified without an accessible backend URL and configured webhook ID. Configure the sandbox webhook only once the backend is reachable; verify signature, deduplication, queued processing and case version/approval invalidation. Decide whether a separate worker is in scope and review its hosting cost. Keep manual refresh available and avoid claiming live automatic synchronization until tested.

Actual PayPal evidence acceptance remains unverified. Current case action availability blocks sending evidence. Recheck the authoritative provider response and required payload before any explicit sandbox write rehearsal. Never enable live-money operation for this hackathon demonstration.

## Submission after the hosted rehearsal

- [ ] Public source and MIT license, current architecture/API/setup documentation.
- [ ] Actual app/tool usage and limitations accurately disclosed.
- [ ] Real end-to-end demo story with measured observations, no invented savings/win rates.
- [ ] Public YouTube video under three minutes, recorded after the hosted flow works.
