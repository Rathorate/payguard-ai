-- Additive migration. Back up the database before applying. No existing rows are rewritten.

CREATE TABLE draft_revisions (
	id VARCHAR(36) NOT NULL,
	tenant_id VARCHAR(36) NOT NULL,
	dispute_id VARCHAR(36) NOT NULL,
	case_version INTEGER NOT NULL,
	action VARCHAR(32) NOT NULL,
	source VARCHAR(32) NOT NULL,
	text TEXT NOT NULL,
	actor VARCHAR(254) NOT NULL,
	created_at INTEGER NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (dispute_id, case_version),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(dispute_id) REFERENCES disputes (id)
);

CREATE INDEX ix_draft_revisions_dispute_id ON draft_revisions (dispute_id);

CREATE INDEX ix_draft_revisions_tenant_id ON draft_revisions (tenant_id);

CREATE TABLE evidence_analyses (
	id VARCHAR(36) NOT NULL,
	tenant_id VARCHAR(36) NOT NULL,
	dispute_id VARCHAR(36) NOT NULL,
	case_version INTEGER NOT NULL,
	source VARCHAR(32) NOT NULL,
	report TEXT NOT NULL,
	created_at INTEGER NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (dispute_id, case_version),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(dispute_id) REFERENCES disputes (id)
);

CREATE INDEX ix_evidence_analyses_dispute_id ON evidence_analyses (dispute_id);

CREATE INDEX ix_evidence_analyses_tenant_id ON evidence_analyses (tenant_id);
