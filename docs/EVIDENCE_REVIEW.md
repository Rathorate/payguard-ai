# Evidence review and human decisions

Evidence checks are a separate AI task from drafting. The model proposes recorded statements, missing facts and conflicts. The backend rejects unknown evidence IDs, invented quotations, malformed reports and conflicts without two distinct sources. Every quoted excerpt must appear exactly in the cited record. This proves a link to recorded text, not factual truth or logical entailment. A human still assesses relevance and meaning.

Groq GPT-OSS 20B/120B evidence reviews and drafts use strict JSON Schema output with the current evidence IDs. Other Groq models use JSON object mode and the same server validation. Structured drafts declare source IDs separately for each paragraph; the backend validates those IDs and renders plain-text bracket references for the existing editor. Unknown IDs, missing sources, embedded citation markers and malformed paragraphs are rejected, not repaired. A declared link does not establish that its source supports the paragraph. OpenAI drafting and offline templates retain their existing plain-text paths. Exact excerpts, source counts and human approval are still independently enforced. Failed analysis validation returns a bounded reason code and field path without exposing rejected case content. No automatic retries are made.

The report is bound to a saved case version. Edits, evidence additions, approval transitions and provider changes make older reports unavailable as current guidance. If the case changes during a model call, its result is discarded. Analysis never approves or submits a case. Offline mode keeps manual review and template drafting available; it does not pretend to perform semantic analysis.

The citation inspector groups the saved response into paragraphs. It exposes linked source records and flags unknown bracket references. Paragraphs without references are labeled, including nonfactual paragraphs; this is not an automatic claim-level fact checker. Saving an edit refreshes the inspector. Source records are merchant statements or imported metadata and are not independently carrier-verified.

Unknown references block approval and submission on the server. Correct or remove them, save, and review again. Valid references still require a human to assess whether their sources support the response. Approved packet exports include citation details and retained review history.

New draft history retains generated output, human edits, approval and withdrawal, each with saved version, actor and time. The original model output and current response can be compared side by side. Only the latest 20 revisions are returned in the case UI; the latest generated baseline is queried separately. Existing responses from older builds have no reconstructed history. Case/audit data and revisions remain tenant-scoped.

## Local use

Pull the source and restart both servers. Demo-mode startup creates the two new tables without rewriting existing case records. In a case, add evidence, select Check evidence with AI, inspect excerpts/gaps, then generate a draft. Inspect source links, correct the response, save, explicitly approve and separately acknowledge simulated submission. A draft/approval version change requires another analysis if a current report is wanted.

For a non-demo existing PostgreSQL database, back up first and apply migrations/002_review_history.sql before starting this build. Fresh databases can use python -m app.manage init-db. This is an additive migration; there is still no complete automated migration framework.

## Repeatable live evaluation

```bash
bash scripts/evaluate-ai.sh
```

This sends four synthetic scenarios to the configured AI provider, two calls per scenario: receipt-only, conflicting delivery statements, missing authorization and embedded malicious instructions. It never reads customer cases, contacts PayPal or changes approvals. API usage may consume provider quota. Results are saved locally in .artifacts/ai-evaluation.json, excluded from source control.

Requests are paced 35 seconds apart by default (roughly four to five minutes for a complete run). --pause-seconds accepts 0..60 to suit the account's limits. A 429 stops further requests and records remaining scenarios as not run, never as passes. A bounded Retry-After value is shown when Groq supplies one. Pacing does not remove daily or account-wide quota limits. GPT-OSS uses low reasoning effort and hidden reasoning output; incomplete generations still fail visibly with a safe finish reason. No partial response is saved as a successful draft.

Mechanical checks validate returned shapes, exact excerpts and reference existence. Read each generated response and complete human_pass/human_notes against the supplied checklist. A mechanically valid citation can still support a false interpretation. Record failures as well as successes. Do not report model accuracy from reference matching alone.

Draft evaluation also requires at least one linked evidence reference when evidence is supplied. Parenthesized IDs, Unicode substitutions and drafts without references no longer pass just because they contain no unknown square-bracket IDs. This is a minimum link check; it does not determine whether every factual paragraph is cited or whether a source entails the text. Drafting instructions request exact ASCII bracket references, concise evidence gaps and no unnecessary payment-instrument details. Human reviewers must still check the actual output. See AI_SAMPLE_REVIEW.md for the observed live sample and its limitations.

Failed synthetic analyses now retain analysis_validation (code and path) and rejected_analysis in the local report, so JSON-shape problems can be distinguished from invented or altered excerpts. This diagnostic capture is limited to the synthetic evaluator, not customer-case API errors. Keep previous reports when comparing releases; do not hide a failed run by repeatedly rerunning until one passes.

Provider HTTP failures record the failed task (draft or analysis), HTTP status and recognized code/type/parameter values. Raw provider error messages, failed generations and credentials are not copied into errors or reports. Unknown metadata is labeled unknown. HTTP 400 alone does not establish whether a request parameter or generated output was rejected; inspect the code before changing configuration. Errors are not automatically retried or converted into a successful template response.

To diagnose a single failing scenario without repeating all eight calls:

```bash
bash scripts/evaluate-ai.sh --case authorization-missing --output .artifacts/ai-authorization-diagnostic.json
```

The report is explicitly labeled single_scenario and is not a full evaluation pass. Keep failed reports; after a diagnosed fix, run the full suite to a new filename and manually assess all four responses.

For a usefulness measurement, have the same reviewer prepare responses for equivalent synthetic cases manually and using PayGuard. Record total preparation time, correction count and evidence errors, including the human review step. Report the sample size and method; do not invent savings, dispute outcomes or win probabilities.

## Shared passage-reference protocol

Both evidence analysis and case Q&A now select short source_refs such as S1 from a server-built catalog. The model never needs to reproduce long JSON-escaped quotations or pair a copied excerpt with an evidence ID. The server resolves each reference to the original record and contiguous excerpt, then runs the existing bounded report validation. Unknown references, duplicate refs/JSON keys, unsupported shapes and conflicts without two distinct evidence records are rejected. API report fields and saved reports retain their existing sources/evidence_id/quote format.

This simplifies the constrained-output schema after an observed Groq 400 json_validate_failed during a real browser rehearsal. It does not establish the provider's internal failure cause or promise that upstream errors cannot recur. There is no automatic retry, no weaker-validation fallback and no automatic approval. A failure leaves saved draft/approval unchanged and preserves a prior report for that case version.

Official provider reference: https://console.groq.com/docs/structured-outputs
