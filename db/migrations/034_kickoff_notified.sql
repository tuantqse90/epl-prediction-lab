-- Phase 43b: kickoff notifications.
-- One column mirrors the ft_notified_at / ht_notified_at pattern so a
-- repeated poll doesn't re-fire the same notification.
ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS kickoff_notified_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_matches_kickoff_notify
    ON matches (status, kickoff_notified_at)
    WHERE status IN ('live', 'scheduled') AND kickoff_notified_at IS NULL;
