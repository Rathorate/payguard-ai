# PayGuard hackathon launch checklist

Updated 31 October 2026. Historical development notes are in [VERIFICATION.md](VERIFICATION.md); current judge access is in [JUDGE_GUIDE.md](JUDGE_GUIDE.md).

## Completed and verified

- [x] Public repository and MIT license.
- [x] Separate Vercel frontend / Render API / dedicated Neon PostgreSQL deployment.
- [x] Exact frontend HTTPS origin, secure sessions and server-only provider credentials configured.
- [x] Actual sandbox OAuth and dispute read/import with the matching seller app.
- [x] Owner-approved replacement merchant workspace mapped; sandbox authentication and PP-R-SLL-10194090 import verified October 31.
- [x] Inquiry observation shows escalation rather than evidence submission. No escalation or evidence write performed.
- [x] Groq analysis, drafting and Q&A exercised with recorded sources.
- [x] Previous hosted tests exercised review acknowledgement, version-bound approval, packet download/checksum and simulated submission.
- [x] Hosted PDF extraction, invalid-PDF rejection and persistence recorded in verification notes.
- [x] Latest code release a2d8a31 passed [CI 41193870893](https://github.com/Rathorate/payguard-ai/actions/runs/41193870893): 234 passing Python checks across the main and PostgreSQL steps; 14 frontend tests.
- [x] Four-case live AI evaluation mechanically passed. This does not complete human quality ratings.
- [x] UptimeRobot monitoring configured. Monitoring does not guarantee uninterrupted free hosting.

## Final rehearsal and personal review

- [ ] Personally review the current recording-case draft against its synthetic sources, correct it and approve the exact saved version.
- [x] At the user's request, the assistant exercised approval, downloaded the packet, verified its checksum/version and completed simulated submission on the fictional recording case. This is a workflow test, not the owner's personal rating.
- [ ] Before making quantitative AI-quality claims, complete human ratings for receipt-only, conflicting-delivery, authorization-missing and untrusted-instructions scenarios. No such claim is currently made.
- [ ] Check recording audio/readability and that no credentials or private customer records appear.
- [ ] Keep public demo access and local setup available throughout judging.

The imported PayPal case and synthetic recording case must remain separate. The synthetic case is fictional and must never be used as evidence for a real dispute. Automated rehearsal is not the user's personal approval.

## Submission

- [x] Hosted app URL and source/setup links available in the README.
- [x] Actual tool usage and integration limits documented.
- [ ] Final project description and required Devpost fields checked against the organizer's current form.
- [ ] Public YouTube demo under three minutes, recorded after the hosted rehearsal.
- [ ] Video URL added and submission completed before the organizer's deadline.

## Deferred provider and production work

Actual PayPal evidence acceptance, external signed webhook delivery/worker processing, broad multi-merchant onboarding, account recovery, OCR, independent carrier verification, backup restoration and load capacity remain follow-up work. Keep DEMO_MODE=true. Do not claim automatic synchronization, provider acceptance, a won dispute or an uptime SLA.

## Latest rehearsal additions

See [RECORDING_REHEARSAL.md](RECORDING_REHEARSAL.md). Three new synthetic review cases remain unapproved, alongside the completed simulation and separate imported inquiry. Credential-free public access was checked by signing out and opening a fresh sample workspace; it loaded four cases and hid merchant import controls. The merchant session was then restored with all five saved cases. The account-switch cleanup clears stale integration details before loading a different workspace; 16 frontend regressions pass locally.
