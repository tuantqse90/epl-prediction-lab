-- Manager tenure per team. Populated manually via admin endpoint +
-- (later) automated from manager-change news patterns.
-- ended_at IS NULL means "still in charge today".
CREATE TABLE IF NOT EXISTS manager_tenure (
    id         SERIAL PRIMARY KEY,
    team_slug  TEXT NOT NULL,
    manager_name TEXT NOT NULL,
    started_at DATE NOT NULL,
    ended_at   DATE,
    source_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_manager_tenure_team ON manager_tenure (team_slug, started_at DESC);
-- Only one open-ended tenure per team at a time.
CREATE UNIQUE INDEX IF NOT EXISTS unq_manager_tenure_current ON manager_tenure (team_slug) WHERE ended_at IS NULL;
