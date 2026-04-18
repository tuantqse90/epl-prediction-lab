-- EPL Prediction Lab — initial schema.
-- Applied automatically on first `docker compose up` via the pgvector image's
-- /docker-entrypoint-initdb.d/ convention. Safe to re-run.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS teams (
    id         SERIAL PRIMARY KEY,
    slug       TEXT UNIQUE NOT NULL,
    name       TEXT NOT NULL,
    short_name TEXT NOT NULL,
    elo_rating FLOAT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS matches (
    id            SERIAL PRIMARY KEY,
    external_id   TEXT UNIQUE,
    season        TEXT NOT NULL,
    matchweek     INT,
    kickoff_time  TIMESTAMPTZ NOT NULL,
    home_team_id  INT REFERENCES teams(id),
    away_team_id  INT REFERENCES teams(id),
    home_goals    INT,
    away_goals    INT,
    home_xg       FLOAT,
    away_xg       FLOAT,
    home_shots    INT,
    away_shots    INT,
    home_ppda     FLOAT,
    away_ppda     FLOAT,
    status        TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS predictions (
    id                   SERIAL PRIMARY KEY,
    match_id             INT REFERENCES matches(id),
    model_version        TEXT NOT NULL,
    p_home_win           FLOAT NOT NULL,
    p_draw               FLOAT NOT NULL,
    p_away_win           FLOAT NOT NULL,
    expected_home_goals  FLOAT,
    expected_away_goals  FLOAT,
    top_scorelines       JSONB,
    reasoning            TEXT,
    reasoning_model      TEXT,
    confidence           FLOAT,
    commitment_hash      TEXT,
    commitment_tx        TEXT,
    commitment_chain     TEXT,
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_predictions_commitment_hash ON predictions (commitment_hash);

CREATE TABLE IF NOT EXISTS match_odds (
    id          SERIAL PRIMARY KEY,
    match_id    INT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    source      TEXT NOT NULL,
    odds_home   FLOAT NOT NULL,
    odds_draw   FLOAT NOT NULL,
    odds_away   FLOAT NOT NULL,
    captured_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (match_id, source)
);
CREATE INDEX IF NOT EXISTS idx_match_odds_match ON match_odds (match_id);

CREATE TABLE IF NOT EXISTS player_season_stats (
    id          SERIAL PRIMARY KEY,
    player_name TEXT NOT NULL,
    team_id     INT REFERENCES teams(id),
    season      TEXT NOT NULL,
    games       INT,
    goals       INT,
    assists     INT,
    xg          FLOAT,
    xa          FLOAT,
    npxg        FLOAT,
    key_passes  INT,
    position    TEXT,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id         SERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    match_id   INT REFERENCES matches(id),
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    embedding  vector(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_matches_kickoff    ON matches(kickoff_time);
CREATE INDEX IF NOT EXISTS idx_predictions_match  ON predictions(match_id);
CREATE INDEX IF NOT EXISTS idx_chat_embedding
    ON chat_messages USING ivfflat (embedding vector_cosine_ops);
