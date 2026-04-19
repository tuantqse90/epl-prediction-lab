-- Auth-less community tipster leaderboard. Users pick a handle, submit
-- (match_id, pick, confidence); we score them by log-loss against the
-- actual outcome once the match settles. Handle uniqueness is the only
-- integrity constraint — two people sharing a handle is user error.

CREATE TABLE IF NOT EXISTS tipsters (
    id         SERIAL PRIMARY KEY,
    handle     TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tipster_picks (
    id          SERIAL PRIMARY KEY,
    tipster_id  INT REFERENCES tipsters(id) ON DELETE CASCADE,
    match_id    INT REFERENCES matches(id) ON DELETE CASCADE,
    pick        TEXT NOT NULL,       -- 'H' | 'D' | 'A'
    confidence  FLOAT NOT NULL CHECK (confidence > 0 AND confidence <= 1),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tipster_id, match_id)
);

CREATE INDEX IF NOT EXISTS idx_tipster_picks_tipster ON tipster_picks (tipster_id);
CREATE INDEX IF NOT EXISTS idx_tipster_picks_match   ON tipster_picks (match_id);
