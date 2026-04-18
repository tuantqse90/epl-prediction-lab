# Architecture

## Tech Stack

### Backend
- **Language**: Python 3.12
- **Framework**: FastAPI (async; same stack as Returnly / NullShift Signals)
- **Database**: Self-hosted **Postgres 16 + `pgvector`** on VPS (Docker compose). No managed DB — user runs it alongside the API container.
- **Data scraping**: `soccerdata` package (Understat + FBref + Club Elo)
- **Real-time fixtures**: API-Football free tier (100 req/day) as secondary source
- **Math engine**: `scipy.stats.poisson`
- **LLM router**: LiteLLM (already configured via Returnly)
- **Scheduling**: APScheduler or cron (scrape weekly, predict on-demand)

### LLM Stack
- **Primary**: Qwen-Turbo (Alibaba Cloud API) — bulk reasoning, cheap
- **Premium tier**: Qwen-Plus for big matches (derbies, top-6)
- **Embeddings**: Qwen text-embedding for Q&A retrieval
- **Fallback**: Claude Haiku via LiteLLM if Qwen fails

### Frontend
- **Framework**: Next.js 15 (App Router) — SSR for SEO + interactivity for chat
- **Styling**: Tailwind CSS + custom terminal theme
- **Fonts**: JetBrains Mono (primary), Inter (body fallback)
- **Charts**: Recharts (bar charts, xG heatmap)
- **Chat UI**: Vercel AI SDK (streaming)

### Deployment
- **Frontend**: Cloudflare Pages (same as Nerf Dev)
- **Backend**: VPS (Docker) — FastAPI + Postgres + `pgvector` in a single `docker compose` stack
- **DB**: Self-hosted Postgres on the same VPS (volume-mounted, nightly `pg_dump` to off-box storage)
- **Scrape cron**: GitHub Actions (free weekly runs) — pushes to the VPS API's ingest endpoint, or systemd timer on the VPS itself

## System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     DATA LAYER                              │
├─────────────────────────────────────────────────────────────┤
│  soccerdata (Understat)  →  xG, npxG, shot locations        │
│  soccerdata (FBref)      →  possession, PPDA, passing       │
│  soccerdata (Club Elo)   →  team strength ratings           │
│  API-Football (free)     →  fixtures, lineups, H2H          │
│  SportRadar (secondary)  →  live match data (optional)      │
│                      ↓                                      │
│              Scrape weekly via GH Actions                   │
│                      ↓                                      │
│              Postgres + pgvector (VPS)                      │
└─────────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│                   PREDICTION ENGINE                         │
├─────────────────────────────────────────────────────────────┤
│  Input:  last 10 matches xG (home + away), H2H, form        │
│  Model:  Dixon-Coles adjusted Poisson                       │
│  Output: P(home win), P(draw), P(away win)                  │
│          + most likely scorelines (top 5)                   │
│          + expected goals per team                          │
│          + confidence score                                 │
└─────────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│                   REASONING LAYER (Qwen)                    │
├─────────────────────────────────────────────────────────────┤
│  Input:  prediction + raw stats + recent news               │
│  Prompt: "Explain this prediction in peer-style Vietnamese" │
│  Output: 2-3 sentence reasoning, data-grounded              │
│                                                             │
│  Also: RAG index for Q&A                                    │
│  (embeddings of team stats + match reports in pgvector)     │
└─────────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (Next.js)                     │
├─────────────────────────────────────────────────────────────┤
│  /                    Weekly fixtures dashboard             │
│  /match/[id]          Deep dive + chat                      │
│  /table               League table + xG-based table         │
│  /teams/[slug]        Team profile + form viz               │
└─────────────────────────────────────────────────────────────┘
```
