-- Migration 0002: Append-Only Monthly Partitioned Audit Events Table
-- Stores all asset scan verdicts and cryptographic certificates immutably.

CREATE TABLE IF NOT EXISTS audit_events (
    id BIGSERIAL,
    event_id UUID DEFAULT gen_random_uuid(),
    batch_id VARCHAR(128) NOT NULL,
    asset_id VARCHAR(256) NOT NULL,
    asset_hash VARCHAR(71) NOT NULL, -- 'sha256:<64 hex>'
    track VARCHAR(32) NOT NULL,       -- 'TEXT', 'IMAGE', etc.
    verdict VARCHAR(32) NOT NULL,     -- 'PASSED', 'BLOCKED', 'REVIEW'
    score NUMERIC(5, 4) NOT NULL,
    certificate_id UUID,
    evidence_uri VARCHAR(512),
    raw_payload JSONB NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id, recorded_at)
) PARTITION BY RANGE (recorded_at);

-- Partitions for 2026
CREATE TABLE IF NOT EXISTS audit_events_2026_09 PARTITION OF audit_events
    FOR VALUES FROM ('2026-09-01 00:00:00+00') TO ('2026-10-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS audit_events_2026_10 PARTITION OF audit_events
    FOR VALUES FROM ('2026-10-01 00:00:00+00') TO ('2026-11-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS audit_events_default PARTITION OF audit_events DEFAULT;

CREATE INDEX IF NOT EXISTS idx_audit_events_asset_hash ON audit_events (asset_hash);
CREATE INDEX IF NOT EXISTS idx_audit_events_batch_id ON audit_events (batch_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_recorded_at ON audit_events (recorded_at DESC);

-- Revoke UPDATE and DELETE on audit_events to guarantee append-only immutability
-- REVOKE UPDATE, DELETE, TRUNCATE ON audit_events FROM PUBLIC;
