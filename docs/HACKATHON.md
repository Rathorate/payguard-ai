# Local hackathon rehearsal

Keep the frontend and backend running locally. PayPal access is not required for this rehearsal. No deployment or real PayPal submission is part of it.

## Enable Groq on the backend

Edit your existing, ignored `.env` in Ubuntu. Do not overwrite your database settings or paste the key into chat or browser code:

```dotenv
DEMO_MODE=true
SECURE_COOKIES=false
AI_PROVIDER=groq
GROQ_API_KEY=your-key-here
GROQ_MODEL=openai/gpt-oss-20b
```

Use a model available to your Groq account. The adapter uses Groq's [Chat Completions API](https://console.groq.com/docs/api-reference); see [available models](https://console.groq.com/docs/models). Keys stay in the backend. When you generate a draft, the case and evidence text are sent to Groq, so use synthetic fixtures for the rehearsal.

For a completely offline rehearsal, set `AI_PROVIDER=template`. No model or PayPal request is then needed. An explicitly selected but unconfigured/failing Groq provider returns an error and preserves the previous saved response; it never silently replaces it with a template. Restart both servers after changing `.env`.

```bash
cd ~/projects/payguard-ai
bash scripts/test.sh
BACKEND_PORT=8001 FRONTEND_PORT=3001 bash scripts/dev.sh
```

Keep that terminal open. Ctrl+C stops both servers. Open http://127.0.0.1:3001 rather than the backend on port 8001. If a port is busy, choose another port; do not stop an unrelated application.

## Test the human decision

1. Open **Interactive demo**, then the Sam Rivera case. Seed data is synthetic and deadlines start relative to demo creation.
2. Expand the receipt. Add records from `fixtures/hackathon-evidence.json` through **Add a record**. You can also upload a text PDF, up to 5 MB / 20 pages / 8000 extracted characters.
3. Generate a draft. Groq output is marked **GROQ**. Check that it acknowledges missing authorization and delivery proof; a model response is never a verified finding.
4. Try **Approve response** without checking the review box: it must show a review error inside the dialog.
5. Edit the draft. Approval, export and submission are blocked while it has unsaved edits. Save it and check every assertion, evidence reference and deadline. You decide whether the response is acceptable.
6. Check the review box, then approve. **Withdraw approval** returns it to review. Try that, then approve again.
7. **Download approved packet** exports the exact approved response, facts, case version and a SHA-256 checksum as JSON. The checksum detects changes; it is not a digital signature or independent fact verification. Export does not submit or mark the case submitted.
8. Try submission without the second checkbox: it must be blocked. Then check **I understand this simulates submission** and submit. The case is locked and shows that nothing was sent to PayPal.
9. Open **Activity log** to see draft edits, approvals, withdrawals and simulated submission. Repeat with a fresh case to test invalid PDFs, expired deadlines, stale tabs and missing evidence.

Approval covers one saved case version. Adding evidence, saving edits or regenerating a draft clears approval. Changing a checked draft in the browser clears the review checkbox. The backend independently rejects unapproved or stale submissions even if a caller bypasses the UI. No code can prove that a person truly read the facts; the application records their explicit acknowledgement and enforces the workflow around it.

## PayPal without API access

Use the labeled simulation and reviewed packet for the hackathon. Demo mode cannot make real PayPal submissions, even if credentials are accidentally configured. It does not fake webhook verification, provider acceptance or a dispute win. A merchant with a real dispute can separately prepare appropriate material for their own manual provider workflow; uploading this JSON is not claimed to be supported by PayPal.

Real PayPal integration remains an adapter behind the same review gate and needs account-specific sandbox validation when credentials become available. Groq credentials alone do not enable it.

## Verification limits

Automated adapter tests use mocked Groq/PayPal responses, including malformed responses, truncation, authentication failures, rate limits and timeouts. A real Groq request and evaluation of its factual quality still require your local key. PostgreSQL checks require a disposable `TEST_POSTGRES_URL`; CI provisions one. Passing tests do not establish unlimited scale or the absence of every possible bug.
