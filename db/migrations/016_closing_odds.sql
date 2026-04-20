-- Closing-Line Value (CLV) snapshot table.
-- Captured once per (match_id, source) at T-5min before kickoff by the
-- ingest_closing_odds cron. Separate from match_odds so the ingest there
-- can keep its upsert-overwrite semantics without losing the kickoff snapshot.
CREATE TABLE IF NOT EXISTS closing_odds (
    id SERIAL PRIMARY KEY,
    match_id INT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    odds_home FLOAT NOT NULL,
    odds_draw FLOAT NOT NULL,
    odds_away FLOAT NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    minutes_before_kickoff INT,
    UNIQUE (match_id, source)
);

CREATE INDEX IF NOT EXISTS idx_closing_odds_match ON closing_odds(match_id);
