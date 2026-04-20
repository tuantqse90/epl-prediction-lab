# Football Prediction Lab — CLAUDE.md

> Brief orientation for Claude Code sessions. Depth lives in [`plan-new.md`](./plan-new.md) (sharp-bettor strategies, current phase), the [`docs/`](./docs/) folder, and [`PROGRESS.md`](./PROGRESS.md).

## What this project is

Multi-league football prediction app covering **EPL · La Liga · Bundesliga · Serie A · Ligue 1**. xG-driven ensemble (Poisson + Elo + XGBoost) for numbers; Qwen via LiteLLM for reasoning and Q&A. **Payy-inspired design** ([payy.network](https://payy.network/)) — pure black, neon-lime accent `#E0FF32`, black-on-neon CTAs. Solo use first, public read-only now. No auth, no wallet.

- **Tagline**: *"xG doesn't lie. But the bookies do."*
- **Live**: [predictor.nullshift.sh](https://predictor.nullshift.sh)
- **Stack**: Python 3.12 + FastAPI (backend) · Next.js 15 + Tailwind (frontend) · **self-hosted Postgres 16 + pgvector on VPS** (Docker) · Qwen via LiteLLM (LLM) · The Odds API + football-data.co.uk + API-Football (odds / injuries / lineups) · Understat (xG + player stats)
- **Deploy**: Git push to bare repo on VPS → `post-receive` hook rebuilds `api` + `web` via docker compose. Frontend served from the same VPS (port 3500), API on 8500, both behind a shared Hostinger Caddy.

## Current phase

**Phase 5+ — sharp-bettor analytics** on top of a live MVP. See [`plan-new.md`](./plan-new.md) for the roadmap.

## Where things live

| Topic | File |
|---|---|
| Sharp-bettor roadmap (current) | [`plan-new.md`](./plan-new.md) |
| Dated progress log (summary only) | [`PROGRESS.md`](./PROGRESS.md) |
| Project identity, value prop, metrics | [`docs/README.md`](./docs/README.md) |
| Tech stack + system diagram | [`docs/architecture.md`](./docs/architecture.md) |
| Postgres schema (self-hosted, VPS) | [`docs/database.md`](./docs/database.md) |
| Ensemble engine (Poisson + Elo + XGB + adjustments) | [`docs/prediction-model.md`](./docs/prediction-model.md) |
| Qwen reasoning, chat Q&A, LiteLLM | [`docs/llm-integration.md`](./docs/llm-integration.md) |
| UX, routes, design system | [`docs/frontend.md`](./docs/frontend.md) |
| Monorepo layout | [`docs/project-structure.md`](./docs/project-structure.md) |
| Build phases history | [`docs/roadmap.md`](./docs/roadmap.md) |
| Code / LLM / data principles | [`docs/principles.md`](./docs/principles.md) |
| Env vars, scope, open questions | [`docs/environment.md`](./docs/environment.md) |
| Deploy path (bare-repo push) | [`docs/deploy.md`](./docs/deploy.md) |
| VPS recovery runbook | [`docs/ops-recovery.md`](./docs/ops-recovery.md) |

## House rules

- **Never** ask the LLM for numbers (probabilities, scores, edges). Math engine only. LLM gets the numbers as context and writes prose around them.
- **Always** ground LLM output in data. Prompt templates in `backend/app/llm/` enforce it.
- **Cache** LLM outputs in DB. Reasoning rarely changes between scrapes.
- **No custody.** This is analytics + display only. No stake placement, no balance, no deposit. Phase 4.2 "non-custodial prediction market" stays dropped; Phase 5+ is reference-only sharp-bettor signal.
- **Design is Payy.** Pure black surface, one neon-lime accent per viewport, **black text on any neon fill** (never white). Full spec: [`docs/frontend.md`](./docs/frontend.md).
- **Multi-league, not EPL-only.** All new features must work across the 5 leagues we ingest; always filter or group by `league_code`.
- Python: `black` + `ruff`, typed, async by default. TS: strict, no `any`.
- No over-engineering. Solo project, optimise for iteration speed.
- Update [`PROGRESS.md`](./PROGRESS.md) after any meaningful change — **date + time + short summary only**.
- **TDD is the default.** Tests before code for any new endpoint, model, or settler. Watch the test fail, then write code.
