-- Web Push subscriptions. One row per browser endpoint. `teams` stores the
-- followed team slugs — empty array means "all goals across all my
-- favorites" (follows the existing favorites flow rather than a duplicate
-- list on the server).

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id              SERIAL PRIMARY KEY,
    endpoint        TEXT UNIQUE NOT NULL,
    p256dh          TEXT NOT NULL,
    auth            TEXT NOT NULL,
    teams           TEXT[] NOT NULL DEFAULT '{}',
    user_agent      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_success_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_push_teams ON push_subscriptions USING GIN (teams);
