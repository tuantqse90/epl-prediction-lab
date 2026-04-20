-- Multi-market odds storage (Over/Under, BTTS, Asian handicap).
-- Parallel to match_odds (which is h2h only) so the schemas stay simple.
-- Ingest writes both an aggregate row (source='the-odds-api:avg') and per-book
-- rows (source='odds-api:<book_key>') exactly like match_odds does for 1X2.
CREATE TABLE IF NOT EXISTS match_odds_markets (
    id SERIAL PRIMARY KEY,
    match_id INT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    market_code TEXT NOT NULL,        -- 'OU' | 'BTTS' | 'AH'
    line FLOAT,                       -- 2.5 for OU, -1.5 for AH home, NULL for BTTS
    outcome_code TEXT NOT NULL,       -- 'OVER'/'UNDER', 'YES'/'NO', 'HOME'/'AWAY'
    odds FLOAT NOT NULL,
    captured_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE NULLS NOT DISTINCT (match_id, source, market_code, line, outcome_code)
);

CREATE INDEX IF NOT EXISTS idx_match_odds_markets_match
    ON match_odds_markets(match_id, market_code);
CREATE INDEX IF NOT EXISTS idx_match_odds_markets_captured
    ON match_odds_markets(captured_at DESC);
