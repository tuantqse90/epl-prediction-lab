# EPL Prediction Lab — CLAUDE.md

> Brief orientation for Claude Code sessions. For depth, see [`plan.md`](./plan.md), the [`docs/`](./docs/) folder, and [`PROGRESS.md`](./PROGRESS.md).

## What this project is

Personal EPL match prediction app: **xG-driven Poisson engine + Qwen-powered reasoning and Q&A chatbot**. **Payy-inspired design** ([payy.network](https://payy.network/)) — pure black, neon-lime accent `#E0FF32`, black-on-neon CTAs. Solo use first, public read-only later. No auth.

- **Tagline**: *"xG doesn't lie. But the bookies do."*
- **Stack**: Python 3.12 + FastAPI (backend) · Next.js 15 + Tailwind (frontend) · **self-hosted Postgres 16 + pgvector on VPS** (Docker) · Qwen via LiteLLM (LLM)
- **Deploy**: VPS (Docker compose: api + db) · Cloudflare Pages (web) · GH Actions (scrape cron)

## Where things live

| Topic | File |
|---|---|
| Master plan + links + current phase | [`plan.md`](./plan.md) |
| Dated progress log (summary only) | [`PROGRESS.md`](./PROGRESS.md) |
| Project identity, value prop, metrics | [`docs/README.md`](./docs/README.md) |
| Tech stack + system diagram | [`docs/architecture.md`](./docs/architecture.md) |
| Postgres schema (self-hosted, VPS) | [`docs/database.md`](./docs/database.md) |
| Poisson + Dixon-Coles math engine | [`docs/prediction-model.md`](./docs/prediction-model.md) |
| Qwen reasoning, chat Q&A, LiteLLM | [`docs/llm-integration.md`](./docs/llm-integration.md) |
| UX, routes, design system | [`docs/frontend.md`](./docs/frontend.md) |
| Monorepo layout | [`docs/project-structure.md`](./docs/project-structure.md) |
| Build phases MVP → v2 | [`docs/roadmap.md`](./docs/roadmap.md) |
| Code / LLM / data principles | [`docs/principles.md`](./docs/principles.md) |
| Env vars, scope, open questions | [`docs/environment.md`](./docs/environment.md) |

## House rules

- **Never** ask LLM for numbers (probabilities, scores). Math engine only.
- **Always** ground LLM output in data. Prompt templates enforce it.
- **Cache** LLM outputs in DB. Reasoning rarely changes between scrapes.
- **Design is Payy.** Pure black surface, one neon-lime accent per viewport, **black text on any neon fill** (never white). Full spec: [`docs/frontend.md`](./docs/frontend.md).
- Python: `black` + `ruff`, typed, async by default. TS: strict, no `any`.
- No over-engineering. Solo project, optimize for iteration speed.
- Update [`PROGRESS.md`](./PROGRESS.md) after any meaningful change — **date + time + short summary only**.
