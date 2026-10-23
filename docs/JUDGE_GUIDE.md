# PayGuard AI: judge guide

## What the product does

PayGuard helps merchants organize PayPal disputes, identify gaps or conflicting statements in evidence, ask source-grounded questions, and prepare a response for explicit human review. It does not decide who is right, determine Seller Protection eligibility or predict dispute outcomes.

Frontend: https://payguard-ai-frontend.vercel.app
Backend: https://payguard-ai-ih99.onrender.com
Source and MIT license: https://github.com/Rathorate/payguard-ai

## Try it without credentials

1. Open the frontend and choose **Open interactive demo**. A separate sample workspace contains four synthetic cases. No personal PayPal account or payment is needed.
2. Open a case. Inspect its recorded evidence and evidence preparation checklist.
3. Choose **Check evidence with AI**. Inspect linked excerpts and missing/conflicting facts. A source link establishes recorded text, not truth.
4. Ask a question such as "Does this receipt prove delivery?" AI answers cannot edit, approve or submit the case.
5. Generate a draft. Inspect citations, correct statements, save edits, then personally review the exact saved version before approving it. Adding evidence or editing the draft invalidates earlier approval.
6. Download the approved JSON packet. It contains the saved version, evidence, review history and a checksum. It is not a PayPal receipt or acceptance notification.
7. Confirm **Simulate submission**. The response locks and the audit log records the simulation. Nothing is sent to PayPal.

An unconfirmed approval/submission is blocked. Failed AI generations preserve saved drafts/reports. Groq calls can hit quotas or fail even with bounded recovery; the UI reports failures explicitly. Do not supply private customer evidence in the public demo. Refreshing a page clears temporary Q&A conversation, while saved case data persists in PostgreSQL.

## Actual PayPal versus simulation

The owner connected a matching seller sandbox app and imported the actual $10 test dispute PP-R-SLL-10194090 through PayPal's API. Read-only refresh recorded Inquiry / Waiting for seller response and an escalate action. PayPal did not offer provide-evidence for this case. No escalation or evidence submission was performed. These are actual sandbox reads, not production payment operations. The demo submission is deliberately simulated and must not be represented as PayPal acceptance.

The public sample workspace is isolated from the owner's connected merchant workspace. One merchant workspace per deployment is supported. Credentials remain server-side. Judges can test the complete synthetic workflow without being given the owner's credentials. To reproduce actual sandbox reads independently, follow PAYPAL_SANDBOX.md with your own seller app, matching case and workspace mapping.

## Stack and AI role

- FastAPI, SQLAlchemy and PostgreSQL for tenant-scoped accounts, sessions, cases, approval versions and audit history.
- HTML/CSS/JavaScript on Vercel, forwarding only API traffic to the Render backend.
- Groq openai/gpt-oss-20b for evidence analysis, drafting and case Q&A. Server-owned source passages and independent validators reject invented references and unsupported excerpt strings. Semantic accuracy still needs human judgment.
- Text PDF extraction supports documents up to 5 MB / 20 pages. Scanned/image-only documents require OCR and are not claimed as supported.
- Explicit human approval, CSRF/origin checks, opaque cookies, optimistic version checks and submission idempotency protect the workflow.

## Evidence and remaining limits

Core reliability update a82e63e passed GitHub Actions 39937591434, including the PostgreSQL test step. Offline tests: 222 passed and 2 PostgreSQL-only skips locally, plus 10 frontend tests. Hosted checks include valid PDF extraction, malformed PDF rejection, saved AI analysis, exact approved packet checksum verification, guarded simulation and persisted locked response after reload/redeploy. Test coverage does not establish perfect accuracy or uptime.

UptimeRobot checks the database-free /health/live endpoint every five minutes. It currently reports Up after HEAD support was added. Render Free shares 750 running hours per month across this workspace's free services; quotas, restarts, database cold starts and upstream failures still apply. No uptime SLA is claimed. Keep hosted access or complete local setup available throughout judging.

Outstanding evaluation: repeat the four-case live AI report after the recovery change and obtain human ratings. No quantified time-saving, accuracy or dispute-win claim has been established. Dedicated carrier verification, image OCR, automatic webhook processing, broad multi-merchant onboarding and load testing remain outside this MVP.

## Suggested demo story (under three minutes)

Show the merchant problem, then one synthetic conflicting-evidence case: inspect sources, ask a question, show an AI draft, correct a statement, approve the exact saved response, download the packet and simulate submission. Briefly show the actual sandbox import/status panel and clearly distinguish its read-only API integration from simulation. End with the intended merchant benefit and the limits demonstrated. Use real measured results only; never imply recovery of money or a won case.
