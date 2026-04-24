-- Mid-game stats check-in: fires once per match around minute 60 with
-- a brief shots/possession/xG snapshot + live model probabilities.
-- Idempotent via matches.midway_notified_at.
ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS midway_notified_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_matches_midway_notify
    ON matches (status, minute, midway_notified_at)
    WHERE status = 'live' AND midway_notified_at IS NULL;
