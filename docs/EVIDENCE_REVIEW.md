# Evidence review and human decisions

Evidence checks are a separate AI task from drafting. The model proposes recorded statements, missing facts and conflicts. The backend rejects unknown evidence IDs, invented quotations, malformed reports and conflicts without two distinct sources. Every quoted excerpt must appear exactly in the cited record. This proves a link to recorded text, not factual truth or logical entailment. A human still assesses relevance and meaning.

Groq GPT-OSS 20B/120B evidence reviews use strict JSON Schema output with the current evidence IDs. Other Groq models use JSON object mode and the same server validation. Draft responses remain plain text. Structured formatting does not prove that a quotation supports a claim; exact excerpts, source counts and human approval are still independently enforced. Failed validation returns a bounded reason code and field path without exposing rejected case content. No automatic retries are made.

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

Mechanical checks validate returned shapes, exact excerpts and reference existence. Read each generated response and complete human_pass/human_notes against the supplied checklist. A mechanically valid citation can still support a false interpretation. Record failures as well as successes. Do not report model accuracy from reference matching alone.

Failed synthetic analyses now retain analysis_validation (code and path) and rejected_analysis in the local report, so JSON-shape problems can be distinguished from invented or altered excerpts. This diagnostic capture is limited to the synthetic evaluator, not customer-case API errors. Keep previous reports when comparing releases; do not hide a failed run by repeatedly rerunning until one passes.

For a usefulness measurement, have the same reviewer prepare responses for equivalent synthetic cases manually and using PayGuard. Record total preparation time, correction count and evidence errors, including the human review step. Report the sample size and method; do not invent savings, dispute outcomes or win probabilities.
