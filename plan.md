# Plan — EPL Prediction Lab

> Master orchestration doc. Links [`CLAUDE.md`](./CLAUDE.md) and every file under [`docs/`](./docs/). Progress is tracked separately in [`PROGRESS.md`](./PROGRESS.md) (summary log, timestamped).

---

## 0. Document map

| File | Purpose |
|------|---------|
| [`CLAUDE.md`](./CLAUDE.md) | Orientation file Claude Code reads on session start |
| [`plan.md`](./plan.md) | **This file** — phases, checklists, pointers |
| [`PROGRESS.md`](./PROGRESS.md) | Dated summary log of what's been done |
| [`docs/README.md`](./docs/README.md) | Project identity + value prop + success metrics |
| [`docs/architecture.md`](./docs/architecture.md) | Tech stack + system diagram |
| [`docs/database.md`](./docs/database.md) | Postgres schema (self-hosted on VPS) |
| [`docs/prediction-model.md`](./docs/prediction-model.md) | Poisson + Dixon-Coles math |
| [`docs/llm-integration.md`](./docs/llm-integration.md) | Qwen reasoning + chat Q&A + LiteLLM |
| [`docs/frontend.md`](./docs/frontend.md) | Design system + routes + UX |
| [`docs/project-structure.md`](./docs/project-structure.md) | Monorepo layout |
| [`docs/roadmap.md`](./docs/roadmap.md) | Build phases (MVP → v2) |
| [`docs/principles.md`](./docs/principles.md) | Code / LLM / data rules |
| [`docs/environment.md`](./docs/environment.md) | Env vars, scope, open questions |

---

## 1. Current status

- **Phase**: 0 — scoping / docs only. No code yet.
- **Repo root**: `football-predict/` (currently: docs + plan + brief only)
- **Next concrete step**: Phase 1.1 — initialize `backend/` + `frontend/` skeleton per [`docs/project-structure.md`](./docs/project-structure.md)

See [`PROGRESS.md`](./PROGRESS.md) for timestamped history.

---

## 2. Phase 1 — MVP checklist

From [`docs/roadmap.md`](./docs/roadmap.md). Check off in `PROGRESS.md` as each lands.

- [x] **1.1** Set up repo + project structure — `backend/` w/ `app/{core,models,ingest,predict,llm,api}`, `frontend/` Next.js scaffold
- [x] **1.2** Postgres on VPS — live at `football-predict-db-1` (pgvector/pgvector:pg16), schema auto-applied, internal-only (no host port)
- [x] **1.3** Scraper EPL — 2024-25 + 2025-26 ingested (760 matches, 20 teams)
- [x] **1.4** Poisson + Dixon-Coles engine — 33 tests pass; walk-forward on 2024-25 EPL: **57.0% 1X2 accuracy** (baseline 41.8%), log-loss 0.9856. ρ calibrated to **−0.10**.
- [x] **1.5** LLM reasoning layer — Qwen-Turbo via LiteLLM; TDD'd prompt builder (5 tests), `explain_prediction()` hooked into POST predictions endpoint
- [x] **1.6** FastAPI endpoints — `/health`, `GET /api/matches`, `GET /api/matches/:id`, `POST /api/predictions/:id` (predict + optional LLM reasoning)
- [x] **1.7** Next.js dashboard — App Router + Tailwind w/ Payy tokens, `<MatchCard>` + `<PredictionBar>` + `<TerminalBlock>`, `/` builds clean (`npm run build` ok)
- [x] **1.8** Deploy — **LIVE at https://predictor.nullshift.sh/** (Hostinger VPS + Caddy + LE cert + CF DNS A record). 21 upcoming predictions with Qwen reasoning serving.

## 3. Phase 2 — Chat killer feature

- [x] **2.1** Streaming chat endpoint (Qwen) — `POST /api/chat` via FastAPI `StreamingResponse` + LiteLLM `acompletion(stream=True)`, `X-Accel-Buffering: no`, intl DashScope compat
- [x] **2.2** RAG context builder — `app/llm/chat_context.py`: last-5 match summaries + H2H last-3 + top scorers stub (player_season_stats empty for now — Phase 3)
- [x] **2.3** Chat widget UI — `components/ChatWidget.tsx` client, plain `fetch().body.getReader()` streaming (no Vercel AI SDK dep), `/match/[id]` page integrates PredictionBar + TerminalBlock + ChatWidget
- [x] **2.4** Suggested prompts — `GET /api/chat/suggest/:match_id` returns VN peer-tone chips, hydrated on widget mount. 6 prompt tests TDD'd. **Live at https://predictor.nullshift.sh/match/:id**

## 4. Phase 3 — Polish

- [x] **3.1** xG table page — `GET /api/table?season=...` + `/table` route with W/D/L/points and xGF/xGA/xGD delta column (neon for overperformers, red for under). **Live https://predictor.nullshift.sh/table**
- [x] **3.2** Team profile pages — `GET /api/teams/:slug` + `/teams/[slug]` with stat grid, form (last-10 W/D/L colored), top-scorers table w/ goals-minus-xG delta, recent + upcoming fixtures. **Live https://predictor.nullshift.sh/teams/arsenal**
- [x] **3.3** Historical accuracy tracking — `scripts/backtest.py` + `GET /api/stats/accuracy` + 4-stat chip on dashboard. **2024-25: 55.0% acc (baseline 40.8%), log-loss 1.00; 2025-26: 45.8% acc (baseline 41.7%), log-loss 1.06** over 699 backtested matches.
- [x] **3.4** Player stats ingest — `scripts/ingest_players.py` via Understat, 42 tests, 1062 rows (2024-25 + 2025-26). Unblocks top-scorer chat context.

## 5. Phase 4 — NullShift ecosystem

- [x] **4.1** Prediction fingerprint (chain-agnostic) — SHA-256 canonical-JSON hash computed on every prediction (4 TDD tests, `app/onchain/commitment.py`). Stored in `predictions.commitment_hash`, surfaced on API + `CommitmentBadge` FE (full hash on `/match/:id`, compact on dashboard). Anyone can recompute from the public prediction body and verify integrity — **no chain dependency**. Broadcast/publisher + Monad-specific artifacts dropped per user decision 2026-04-18.
- [~] **4.2** Non-custodial prediction market — **explicitly SKIPPED**. `docs/environment.md` out-of-scope rule: "Betting integration (regulatory risk, Vietnam context)". Not built.

---

## 6. Open questions (resolve during build)

Mirror of [`docs/environment.md`](./docs/environment.md). Answer inline or in `PROGRESS.md` when decided.

- [ ] Historical data depth: backfill 3 seasons or 5?
- [ ] Dixon-Coles `rho`: calibrate or use standard `0.1`?
- [ ] Chat history: session-only or persist per device fingerprint?
- [ ] Cache TTL for predictions: regenerate per scrape or daily?

---

## 7. How to work with this plan

1. Before touching code, read [`CLAUDE.md`](./CLAUDE.md) + the relevant `docs/` section.
2. Pick the next unchecked phase item. Do it.
3. Append an entry to [`PROGRESS.md`](./PROGRESS.md): **date + time + one-line summary** (not a dump of the diff).
4. If scope, stack, or a principle changes, update the affected `docs/` file first — the plan follows the docs, not the other way around.
