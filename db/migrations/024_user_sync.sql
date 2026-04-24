-- Cross-device sync for localStorage state. No email, no password.
-- User picks a 6-digit PIN; bytes are stored as-is (JSONB). Collisions
-- are rare at this scale (10^6 keyspace); rate-limit protects against
-- brute-force via a per-IP throttle at the endpoint.
CREATE TABLE IF NOT EXISTS user_sync (
    pin        TEXT PRIMARY KEY,          -- 6-digit, stored hashed (sha256)
    payload    JSONB NOT NULL,
    version    INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_user_sync_updated ON user_sync (updated_at);
