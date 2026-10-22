-- Initial PostgreSQL schema. Use app.manage init-db for a fresh database.

CREATE TABLE rate_buckets (
	key VARCHAR(128) NOT NULL,
	count INTEGER NOT NULL,
	expires INTEGER NOT NULL,
	PRIMARY KEY (key)
);

CREATE INDEX ix_rate_buckets_expires ON rate_buckets (expires);

CREATE TABLE tenants (
	id VARCHAR(36) NOT NULL,
	name VARCHAR(100) NOT NULL,
	PRIMARY KEY (id)
);

CREATE TABLE audit (
	id VARCHAR(36) NOT NULL,
	tenant_id VARCHAR(36) NOT NULL,
	actor VARCHAR(254) NOT NULL,
	action VARCHAR(100) NOT NULL,
	resource_id VARCHAR(255) NOT NULL,
	created_at INTEGER NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX ix_audit_created_at ON audit (created_at);

CREATE INDEX ix_audit_tenant_id ON audit (tenant_id);

CREATE TABLE disputes (
	id VARCHAR(36) NOT NULL,
	tenant_id VARCHAR(36) NOT NULL,
	paypal_id VARCHAR(255) NOT NULL,
	customer VARCHAR(100) NOT NULL,
	reason VARCHAR(100) NOT NULL,
	amount_cents INTEGER NOT NULL,
	currency VARCHAR(3) NOT NULL,
	status VARCHAR(24) NOT NULL,
	due_at INTEGER NOT NULL,
	created_at INTEGER NOT NULL,
	draft TEXT NOT NULL,
	draft_source VARCHAR(32) NOT NULL,
	version INTEGER NOT NULL,
	provider_updated VARCHAR(64) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (tenant_id, paypal_id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX ix_queue ON disputes (tenant_id, status, due_at, id);

CREATE TABLE users (
	id VARCHAR(36) NOT NULL,
	tenant_id VARCHAR(36) NOT NULL,
	email VARCHAR(254) NOT NULL,
	password_hash VARCHAR(256) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	UNIQUE (email)
);

CREATE INDEX ix_users_tenant_id ON users (tenant_id);

CREATE TABLE webhook_inbox (
	id VARCHAR(36) NOT NULL,
	tenant_id VARCHAR(36) NOT NULL,
	event_id VARCHAR(255) NOT NULL,
	payload TEXT NOT NULL,
	state VARCHAR(24) NOT NULL,
	attempts INTEGER NOT NULL,
	available_at INTEGER NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (tenant_id, event_id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX ix_webhook_inbox_available_at ON webhook_inbox (available_at);

CREATE INDEX ix_webhook_inbox_state ON webhook_inbox (state);

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

CREATE TABLE evidence (
	id VARCHAR(36) NOT NULL,
	dispute_id VARCHAR(36) NOT NULL,
	tenant_id VARCHAR(36) NOT NULL,
	title VARCHAR(160) NOT NULL,
	kind VARCHAR(32) NOT NULL,
	content TEXT NOT NULL,
	sha256 VARCHAR(64) NOT NULL,
	created_at INTEGER NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(dispute_id) REFERENCES disputes (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX ix_evidence_dispute_id ON evidence (dispute_id);

CREATE INDEX ix_evidence_tenant_id ON evidence (tenant_id);

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

CREATE TABLE sessions (
	token_hash VARCHAR(64) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	csrf VARCHAR(64) NOT NULL,
	expires INTEGER NOT NULL,
	PRIMARY KEY (token_hash),
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_sessions_expires ON sessions (expires);

CREATE INDEX ix_sessions_user_id ON sessions (user_id);

CREATE TABLE submissions (
	id VARCHAR(36) NOT NULL,
	tenant_id VARCHAR(36) NOT NULL,
	dispute_id VARCHAR(36) NOT NULL,
	request_key VARCHAR(128) NOT NULL,
	draft_version INTEGER NOT NULL,
	state VARCHAR(24) NOT NULL,
	provider_reference VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (tenant_id, request_key),
	UNIQUE (dispute_id, draft_version),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(dispute_id) REFERENCES disputes (id)
);

CREATE INDEX ix_submissions_dispute_id ON submissions (dispute_id);
