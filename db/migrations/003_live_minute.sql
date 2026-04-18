-- Live-match fields: polled from API-Football during match windows.
ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS minute INT,
    ADD COLUMN IF NOT EXISTS live_updated_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_matches_live
    ON matches (status)
    WHERE status = 'live';
