-- Block 24 internal tools: persisted error log + feature flags + page views

CREATE TABLE IF NOT EXISTS error_events (
    id          BIGSERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    request_id  TEXT NOT NULL,
    method      TEXT,
    path        TEXT NOT NULL,
    query       TEXT,
    error_class TEXT NOT NULL,
    message     TEXT,
    traceback   TEXT
);
CREATE INDEX IF NOT EXISTS idx_error_ts ON error_events (ts DESC);
CREATE INDEX IF NOT EXISTS idx_error_path ON error_events (path, ts DESC);

CREATE TABLE IF NOT EXISTS feature_flags (
    key        TEXT PRIMARY KEY,
    enabled    BOOLEAN NOT NULL DEFAULT FALSE,
    rollout_pct INTEGER NOT NULL DEFAULT 0 CHECK (rollout_pct BETWEEN 0 AND 100),
    description TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS page_views (
    id         BIGSERIAL PRIMARY KEY,
    ts         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    path       TEXT NOT NULL,
    referrer   TEXT,
    country    TEXT,              -- best-effort from CF-IPCountry header if available
    lang       TEXT,
    session_id TEXT               -- random 128-bit, client-generated
);
CREATE INDEX IF NOT EXISTS idx_page_views_ts ON page_views (ts DESC);
CREATE INDEX IF NOT EXISTS idx_page_views_path ON page_views (path, ts DESC);
