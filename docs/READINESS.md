# PayGuard readiness and remaining gaps

Updated 31 October 2026. See [judge instructions](JUDGE_GUIDE.md), [launch checklist](LAUNCH_CHECKLIST.md) and [verification record](VERIFICATION.md).

## Verified hackathon MVP

- Public repository with MIT license.
- Separate Vercel frontend, Render API and dedicated Neon PostgreSQL database.
- Merchant sign-in/registration with tenant-scoped persistent cases. Guest login and preset sample loading are disabled by default; new merchant accounts start empty.
- Actual PayPal sandbox authentication and import of PP-R-SLL-10194090. The owner-approved replacement workspace mapping was verified October 31. Older workspaces retain their saved cases but are not migrated automatically.
- Groq evidence analysis, case Q&A and drafting; source excerpts, citation inspection and retained draft/edit/approval history.
- Explicit review and version-bound approval, approved JSON packet export, separately confirmed simulated submission and locked response after submission.
- Hosted valid-PDF extraction, malformed-PDF rejection and persistence checks recorded in the verification documents.
- Release a2d8a31: [CI 41193870893](https://github.com/Rathorate/payguard-ai/actions/runs/41193870893) passed 232 main-suite Python tests plus two dedicated PostgreSQL tests, and 14 frontend tests. Locally the two PostgreSQL tests were skipped. A non-failing Starlette TestClient deprecation warning remains.
- User's four-case live AI evaluation passed mechanical checks. Human quality ratings remain pending; an assistant review is not a human assessment.

## What the human does

Compare every statement with its source; recorded merchant statements are not independently verified delivery or authorization. Edit and save the response, then approve only the exact version personally reviewed. Changes to evidence or draft invalidate approval. A separate acknowledgement is required for simulation. These are account-level review controls, not an independent two-person approval system; the application cannot prove someone read the evidence.

## Before recording and submission

1. Rehearse one clearly labeled synthetic case through evidence, AI analysis, Q&A, editing, personal review, approval, packet download and simulated submission.
2. Keep the actual sandbox case separate from fictional recording evidence. Its Inquiry observation offers escalation, not provide-evidence. Do not escalate merely to unlock a demonstration feature.
3. Complete human assessments of the four synthetic AI scenarios. Do not derive an accuracy, time-saving or dispute-win metric from mechanical tests.
4. Verify merchant registration/sign-in and prepare the public video and submission text. Describe actual PayPal reads separately from simulated submission.
5. Keep hosted access or complete local instructions available throughout judging. Free hosting, provider quotas and cold starts do not provide an uptime SLA.

## Production follow-up, outside the hackathon demo

| Gap | Required work |
|---|---|
| Account recovery and onboarding | Email verification, password recovery and deliberate multi-merchant connection onboarding. New accounts do not inherit the configured seller connection. |
| Real PayPal writes | Validate permitted account-specific payloads, signed webhooks, provider transitions, ambiguous-result reconciliation and actual evidence acceptance in sandbox before enabling real submissions. |
| Operations and customer data | Retention/deletion policy, tested backups/restores, abuse and cost controls, secret rotation and operational alert handling. |
| Evidence verification | Original-document storage with access controls, scanned-document OCR, carrier integration and source provenance. Current PDF uploads extract text only. |
| Scale | Load tests, query/index analysis, connection limits and durable job capacity. Millions of users have not been demonstrated. |
| Independent approval | Explicit roles and distinct reviewer identity if a two-person approval policy is needed. |

## Database and migration limits

Demo-mode startup can create additive tables; existing non-demo databases need documented migrations, including 001 audit actor width and 003 workflow observations. This is not a full migration system. Back up before migrations.

## AI and integration limits

AI may omit relevant gaps, generate irrelevant advice, or fail despite schema recovery. Known references and exact excerpts establish source text, not factual entailment. Failed requests preserve saved drafts/reports. Human review remains necessary. The deployment supports one connected PayPal merchant, notes-only provider submission, manual refresh, no reconciliation UI, no independent carrier verification and no image OCR. Do not claim real evidence acceptance, Seller Protection eligibility, money recovery or perfect accuracy.
