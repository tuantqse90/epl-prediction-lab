-- API-Football /injuries feed cache. One row per active injury per league.
-- We trade CT-level freshness for quota: cron refreshes daily, serves any
-- upcoming match in that league without per-fixture calls.

CREATE TABLE IF NOT EXISTS player_injuries (
    id            SERIAL PRIMARY KEY,
    team_slug     TEXT NOT NULL,
    player_name   TEXT NOT NULL,
    reason        TEXT,
    status_label  TEXT,              -- 'Missing Fixture' | 'Questionable' | …
    league_code   TEXT,
    season        TEXT NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (team_slug, player_name, season, reason)
);

CREATE INDEX IF NOT EXISTS idx_injuries_team_season
    ON player_injuries (team_slug, season);

CREATE INDEX IF NOT EXISTS idx_injuries_league_fresh
    ON player_injuries (league_code, last_seen_at);
