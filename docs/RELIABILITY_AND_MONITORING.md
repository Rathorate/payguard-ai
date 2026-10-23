# Reliability and monitoring

The hosted demo uses Render Free. UptimeRobot monitor 804393583 checks https://payguard-ai-ih99.onrender.com/health/live every five minutes. This endpoint supports GET and HEAD without authentication and does not query PostgreSQL or call Groq/PayPal. Monitor alerts use the account's existing email contact. No paid monitor or hosting upgrade was selected.

Monitoring reduces idle cold starts but cannot guarantee continuous availability. Render Free shares 750 running hours per calendar month across a workspace's free services. PayGuard shares that workspace with other apps; exhausting the allowance can suspend all free services. The monitor does not prevent provider outages, restarts, resource limits, database cold starts or AI quotas. Review usage before judging; do not claim an uptime SLA.

GROQ_SCHEMA_RECOVERY=true enables one additional read-only generation only after a strict-schema request returns HTTP 400 with the allowlisted code json_validate_failed. The second request uses JSON mode with the original schema supplied in system instructions. Rejected provider text is discarded. All task-specific validators still reject wrong shape, invented sources, unsupported quotations and incomplete responses. Recovery failure preserves the existing saved draft/report and returns the normal safe error. Recovery is disabled by default for predictable local diagnostics. No retry occurs for authentication failures, rate limits, timeouts, other error codes or PayPal writes. A recovery request can consume extra provider tokens and time; this is resilience, not proof of a root-cause fix or perfect accuracy.

After submission, the workflow checklist consults retained approval history for the same saved draft. It reports the actual approved version and does not suggest approving a locked response again. Legacy cases without such history remain explicitly unverified. Analysis at an earlier version is not presented as a current-version analysis; locked views direct the reviewer to history and the approved export.

Validation: full offline suite plus new HEAD regression total 222 Python tests passed, 2 PostgreSQL-only tests skipped locally, one non-failing upstream TestClient deprecation warning. Ten frontend tests and the deployment configuration check passed. CI must separately confirm PostgreSQL. Live synthetic recovery and upload checks are recorded separately after deployment; offline mocks do not establish provider reliability.

References checked 23 October 2026:
- https://render.com/docs/free
- https://console.groq.com/docs/structured-outputs
