# Project Structure

```
football-predict/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI entry + router wiring
│   │   ├── queries.py             # SQL query layer (asyncpg)
│   │   ├── schemas.py             # Pydantic response models
│   │   ├── leagues.py             # league_code canon + display metadata
│   │   │
│   │   ├── api/                   # 14 routers
│   │   │   ├── matches.py         # list / get / h2h / lineups / injuries / weather / scorers / odds-comparison / CI / halftime / markets
│   │   │   ├── predictions.py     # POST trigger
│   │   │   ├── stats.py           # accuracy / calibration / recent / comparison / roi / history / scorers
│   │   │   ├── teams.py           # team profile
│   │   │   ├── players.py         # player stats + history
│   │   │   ├── table.py           # per-league standings
│   │   │   ├── chat.py            # streaming Qwen + suggestions + history
│   │   │   ├── admin.py           # quota + ingest freshness + counts
│   │   │   ├── tipsters.py        # community leaderboard
│   │   │   ├── push.py            # web-push notifications
│   │   │   ├── news.py            # team-filtered news
│   │   │   ├── compare.py         # player/team H2H
│   │   │   ├── fpl.py             # Fantasy Premier League integration
│   │   │   └── search.py          # full-text search
│   │   │
│   │   ├── core/
│   │   │   ├── config.py          # env / LiteLLM / feature flags
│   │   │   ├── db.py              # asyncpg pool + lifespan
│   │   │   ├── cache.py           # in-proc LRU + pg advisory locks
│   │   │   └── llm.py             # LiteLLM router (qwen-turbo / qwen-plus / haiku fallback)
│   │   │
│   │   ├── ingest/
│   │   │   ├── schedule.py        # soccerdata CSV → matches
│   │   │   ├── players.py         # Understat player_season_stats
│   │   │   ├── odds.py            # football-data.co.uk CSV + fair_probs() + edge()
│   │   │   └── upsert.py          # atomic DB writes
│   │   │
│   │   ├── models/                # prediction legs + adjustments
│   │   │   ├── poisson.py         # Dixon-Coles engine
│   │   │   ├── elo.py             # Elo rating maintenance + 3-way mapper
│   │   │   ├── xgb_model.py       # XGBoost primary leg (weight 0.60)
│   │   │   ├── features.py        # TeamStrength + λ composition
│   │   │   ├── ci.py              # bootstrap confidence intervals
│   │   │   ├── half_time.py       # halftime λ
│   │   │   └── markets.py         # over/under + Phase 6 correlated markets
│   │   │
│   │   ├── predict/
│   │   │   └── service.py         # ensemble blend + injury/weather shrinks + commitment hash
│   │   │
│   │   ├── llm/
│   │   │   ├── prompts/           # reasoning + chat templates
│   │   │   └── chat_context.py    # RAG: last-5 matches + H2H + top scorers
│   │   │
│   │   ├── onchain/
│   │   │   └── commitment.py      # SHA-256 canonical-JSON hash (chain-agnostic; no broadcast)
│   │   │
│   │   └── weather/
│   │       └── fetcher.py         # OpenWeatherMap client
│   │
│   ├── scripts/                   # 33 standalone entry points
│   │   ├── ingest_season.py           # initial seed
│   │   ├── ingest_players.py          # seasonal stats
│   │   ├── ingest_bookmaker_odds.py   # football-data CSV
│   │   ├── ingest_live_odds.py        # The Odds API (30-bookie avg)
│   │   ├── ingest_injuries.py         # API-Football
│   │   ├── ingest_lineups.py          # API-Football (15m pre-KO)
│   │   ├── ingest_live_scores.py      # 10s cadence, skip-unchanged
│   │   ├── ingest_weather.py          # T-2h per match
│   │   ├── ingest_news.py             # RSS team filter
│   │   ├── ingest_player_photos.py    # API-Football photos
│   │   ├── ingest_full_squad_photos.py
│   │   ├── predict_upcoming.py        # batch ensemble runner
│   │   ├── backtest.py                # walk-forward accuracy + calibration
│   │   ├── post_telegram.py / post_telegram_recap.py / post_telegram_digest.py
│   │   ├── post_twitter.py / post_twitter_recap.py
│   │   └── …                          # LLM cache warmers, diagnostics, etc.
│   │
│   ├── tests/                     # pytest — 100+ tests, TDD where possible
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                      # Next.js 15 App Router + Tailwind
│   ├── app/
│   │   ├── page.tsx                   # /        dashboard (hero, quick picks, proof strip)
│   │   ├── match/[id]/page.tsx        # /match/:id  predictions + odds + lineups + chat
│   │   ├── leagues/                   # /leagues, /leagues/:slug
│   │   ├── teams/[slug]/page.tsx      # /teams/:slug
│   │   ├── players/                   # /players, /players/:slug
│   │   ├── proof/page.tsx             # 30d accuracy + hash verification
│   │   ├── stats/page.tsx             # generic stats dashboard
│   │   ├── roi/page.tsx               # flat-stake PnL + threshold selector (edge ≥ 3/5/7/10pp)
│   │   ├── last-weekend/page.tsx      # 7-day hit/miss window
│   │   ├── benchmark/page.tsx         # model vs baselines
│   │   ├── table/page.tsx             # xG standings
│   │   ├── scorers/page.tsx           # top 25 sortable
│   │   ├── parlay/page.tsx            # Kelly-capped parlay builder
│   │   ├── betslip/page.tsx           # localStorage slip
│   │   ├── fpl/page.tsx               # FPL picks
│   │   ├── news/page.tsx
│   │   ├── tipsters/page.tsx
│   │   ├── history/page.tsx
│   │   ├── compare/page.tsx
│   │   ├── admin/page.tsx
│   │   ├── faq/page.tsx
│   │   ├── about/page.tsx
│   │   ├── docs/                      # model explainer
│   │   └── blog/                      # launch posts
│   │
│   ├── components/
│   │   ├── MatchCard.tsx
│   │   ├── TeamLogo.tsx               # fallback-pill on bad URL; ESPN CDN ID map
│   │   ├── PredictionBar.tsx
│   │   ├── OddsPanel.tsx              # Kelly popout at edge ≥ 10pp
│   │   ├── ProofStrip.tsx
│   │   ├── ScoreMatrix.tsx            # 6×6 heatmap
│   │   ├── QuickPicks.tsx
│   │   ├── RoiChart.tsx
│   │   ├── CommitmentBadge.tsx
│   │   ├── ChatWidget.tsx
│   │   ├── SiteHeader.tsx
│   │   ├── LangToggle.tsx
│   │   └── TerminalBlock.tsx
│   │
│   ├── lib/
│   │   ├── api.ts
│   │   ├── date.ts
│   │   ├── i18n.ts                    # client context
│   │   ├── i18n-server.ts             # SSR locale resolution via cookie
│   │   ├── leagues.ts
│   │   └── team-logos.ts              # slug → ESPN CDN URL (102 clubs across 5 leagues)
│   │
│   ├── locales/
│   │   ├── en.ts / vi.ts / th.ts / zh.ts / ko.ts
│   │   └── index.ts
│   │
│   ├── tailwind.config.ts             # Payy tokens
│   └── package.json
│
├── db/
│   ├── schema.sql                 # canonical
│   └── migrations/                # numbered 001_*.sql …
│
├── ops/
│   ├── weekly.sh                  # Monday: recap → backtest → predict_upcoming → post
│   └── systemd/                   # timer units on the VPS
│
├── infra/
│   └── deploy/                    # post-receive hook for bare-repo push
│
├── .github/workflows/             # CI + scheduled ingest backups
├── docker-compose.yml             # api + db
├── CLAUDE.md
├── plan.md                        # closed phases 1–4
├── plan-new.md                    # current: sharp-bettor analytics
├── PROGRESS.md
└── README.md
```

## Deploy note

No Cloudflare Pages any more. Frontend `web` is a container in the same `docker-compose.yml` as `api`, both published behind a shared Hostinger Caddy. See [`docs/deploy.md`](./deploy.md).
