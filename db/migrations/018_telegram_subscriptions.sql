-- Per-chat team-follow list for the interactive Telegram bot.
-- When a goal/HT/FT event fires on a match involving a subscribed team,
-- live-scores fans out to every chat_id with a matching row.
CREATE TABLE IF NOT EXISTS telegram_subscriptions (
    chat_id     BIGINT NOT NULL,
    team_slug   TEXT   NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (chat_id, team_slug)
);
CREATE INDEX IF NOT EXISTS idx_telegram_subs_team ON telegram_subscriptions (team_slug);
