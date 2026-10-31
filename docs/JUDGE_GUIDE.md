# PayGuard AI: judge guide

## What the product does

PayGuard helps merchants organize PayPal disputes, identify gaps or conflicting statements in evidence, ask source-grounded questions, and prepare a response for explicit human review. It does not decide who is right, determine Seller Protection eligibility or predict dispute outcomes.

Frontend: https://payguard-ai-frontend.vercel.app
Backend: https://payguard-ai-ih99.onrender.com
Source and MIT license: https://github.com/Rathorate/payguard-ai

## Try it with a merchant account

Guest access and the preset four-case loader are disabled on the hosted app. No existing owner's credentials are shared.

1. Open the frontend and select **New here? Create a workspace**, or sign in with your own PayGuard account.
2. A new account starts empty. Choose **Add dispute**, enter a fictional ID such as PP-D-JUDGE-RECEIPT, a customer named Synthetic judge fixture, USD 10, and a future test deadline.
3. Open the case and add an INVOICE record titled SYNTHETIC receipt only with text: "SYNTHETIC TEST: Merchant receipt records payment of 10.00 USD. No shipping or delivery record is provided. Never submit fictional evidence to PayPal."
4. Run evidence checks. From the dashboard you can also select the case in **Case for AI chat** and click **Ask AI**. Ask "Does this receipt prove delivery?" Inspect source excerpts; citations establish recorded text, not truth.
5. Generate a draft, inspect citations, correct statements and save edits. Personally review the saved version before approving. Evidence/draft changes invalidate prior approval.
6. Download the approved JSON packet. It includes the saved version, evidence, review history and checksum; it is not PayPal acceptance.
7. Confirm **Simulate submission**. The response locks and audit records the simulation. Nothing is sent to PayPal.

An unconfirmed approval/submission is blocked. Failed generations preserve saved drafts/reports. Invalid completed Q&A output gets at most one fresh source-constrained answer attempt; source validation remains enforced and provider/quota errors are not automatically retried by that mechanism. Existing provider JSON-schema recovery may also apply. No perfect reliability or factual-accuracy claim is made. Use only synthetic data for judging. Q&A conversation clears on reload/version changes; saved cases persist.

## Actual PayPal versus simulation

The owner connected a matching seller sandbox app and imported the actual $10 test dispute PP-R-SLL-10194090 through PayPal's API. Read-only refresh recorded Inquiry / Waiting for seller response and an escalate action. PayPal did not offer provide-evidence for this case. No escalation or evidence submission was performed. These are actual sandbox reads, not production payment operations. The demo submission is deliberately simulated and must not be represented as PayPal acceptance.

Guest sample sessions are disabled. Merchant workspaces are tenant-scoped, and one merchant workspace per deployment is linked to the configured PayPal seller. A new account does not inherit that seller connection. Credentials remain server-side. To reproduce actual sandbox reads, follow PAYPAL_SANDBOX.md with your own matching seller app, case and deliberately configured workspace mapping. The owner's sandbox import is demonstrated in the video and recorded verification.

## Stack and AI role

- FastAPI, SQLAlchemy and PostgreSQL for tenant-scoped accounts, sessions, cases, approval versions and audit history.
- HTML/CSS/JavaScript on Vercel, forwarding only API traffic to the Render backend.
- Groq openai/gpt-oss-20b for evidence analysis, drafting and case Q&A. Server-owned source passages and independent validators reject invented references and unsupported excerpt strings. Semantic accuracy still needs human judgment.
- Text PDF extraction supports documents up to 5 MB / 20 pages. Scanned/image-only documents require OCR and are not claimed as supported.
- Explicit human approval, CSRF/origin checks, opaque cookies, optimistic version checks and submission idempotency protect the workflow.

## Evidence and remaining limits

Release a2d8a31 passed [GitHub Actions 41193870893](https://github.com/Rathorate/payguard-ai/actions/runs/41193870893). The main Python run passed 232 tests with two PostgreSQL-only skips; the dedicated PostgreSQL step passed both tests, for 234 passing Python checks overall. All 14 frontend tests passed for that release. The subsequent account-switch cleanup adds two regressions, with the subsequent dashboard-chat and guest-access changes bringing the frontend suite to 20 tests; consult [latest CI](https://github.com/Rathorate/payguard-ai/actions) for release status. Hosted verification includes sandbox authentication/import, valid PDF extraction, malformed PDF rejection, saved AI analysis, approved packet checksum verification, guarded simulation and persistence after reload/redeploy. Test coverage does not establish perfect accuracy or uptime.

UptimeRobot checks the database-free /health/live endpoint every five minutes. HEAD support and an Up status were verified when the monitor was configured on October 23; this is not a live status report. Render Free shares 750 running hours per month across this workspace's free services; quotas, restarts, database cold starts and upstream failures still apply. No uptime SLA is claimed. Keep hosted access or complete local setup available throughout judging.

The user completed the four-case live AI evaluation with all mechanical checks passing. The report's human ratings remain pending; assistant review found semantic/privacy issues that prompted additional guards and manual corrections. Mechanical success is not an accuracy score. No quantified time-saving, accuracy or dispute-win claim has been established. Dedicated carrier verification, image OCR, automatic webhook processing, broad multi-merchant onboarding and load testing remain outside this MVP.

## Suggested demo story (under three minutes)

Show the merchant problem, then one synthetic conflicting-evidence case: inspect sources, ask a question, show an AI draft, correct a statement, approve the exact saved response, download the packet and simulate submission. Briefly show the actual sandbox import/status panel and clearly distinguish its read-only API integration from simulation. End with the intended merchant benefit and the limits demonstrated. Use real measured results only; never imply recovery of money or a won case.

## Connection troubleshooting

Sign in to the intended merchant account. A new regular account starts empty and is not automatically linked to PayPal. The administrator must deliberately map the intended workspace; existing cases are not migrated automatically. PUBLIC_DEMO_ENABLED=false disables guest login, preset sample loading and existing sample-session access while preserving merchant cases. DEMO_MODE=true independently keeps submissions simulated.
