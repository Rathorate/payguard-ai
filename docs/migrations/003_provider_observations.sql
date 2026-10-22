-- Additive migration for an existing non-demo database. Back up before applying.
BEGIN;
CREATE TABLE provider_observations (
    dispute_id VARCHAR(36) NOT NULL PRIMARY KEY REFERENCES disputes(id),
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id),
    observed_at INTEGER NOT NULL,
    report TEXT NOT NULL
);
CREATE INDEX ix_provider_observations_tenant_id ON provider_observations (tenant_id);
COMMIT;
