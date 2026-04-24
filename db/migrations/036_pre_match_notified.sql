-- Pre-match notification: fires 30 min before kickoff across social
-- channels (Telegram, team-subs, Discord). One row per match,
-- idempotent via matches.pre_match_notified_at.
ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS pre_match_notified_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_matches_pre_match_notify
    ON matches (status, kickoff_time, pre_match_notified_at)
    WHERE status = 'scheduled' AND pre_match_notified_at IS NULL;
