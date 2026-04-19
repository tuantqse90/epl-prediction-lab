-- Referee captured from API-Football fixture payload. Currently surfaced on
-- match detail only; future work: aggregate per-referee cards/penalty rates
-- and wire into card-market predictions.

ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS referee TEXT;

CREATE INDEX IF NOT EXISTS idx_matches_referee
    ON matches (referee)
    WHERE referee IS NOT NULL;
