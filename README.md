# Football Prediction Lab

> Open-methodology Poisson + Elo + XGBoost ensemble for top-5 European football leagues. Every prediction is publicly recomputable and commitment-hashed.

Live: **https://predictor.nullshift.sh/** · Telegram: **[@worldcup_predictor](https://t.me/worldcup_predictor)**

## What it does

- **Predicts** every fixture in EPL, La Liga, Serie A, Bundesliga, Ligue 1 with a layered ensemble:
  - Dixon-Coles Poisson on opponent-adjusted xG (last 12 matches, exponential decay, venue-split strengths)
  - Goal-weighted Elo (25% blend, 70-point home-field advantage)
  - XGBoost softprob on 21 features (30% second-layer blend)
- **Quantifies uncertainty**: 30-sample bootstrap confidence intervals on every outcome (`68% / 58%–76%`).
- **Derived markets**: O/U 1.5/2.5/3.5, BTTS, clean-sheet, HT winner, HT/FT 9-grid, anytime goalscorer per player. Fractional Kelly stake next to every bookmaker odds.
- **Live mode**: 10-second systemd timer polls API-Football during match windows, recomputes probabilities from remaining-Poisson, publishes goal events to Telegram + web push.
- **Transparent**: every prediction carries a SHA-256 commitment hash recomputable from the public body. /benchmark page tracks rolling model vs baseline vs uniform-random.
- **Multilingual**: EN / VI / TH / ZH / KO with per-locale timezones (London, Ho Chi Minh, Bangkok, Shanghai, Seoul).
- **Explains itself**: Qwen-generated reasoning per fixture + multi-turn chat grounded in the same RAG data.

**Backtested accuracy** (6 seasons, 2,263 matches):

| config | accuracy | log-loss |
|---|---|---|
| baseline (raw Poisson) | 52.32% | 1.0015 |
| + Elo ensemble | 53.29% | 0.9866 |
| **full ensemble** (Poisson+Elo+opp-adj) | **53.03%** | **0.9843 (−1.73%)** |

## Stack

| Layer | Tech |
|---|---|
| Math | NumPy · SciPy Poisson · custom Dixon-Coles + temperature scaling (TDD) |
| API | FastAPI · asyncpg · Pydantic v2 |
| LLM | LiteLLM → DashScope intl (`qwen-turbo`), streaming |
| DB | Postgres 16 + pgvector (self-hosted) |
| Web | Next.js 15 App Router · Tailwind · i18n VI/EN |
| Ingest | `soccerdata` (Understat) · football-data.co.uk (historical odds) · The Odds API (live odds) |
| Deploy | Docker compose · Caddy + LE · Cloudflare proxy |

## Repo layout

```
backend/
  app/
    api/          # FastAPI routers
    core/         # config + db pool
    ingest/       # schedule / players / odds translators + upserts
    llm/          # chat prompt + reasoning via LiteLLM
    models/       # Poisson + Dixon-Coles + temperature
    predict/      # orchestration service
    onchain/      # chain-agnostic SHA-256 commitment hash
  scripts/        # ingest / backtest / predict / fit / telegram
  tests/          # 60 pytest tests
frontend/
  app/            # Next.js routes (/, /match/:id, /table, /teams/:slug, /stats, /scorers, /last-weekend)
  components/     # cards, charts, chat widget, heatmap, logos
  lib/            # api client, i18n, team colors, TS Poisson port
  locales/        # en.ts + vi.ts dicts
contracts/        # (removed) was the Monad commitment contract
db/
  schema.sql      # pgvector extension + 6 tables
  migrations/     # idempotent ALTERs
ops/
  weekly.sh       # full-refresh cron entry
  football-predict-weekly.{service,timer}
docs/             # architecture, design, deploy, principles
```

## Run locally

```bash
cp .env.example .env   # fill secrets
docker compose up -d
docker compose exec api python scripts/ingest_season.py --season 2025-26
docker compose exec api python scripts/ingest_odds.py   --season 2025-26
docker compose exec api python scripts/backtest.py      --season 2025-26
docker compose exec api python scripts/predict_upcoming.py --horizon-days 14 --with-reasoning
```

## Tests

```
cd backend && python -m pytest
```

## License

Unlicensed — personal project. Feel free to read; don't expect support.
