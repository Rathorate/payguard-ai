# Hosted verification — 23 October 2026

Frontend: https://payguard-ai-frontend.vercel.app
Backend: https://payguard-ai-ih99.onrender.com

Vercel Hobby uses root frontend and BACKEND_ORIGIN pointing to Render. Render Free uses the repository Dockerfile, /health/ready, the dedicated Neon database configured privately by the owner, SECURE_COOKIES=true, DEMO_MODE=true and APP_ORIGIN pointing to the frontend. No paid upgrade was selected.

Verified through the deployed browser: demo login, session survives reload, seeded synthetic cases, case detail, Groq source-linked Q&A and saved draft generation. Evidence analysis received one json_validate_failed provider rejection; one explicit manual retry succeeded. The rejected request did not change the draft. Provider reliability is not established by this small rehearsal.

Hosted PayPal is not connected yet. Create the owner's hosted merchant workspace, privately configure sandbox Client ID/Secret and that workspace's PAYPAL_TENANT_ID on Render, then re-import PP-R-SLL-10194090 and refresh its available actions. Never map the disposable demo workspace as the merchant. Local accounts, SQLite evidence and approval are not automatically migrated.

Pending hosted checks: owner review/approval, export, simulated submission, PDF upload and data persistence across backend redeploy. Real PayPal submission is unverified and remains disabled by demo mode. No escalation or PayPal write was performed.

The hosted review also exposed that responsive CSS hid Sign out below 800px. The profile/account switch control is now retained with a 44px minimum button target. Frontend contract tests: 10 passed; deployment configuration check passed with the actual backend origin. This CSS change does not modify backend logic.
