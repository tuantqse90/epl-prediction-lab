-- Per-match event timeline from API-Football: goals, cards, subs.
CREATE TABLE IF NOT EXISTS match_events (
    id             SERIAL PRIMARY KEY,
    match_id       INT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    minute         INT,
    extra_minute   INT,
    team_slug      TEXT,
    player_name    TEXT,
    assist_name    TEXT,
    event_type     TEXT NOT NULL,
    event_detail   TEXT,
    captured_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Expression-based UNIQUE has to go on an INDEX, not the column list.
CREATE UNIQUE INDEX IF NOT EXISTS idx_match_events_unique
    ON match_events (
        match_id,
        COALESCE(minute, -1),
        COALESCE(extra_minute, 0),
        COALESCE(player_name, ''),
        event_type,
        COALESCE(event_detail, '')
    );

CREATE INDEX IF NOT EXISTS idx_match_events_match
    ON match_events (match_id, minute);
