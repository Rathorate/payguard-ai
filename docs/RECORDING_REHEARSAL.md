# Recording rehearsal — 31 October 2026

Use the [hosted app](https://payguard-ai-frontend.vercel.app) and the [judge guide](JUDGE_GUIDE.md).

## Prepared owner recording case

The replacement merchant workspace contains PP-D-DEMO-VIDEO-1031, customer **Synthetic recording customer**. It is a manually created fictional case, separate from the imported PayPal sandbox inquiry. Its two records deliberately conflict: the merchant note claims delivery and the buyer message says non-receipt. No carrier proof is attached.

Actual Groq analysis identified the conflict. The first analysis omitted a missing-proof finding; case Q&A identified that gap, and a later analysis at saved version 5 explicitly flagged absent independent carrier/scan/signature evidence. This illustrates model variation and why human review is necessary. The draft was edited by the assistant under owner authorization to label it fictional, preserve both references and leave the disagreement unresolved. Its MERCHANT edit-history label reflects the account used, not proof that the human owner typed the edit.

At the user's explicit request, the assistant exercised the review acknowledgement and approval as a synthetic workflow test. Approval was retained at version 6, the downloaded demo packet's SHA-256 checksum and review/case versions matched, and simulated submission locked the case at lifecycle version 8. This records a test of the controls, not the human owner's quality rating. No real PayPal submission occurred. Use another open synthetic scenario for a fresh recording of review and approval.

## Rehearse the final steps

1. Show the synthetic case title and evidence. Keep credentials, account settings and unrelated records off camera.
2. Inspect the saved conflict and missing-proof findings. Explain that citations link to source text, not independent truth.
3. Ask: "Do these records prove delivery? What independent records are missing?" Q&A clears on reload or case-version changes; record that part before navigating away if desired.
4. Compare the generated response with the edited saved version. Explain the correction.
5. Personally review and approve. Download the approved JSON packet and inspect its version.
6. Check the separate simulation acknowledgement and use Simulate submission. This locks the demonstration response. Nothing is sent to PayPal.
7. Show the real sandbox inquiry's read-only status separately. Its observed available action is escalation, not evidence submission. Do not escalate or mix fictional evidence into it.

Additional open scenarios in the same merchant workspace are PP-D-DEMO-RECEIPT-1031, PP-D-DEMO-AUTH-1031 and PP-D-DEMO-INQUIRY-1031. They cover a receipt without delivery proof, missing authorization and embedded instructions in an inquiry. They are fictional and can be reviewed or rejected. During rehearsal the inquiry draft incorrectly called the case amount a recorded payment; it was corrected before any approval. Retained generation/edit history demonstrates why source review is necessary. Do not present every generated response as accurate. For another repeat recording after these are locked, use a fresh interactive-demo workspace. Do not claim the public sample workspace is connected to the owner's PayPal merchant.

## Claims supported by the demonstration

PayPal sandbox authentication/read/import, AI-assisted evidence preparation and Q&A, explicit personal review, version-bound approval, JSON packet export and simulated submission.

## Claims not established

PayPal evidence acceptance, a won dispute, money recovered, accuracy/time-saving percentages, fully automatic synchronization, independent two-person approval, always-on free hosting or million-user capacity.

Before filming, keep the hosted app available and confirm audio and text readability. Final Devpost/video submission remains the owner's task. Formal human AI ratings are still pending and are needed before making quantitative accuracy claims; no such claim is made here.
