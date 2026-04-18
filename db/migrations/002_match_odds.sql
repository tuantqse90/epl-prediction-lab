-- Phase polish+ — bookmaker odds per match (football-data.co.uk source).
-- Idempotent; multiple sources per match allowed (current / historical).

CREATE TABLE IF NOT EXISTS match_odds (
    id         SERIAL PRIMARY KEY,
    match_id   INT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    source     TEXT NOT NULL,      -- e.g. 'football-data:avg', 'football-data:pinnacle'
    odds_home  FLOAT NOT NULL,
    odds_draw  FLOAT NOT NULL,
    odds_away  FLOAT NOT NULL,
    captured_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (match_id, source)
);

CREATE INDEX IF NOT EXISTS idx_match_odds_match ON match_odds (match_id);
