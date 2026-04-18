-- Multi-league support: identify which league each match belongs to.
-- Existing data is all EPL; backfill accordingly.
ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS league_code TEXT;

UPDATE matches SET league_code = 'ENG-Premier League' WHERE league_code IS NULL;

CREATE INDEX IF NOT EXISTS idx_matches_league_season
    ON matches (league_code, season);
