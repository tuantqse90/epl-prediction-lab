-- Discord webhook URLs users post to us so we can fan out digest +
-- goal pings into their guild. No auth — user posts the URL with a
-- label; we store it and POST JSON messages to it.
CREATE TABLE IF NOT EXISTS discord_webhooks (
    id           SERIAL PRIMARY KEY,
    url          TEXT   NOT NULL UNIQUE,
    label        TEXT,
    team_slugs   TEXT[] NOT NULL DEFAULT '{}',  -- optional scope; empty = all
    daily_digest BOOLEAN NOT NULL DEFAULT TRUE,
    goal_pings   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_ok_at   TIMESTAMPTZ,
    last_error   TEXT
);
CREATE INDEX IF NOT EXISTS idx_discord_webhooks_teams ON discord_webhooks USING GIN (team_slugs);
