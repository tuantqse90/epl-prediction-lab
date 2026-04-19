-- Lineups cache (from API-Football /fixtures/lineups).
-- Keyed by (match_id, team_slug, player_name) so re-running the ingest is
-- idempotent. Also adds api_football_fixture_id on matches so we don't
-- have to re-lookup the fixture id per fetch.

ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS api_football_fixture_id INT;

CREATE INDEX IF NOT EXISTS idx_matches_af_fixture
    ON matches (api_football_fixture_id);

CREATE TABLE IF NOT EXISTS match_lineups (
    id            SERIAL PRIMARY KEY,
    match_id      INT REFERENCES matches(id) ON DELETE CASCADE,
    team_slug     TEXT NOT NULL,
    player_name   TEXT NOT NULL,
    player_number INT,
    position      TEXT,        -- G / D / M / F / (null)
    grid          TEXT,        -- "4:1" etc., API-Football grid string
    is_starting   BOOLEAN NOT NULL DEFAULT TRUE,
    formation     TEXT,        -- "4-3-3" — stored per row for easy lookup
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (match_id, team_slug, player_name)
);

CREATE INDEX IF NOT EXISTS idx_lineups_match_team
    ON match_lineups (match_id, team_slug);
