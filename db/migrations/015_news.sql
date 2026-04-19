-- Aggregated football news headlines. We store headline + URL only
-- (copyright-safe); full text lives on the source site, not ours.
-- Team / league linking is keyword-based against our teams table.

CREATE TABLE IF NOT EXISTS news_items (
    id            SERIAL PRIMARY KEY,
    source        TEXT NOT NULL,          -- 'bbc' | 'guardian' | 'espn' | 'goal'
    url           TEXT UNIQUE NOT NULL,
    title         TEXT NOT NULL,
    summary       TEXT,                   -- RSS description / first 280 chars
    published_at  TIMESTAMPTZ NOT NULL,
    teams         TEXT[] NOT NULL DEFAULT '{}',  -- team slugs detected in title
    league_code   TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_news_published  ON news_items (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_teams      ON news_items USING GIN (teams);
CREATE INDEX IF NOT EXISTS idx_news_league     ON news_items (league_code, published_at DESC);
