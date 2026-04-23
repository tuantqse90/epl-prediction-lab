-- Email opt-in for the weekly digest (Mon 09:00 UTC).
-- No passwords. Unsubscribe via confirmation token.
CREATE TABLE IF NOT EXISTS email_subscriptions (
    id           SERIAL PRIMARY KEY,
    email        TEXT   NOT NULL UNIQUE,
    token        TEXT   NOT NULL UNIQUE,        -- random; confirm + unsubscribe
    lang         TEXT   NOT NULL DEFAULT 'en',
    league_filter TEXT,                          -- NULL = all top-5
    confirmed_at TIMESTAMPTZ,
    unsubscribed_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_sent_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_email_subs_confirmed ON email_subscriptions (confirmed_at) WHERE confirmed_at IS NOT NULL;
