# Case preparation and provider actions

GET /api/v1/disputes/{id}/workflow returns tenant-scoped guidance from current local evidence, version-matched AI findings and the latest saved provider observation. It makes no remote request.

POST /api/v1/disputes/{id}/workflow/refresh requires CSRF, exact origin, matching version and configured sandbox seller mapping. It is limited to five reads per workspace per minute. The authenticated GET response must match the case ID and valid monetary/deadline fields. Only known action relations with POST and matching official HTTPS host/path are retained; URLs, access tokens and the full response are not stored. Failure preserves the previous observation. Successful reads audit PAYPAL_STATUS_READ. No evidence, response, approval or case version changes.

Import stores an observation atomically with the case. Older imports show no observation until refreshed. Observations are historical after five minutes and may become outdated sooner. There is no background polling or automatic provider-to-evidence reconciliation.

The preparation checklist uses record kinds to suggest relevant source collection. A record being present is not verification; the merchant must inspect it. Current AI findings and draft citations remain separate from deterministic checks. No confidence score or win prediction is offered.

For non-demo submission the API reads PayPal immediately before recording submission intent, requires WAITING_FOR_SELLER_RESPONSE and a trusted provide-evidence link, and rejects changed reason, amount, currency or seller deadline. Missing/expired deadlines block sending. Provider failures during this preflight create no submission record. Existing uncertain-write protections still apply after intent is committed. Provider acceptance and notes constraints still require an actual sandbox write rehearsal. Other action links are displayed as information, not automatically executed.

Existing demo SQLite schemas get the new table at startup. Existing non-demo databases must apply docs/migrations/003_provider_observations.sql first after backing up. Fresh database initialization includes it.

Reference: https://developer.paypal.com/api/customer-disputes/v1/disputes-provide-evidence — the provider requires its returned provide-evidence link, not just a lifecycle-stage assumption.
