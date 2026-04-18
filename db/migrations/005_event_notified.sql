-- Track which goal events have already been pushed to Telegram so we don't
-- re-notify across cron ticks.
ALTER TABLE match_events
    ADD COLUMN IF NOT EXISTS notified_at TIMESTAMPTZ;
