-- Log every tweet we post so recap replies can thread on the original + we
-- avoid re-tweeting the same pick on a cron rerun.

CREATE TABLE IF NOT EXISTS twitter_posts (
    id          SERIAL PRIMARY KEY,
    match_id    INT REFERENCES matches(id) ON DELETE CASCADE,
    post_type   TEXT NOT NULL,        -- 'pick' | 'recap'
    tweet_id    TEXT NOT NULL,
    body        TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (match_id, post_type)
);

CREATE INDEX IF NOT EXISTS idx_twitter_match ON twitter_posts (match_id);
