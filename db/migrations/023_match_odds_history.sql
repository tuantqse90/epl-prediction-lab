-- Append-only log of every match_odds insert/update.
-- Keeps match_odds itself latest-only (existing queries unaffected) while
-- giving us a time series for line-movement charts and sharp-vs-square
-- divergence detection.

CREATE TABLE IF NOT EXISTS match_odds_history (
    id          BIGSERIAL PRIMARY KEY,
    match_id    INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    source      TEXT NOT NULL,
    odds_home   DOUBLE PRECISION NOT NULL,
    odds_draw   DOUBLE PRECISION NOT NULL,
    odds_away   DOUBLE PRECISION NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_moh_match_time ON match_odds_history (match_id, captured_at);
CREATE INDEX IF NOT EXISTS idx_moh_source_time ON match_odds_history (source, captured_at);

CREATE OR REPLACE FUNCTION log_match_odds_history()
RETURNS trigger AS $$
BEGIN
    -- Only log when odds actually changed on update; always log on insert.
    IF TG_OP = 'INSERT' OR
       NEW.odds_home IS DISTINCT FROM OLD.odds_home OR
       NEW.odds_draw IS DISTINCT FROM OLD.odds_draw OR
       NEW.odds_away IS DISTINCT FROM OLD.odds_away
    THEN
        INSERT INTO match_odds_history (match_id, source, odds_home, odds_draw, odds_away, captured_at)
        VALUES (NEW.match_id, NEW.source, NEW.odds_home, NEW.odds_draw, NEW.odds_away, NOW());
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_match_odds_history ON match_odds;
CREATE TRIGGER trg_match_odds_history
AFTER INSERT OR UPDATE ON match_odds
FOR EACH ROW EXECUTE FUNCTION log_match_odds_history();

-- Backfill existing rows as "first snapshot" so the chart has at least
-- one point per (match, source) immediately; new snapshots accumulate.
INSERT INTO match_odds_history (match_id, source, odds_home, odds_draw, odds_away, captured_at)
SELECT match_id, source, odds_home, odds_draw, odds_away, COALESCE(captured_at, NOW())
FROM match_odds
WHERE NOT EXISTS (
    SELECT 1 FROM match_odds_history h
    WHERE h.match_id = match_odds.match_id AND h.source = match_odds.source
);
