# PayGuard readiness and remaining gaps

## Current hackathon status

The core local demonstration is working: synthetic cases, evidence entry/text PDF import, a real Groq-generated case response, merchant edits, explicit review and approval, withdrawal/reapproval, approved JSON export, and clearly simulated PayPal submission.

On 22 October 2026 the user ran scripts/verify-ai.sh successfully with Groq's openai/gpt-oss-20b. The running frontend on port 3001 also generated a real Groq response for a fresh synthetic case. The browser test then blocked unchecked approval, saved an edited response, approved/withdrew/reapproved it, blocked unchecked submission, and completed a simulation that locked the response. No real PayPal submission occurred.

The real draft requested an unnecessary tax ID. It was edited out before the synthetic approval test. Drafting instructions now prohibit unnecessary identity/payment credentials and keep the response in the merchant's voice. This improves guidance, but does not certify model factual quality. Mandatory review remains necessary. Further live evaluation of the revised prompt requires pulling the new source and restarting the backend.

## What the human does

New evidence-review tooling is documented in EVIDENCE_REVIEW.md: version-bound AI findings with exact excerpts, paragraph-level citation inspection, server rejection of unknown references, retained generated/edit/approval history and a synthetic evaluation runner. These controls need a live Groq rehearsal after pulling and restarting; exact citations are not proof of factual entailment. Existing older responses have no retroactive revision history. UI redesign remains a later step after sandbox and hosted verification.

1. Compare every claim with the actual evidence and check the provider deadline.
2. Edit or replace the response when evidence is incomplete, inaccurate or irrelevant. A receipt alone does not establish delivery or authorization.
3. Save the response, check the review acknowledgement, and approve its exact current version.
4. Withdraw approval to reconsider. Evidence or draft changes require another approval.
5. Make a separate submission acknowledgement. Demo submissions remain simulations.

The server independently enforces versions, approval and confirmation; hiding or bypassing a browser button does not bypass those checks. The audit records the account performing an action. This is a single-merchant review workflow, not independent approval by a second employee. The application cannot prove that someone actually read the evidence.

Review edits now have Keep editing/Discard edits protection. Case controls are locked while a request is pending, including while the UI reloads a saved case, so a slow generation cannot overwrite newly typed edits. Out-of-order case loads cannot replace the most recently opened case.

## Priorities

| Priority | Gap | What bridges it |
|---|---|---|
| Before the hackathon presentation | Repeatable demo and AI quality checks | Rehearse received/not-received, unauthorized, incomplete and contradictory evidence. Check citations, unsupported claims, irrelevant requests and missing facts. Keep synthetic fixtures and a template fallback. |
| Before public hosting | Actual cloud verification | Deploy separate frontend/API, configure exact HTTPS origin and secure cookies, managed PostgreSQL, server-only keys, health checks and provider limits. Test login, upload, draft, review, export and simulation through the hosted frontend. Local proxy tests do not establish cloud behavior. |
| Before accepting real customer data | Account recovery, access controls and data lifecycle | Email verification/password recovery, team roles if needed, retention/deletion policy, tested backups/restores, operational alerts, secret rotation and abuse/cost controls appropriate to public traffic. |
| Before real PayPal submission | Account-specific API integration validation | Obtain eligible sandbox access; validate merchant mapping, scopes, verified webhooks, notes limits, provider status transitions and ambiguous-result reconciliation. Keep the manual packet/simulation until this is done. |
| If two-person approval is required | Reviewer separation | Add explicit roles, distinct reviewer identity and an enforced second-person approval policy. Do not describe the current acknowledgement as independent review. |
| If stronger evidence handling is required | Source documents and verification | Object storage/original-file retention with access controls, OCR for scanned PDFs, carrier verification and source provenance. Current uploaded PDFs produce extracted text only. |
| Before substantial scale | Measured capacity and operations | Load testing, indexes/query analysis, bounded database connections, rate-limit/proxy behavior under real hosting, AI concurrency/cost limits and durable job processing as needed. Millions of users have not been demonstrated. |

## Existing database note

Audit actor length now matches the accepted email length (254 characters). Fresh PostgreSQL schemas use the corrected width. For an older PostgreSQL database, back it up and apply docs/migrations/001_audit_actor_length.sql before using this build. SQLite needs no length alteration. Broader versioned migrations remain a production follow-up; this one repair is not a complete migration system.

## Remaining explicit limitations

There is one configured PayPal merchant per deployment, no reconciliation UI for unknown submissions, no original-file retention or image OCR, no carrier proof verification, and no proven million-user capacity. The Starlette TestClient/httpx warning is non-failing development tooling noise; dependency modernization can be done separately with its own regression run.

The hackathon requires meaningful PayPal developer platform integration. AI and human judgment can be rehearsed offline, but CSV/manual cases and simulation alone should not be assumed sufficient. Verify an actual sandbox dispute read and demonstrate its data flowing through AI drafting and human review. Confirm eligibility with organizers; avoid claiming provider acceptance or a dispute win.

Sandbox authentication and import have mocked transport regression coverage. The user verified actual sandbox authentication from Ubuntu. Dispute permissions, an actual sandbox purchase/dispute and retrieval remain pending. See PAYPAL_SANDBOX.md. The approved MIT license is included.
