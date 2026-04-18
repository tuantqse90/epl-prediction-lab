# Database Schema (self-hosted Postgres + pgvector)

> Runs on the VPS alongside the API container via `docker compose`. Image: `pgvector/pgvector:pg16`. Data lives in a named volume; nightly `pg_dump` to off-box storage.

## Bootstrap

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Schema


```sql
-- Teams
CREATE TABLE teams (
  id SERIAL PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  short_name TEXT NOT NULL,
  elo_rating FLOAT,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Matches (historical + upcoming)
CREATE TABLE matches (
  id SERIAL PRIMARY KEY,
  external_id TEXT UNIQUE,  -- understat or api-football id
  season TEXT NOT NULL,     -- e.g. "2025-26"
  matchweek INT,
  kickoff_time TIMESTAMPTZ NOT NULL,
  home_team_id INT REFERENCES teams(id),
  away_team_id INT REFERENCES teams(id),
  home_goals INT,
  away_goals INT,
  home_xg FLOAT,
  away_xg FLOAT,
  home_shots INT,
  away_shots INT,
  home_ppda FLOAT,
  away_ppda FLOAT,
  status TEXT,              -- 'scheduled', 'live', 'final'
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Predictions (what we predicted before the match)
CREATE TABLE predictions (
  id SERIAL PRIMARY KEY,
  match_id INT REFERENCES matches(id),
  model_version TEXT NOT NULL,
  p_home_win FLOAT NOT NULL,
  p_draw FLOAT NOT NULL,
  p_away_win FLOAT NOT NULL,
  expected_home_goals FLOAT,
  expected_away_goals FLOAT,
  top_scorelines JSONB,     -- [{"score": "2-1", "prob": 0.12}, ...]
  reasoning TEXT,           -- Qwen-generated
  reasoning_model TEXT,     -- 'qwen-turbo' | 'qwen-plus'
  confidence FLOAT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Player stats (for Q&A context)
CREATE TABLE player_season_stats (
  id SERIAL PRIMARY KEY,
  player_name TEXT NOT NULL,
  team_id INT REFERENCES teams(id),
  season TEXT NOT NULL,
  games INT,
  goals INT,
  assists INT,
  xg FLOAT,
  xa FLOAT,
  npxg FLOAT,
  key_passes INT,
  position TEXT,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chat sessions (Q&A history + RAG context)
CREATE TABLE chat_messages (
  id SERIAL PRIMARY KEY,
  session_id UUID NOT NULL,
  match_id INT REFERENCES matches(id),
  role TEXT NOT NULL,       -- 'user' | 'assistant'
  content TEXT NOT NULL,
  embedding vector(1536),   -- pgvector semantic search
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_matches_kickoff ON matches(kickoff_time);
CREATE INDEX idx_predictions_match ON predictions(match_id);
CREATE INDEX idx_chat_embedding ON chat_messages USING ivfflat (embedding vector_cosine_ops);
```
