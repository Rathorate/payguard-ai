# Ask AI in the merchant workspace

1. Sign in and open the dispute inbox.
2. In **Ask AI about a case**, select a dispute in **Case for AI chat**, then click **Ask AI**. The selector lists cases on the current filtered page.
3. The case opens at **Your question**. Type a question and click **Ask AI** in the case panel.
4. Read the answer and open its source excerpts. Matching text is not proof that a claim is true.
5. Ask a follow-up. Check **Include my saved draft** if the question concerns the saved response.

Examples:
- Does this receipt establish delivery? What is missing?
- What do the merchant and buyer disagree about?
- Does the payment record establish buyer authorization?
- Which sentence in my saved draft is unsupported by the evidence?

The chat uses only the selected case's saved evidence, limited recent conversation and optional saved draft. It cannot edit, approve or submit a case. Evidence is sent to the configured AI provider. Empty accounts need a case and evidence first. Conversation clears on reload or version changes; saved records remain.

Completed answers that fail structural/source validation get at most one fresh source-constrained generation attempt, with source validators still enforced. Provider failures and quotas are not retried by this mechanism. Existing provider schema recovery may also run. Repeated invalid answers fail closed and do not change the case. This improves format reliability, not factual accuracy. No perfect response-quality claim is made.

PUBLIC_DEMO_ENABLED=false disables guest access and preset sample loading. DEMO_MODE=true independently keeps submissions simulated. Your merchant cases persist and new merchant accounts start empty.

A live rehearsal caught a receipt-only answer incorrectly describing payment as authorized. A targeted check now rejects RECORDED authorization/consent language when the linked source excerpts do not mention those concepts, allowing the existing single fresh-answer attempt. Missing authorization can be explained as uncertainty. This is a narrow guard for the observed error; a word appearing in an excerpt does not establish consent or factual correctness.
