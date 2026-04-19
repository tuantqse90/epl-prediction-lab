# Database Schema (self-hosted Postgres + pgvector)

> Runs on the VPS alongside the API container via `docker compose`. Image: `pgvector/pgvector:pg16`. Data lives in a named volume (`football-predict_db_data`); nightly `pg_dump` to off-box storage. Container port **not exposed** — only `api` reaches the DB via the internal compose network.

## Bootstrap

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Canonical schema lives in [`db/schema.sql`](../db/schema.sql). Migrations in `db/migrations/` (numbered `001_*.sql` …). Always add new columns/tables via a new migration file, not by hand-editing `schema.sql`.

## Schema (15 tables)

### Core model tables

```sql
-- Teams (canonical master for every league)
CREATE TABLE teams (
  id SERIAL PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,      -- kebab-case, understat-style ('manchester-city', 'bayern-munich')
  name TEXT NOT NULL,
  short_name TEXT NOT NULL,       -- display label, must be unique across active leagues
  league_code TEXT,               -- 'eng.1' | 'esp.1' | 'ger.1' | 'ita.1' | 'fra.1'
  elo_rating FLOAT,
  api_football_id INT,            -- cross-ref for photos / lineups / injuries
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Matches (historical + upcoming + live)
CREATE TABLE matches (
  id SERIAL PRIMARY KEY,
  external_id TEXT UNIQUE,        -- understat or api-football id
  league_code TEXT NOT NULL,      -- same domain as teams.league_code
  season TEXT NOT NULL,           -- e.g. '2025-26'
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
  status TEXT,                    -- 'scheduled' | 'live' | 'final'
  minute INT,                     -- live-only
  live_period TEXT,               -- '1H' | 'HT' | '2H' | 'FT' | 'AET' | 'PEN'
  referee TEXT,
  live_updated_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Predictions (pre-match ensemble output)
CREATE TABLE predictions (
  id SERIAL PRIMARY KEY,
  match_id INT REFERENCES matches(id),
  model_version TEXT NOT NULL,    -- 'ensemble-v3' etc.
  p_home_win FLOAT NOT NULL,
  p_draw FLOAT NOT NULL,
  p_away_win FLOAT NOT NULL,
  expected_home_goals FLOAT,
  expected_away_goals FLOAT,
  top_scorelines JSONB,           -- [{"score": "2-1", "prob": 0.12}, …]
  reasoning TEXT,                 -- Qwen-generated
  reasoning_model TEXT,           -- 'qwen-turbo' | 'qwen-plus' | 'haiku-fallback'
  confidence FLOAT,               -- 1 − scaled entropy
  commitment_hash TEXT,           -- SHA-256 canonical-JSON hash of the numeric body
  commitment_tx TEXT,             -- reserved; unused (Phase 4 dropped)
  commitment_chain TEXT,          -- reserved; unused
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Odds + betting reference

```sql
-- Bookmaker odds (per-source snapshot)
CREATE TABLE match_odds (
  id SERIAL PRIMARY KEY,
  match_id INT REFERENCES matches(id),
  source TEXT NOT NULL,           -- 'football-data:avg', 'the-odds-api:avg',
                                  -- 'odds-api:pinnacle', 'odds-api:bet365', …
  odds_home FLOAT,
  odds_draw FLOAT,
  odds_away FLOAT,
  captured_at TIMESTAMPTZ DEFAULT NOW()
);

-- NOTE: best-odds shopping is a SQL CTE in stats.py — MAX(odds_*) across all
-- sources per match. No materialised view.
```

### Contextual data (for model adjustments + UI)

```sql
-- Player season aggregates (chat context + top-scorer endpoints)
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

-- Injuries (feed INJURY_ALPHA λ shrink, surface on match page)
CREATE TABLE player_injuries (
  id SERIAL PRIMARY KEY,
  team_slug TEXT NOT NULL,
  player_name TEXT NOT NULL,
  reason TEXT,
  status_label TEXT,              -- 'Doubtful' | 'Out' | 'Questionable'
  league_code TEXT,
  season TEXT,
  first_seen_at TIMESTAMPTZ,
  last_seen_at TIMESTAMPTZ
);

-- Pre-match lineups (api-football; refreshed T-3h → T-0)
CREATE TABLE match_lineups (
  id SERIAL PRIMARY KEY,
  match_id INT REFERENCES matches(id),
  team_slug TEXT NOT NULL,
  player_name TEXT NOT NULL,
  player_number INT,
  position TEXT,
  grid TEXT,                      -- '3:2' etc. for formation plotting
  is_starting BOOLEAN,
  formation TEXT
);

-- Live match events (goal / card / sub — used for alerts + recaps)
CREATE TABLE match_events (
  id SERIAL PRIMARY KEY,
  match_id INT REFERENCES matches(id),
  minute INT,
  extra_minute INT,
  team_slug TEXT,
  player_name TEXT,
  assist_name TEXT,
  event_type TEXT,                -- 'goal' | 'card' | 'substitution'
  event_detail TEXT,
  notified_at TIMESTAMPTZ
);

-- Match-day conditions (feed weather λ multiplier)
CREATE TABLE match_weather (
  match_id INT PRIMARY KEY REFERENCES matches(id),
  temp_c FLOAT,
  wind_kmh FLOAT,
  precip_mm FLOAT,
  condition TEXT,
  fetched_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Content + community

```sql
-- Chat sessions (Q&A history + RAG context, pgvector semantic search)
CREATE TABLE chat_messages (
  id SERIAL PRIMARY KEY,
  session_id UUID NOT NULL,
  match_id INT REFERENCES matches(id),
  role TEXT NOT NULL,             -- 'user' | 'assistant'
  content TEXT NOT NULL,
  embedding vector(1536),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- News aggregation (team-scoped)
CREATE TABLE news_items (
  id SERIAL PRIMARY KEY,
  source TEXT,                    -- RSS feed slug
  url TEXT UNIQUE,
  title TEXT,
  summary TEXT,
  published_at TIMESTAMPTZ,
  teams TEXT[],                   -- matched team slugs
  league_code TEXT
);

-- Posted social content (Telegram + X) — prevents double-posting
CREATE TABLE twitter_posts (
  id SERIAL PRIMARY KEY,
  match_id INT REFERENCES matches(id),
  post_type TEXT,                 -- 'pre' | 'recap'
  tweet_id TEXT,
  body TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Community tipster leaderboard
CREATE TABLE tipsters (
  id SERIAL PRIMARY KEY,
  handle TEXT UNIQUE NOT NULL
);

CREATE TABLE tipster_picks (
  id SERIAL PRIMARY KEY,
  tipster_id INT REFERENCES tipsters(id),
  match_id INT REFERENCES matches(id),
  pick TEXT,                      -- 'H' | 'D' | 'A'
  confidence FLOAT                -- 0..1
);
```

## Indexes

```sql
CREATE INDEX idx_matches_kickoff       ON matches(kickoff_time);
CREATE INDEX idx_matches_league_status ON matches(league_code, status);
CREATE INDEX idx_predictions_match     ON predictions(match_id);
CREATE INDEX idx_match_odds_match      ON match_odds(match_id, source);
CREATE INDEX idx_chat_embedding        ON chat_messages USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_events_match_min      ON match_events(match_id, minute);
CREATE INDEX idx_news_published        ON news_items(published_at DESC);
```

## Tables coming in Phase 5+ (see [`plan-new.md`](../plan-new.md))

- `closing_odds` — T-5min snapshot for CLV calculation
- `match_odds_markets` — BTTS / Over-Under / AH odds per source
- `virtual_bankroll_state` — singleton row for the Kelly-sim bankroll
- `virtual_stake_log` — per-bet stake history with PnL

## Backups

```bash
# nightly
docker compose exec -T db pg_dump -U epl -d epl --clean | gzip > epl_$(date +%Y-%m-%d).sql.gz
# restore
gunzip < epl_YYYY-MM-DD.sql.gz | docker compose exec -T db psql -U epl -d epl
```
