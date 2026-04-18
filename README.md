# EPL Prediction Lab

> xG-driven Poisson + Dixon-Coles predictions for every Premier League match, with market-edge value bets, calibrated confidence, and plain-language reasoning from Qwen.

Live: **https://predictor.nullshift.sh/** · Telegram: **[@worldcup_predictor](https://t.me/worldcup_predictor)**

## What it does

- **Predicts** every EPL fixture with a Poisson + Dixon-Coles engine tuned on 7 seasons of Understat data (`last_n=12`, `ρ=-0.15`, `T=1.35`).
- **Compares to the market**: flags every outcome where the model's implied edge over devigged bookmaker odds exceeds 5 percentage points.
- **Explains itself**: each prediction ships with a short, data-grounded Vietnamese reasoning line from Qwen (via LiteLLM → DashScope intl).
- **Chats about the match**: multi-turn Q&A grounded in the same RAG data block (last-5 xG, H2H, top scorers, model probabilities).
- **Ships weekly**: systemd timer drives a full refresh cycle every Monday 02:00 UTC; pre-match picks + post-match recap auto-post to the Telegram channel.

Currently 52% 1X2 accuracy vs a 42% home-always baseline over ~2600 backtested matches.

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
