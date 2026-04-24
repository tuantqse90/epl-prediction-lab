-- Developer API keys + usage metrics + webhooks.
CREATE TABLE IF NOT EXISTS api_keys (
    id            SERIAL PRIMARY KEY,
    key_hash      TEXT NOT NULL UNIQUE,          -- sha256(raw_key)
    key_prefix    TEXT NOT NULL,                  -- first 8 chars for display
    label         TEXT,
    scope         TEXT NOT NULL DEFAULT 'read',   -- 'read' for now
    rate_limit    INTEGER NOT NULL DEFAULT 60,    -- requests / minute
    cors_origins  TEXT[] NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at  TIMESTAMPTZ,
    revoked_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys (key_hash) WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS api_key_usage (
    id          BIGSERIAL PRIMARY KEY,
    key_id      INTEGER REFERENCES api_keys(id) ON DELETE CASCADE,
    ts          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    path        TEXT NOT NULL,
    status_code INTEGER,
    latency_ms  INTEGER
);
CREATE INDEX IF NOT EXISTS idx_api_usage_key ON api_key_usage (key_id, ts DESC);

CREATE TABLE IF NOT EXISTS api_webhooks (
    id          SERIAL PRIMARY KEY,
    key_id      INTEGER NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    url         TEXT NOT NULL,
    event_types TEXT[] NOT NULL DEFAULT '{prediction_created,match_final}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_ok_at  TIMESTAMPTZ,
    last_error  TEXT
);
CREATE INDEX IF NOT EXISTS idx_api_webhooks_key ON api_webhooks (key_id);
