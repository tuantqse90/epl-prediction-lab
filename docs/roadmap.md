# Roadmap — MVP → v2 → Sharp-bettor analytics

## Phase 1: MVP (closed)

1. Repo + project structure
2. Postgres on VPS + pgvector + migrations
3. Scrape EPL via Understat (`soccerdata`)
4. Poisson + Dixon-Coles engine
5. Qwen reasoning via LiteLLM
6. FastAPI endpoints
7. Next.js dashboard (Payy tokens)
8. Deploy VPS + Caddy + TLS

## Phase 2: Chat (closed)

9. Streaming chat endpoint (Qwen)
10. RAG context builder
11. Chat widget with SSE streaming
12. Suggested prompts per match

## Phase 3: Polish (closed)

13. xG table page
14. Team profile pages
15. Historical accuracy tracking
16. Backfill 3 seasons (later extended to 7)

## Phase 4: Ecosystem (partial)

- **4.1 (closed)** SHA-256 commitment hash on every prediction, surfaced on the UI. Chain-agnostic. Anyone can recompute from the public body.
- **4.2 (skipped)** Non-custodial prediction market — dropped 2026-04-19 per `docs/environment.md` out-of-scope rule (betting regulation, Vietnam context).

Chain publishing was considered and dropped: the hash is already publicly recomputable, so posting to a chain adds custody/gas burden without improving verifiability for users.

## Phase 5+: Sharp-bettor analytics (current)

See [`plan-new.md`](../plan-new.md) for the full checklist. Headline items:

- **Phase 5** — Closing-Line Value (CLV) logging + `/proof` CLV card
- **Phase 6** — Correlated markets (BTTS, Over/Under, Asian handicap, same-game parlay pricing from the xG matrix)
- **Phase 7** — Backend fractional-Kelly + virtual bankroll with compounded PnL + drawdown
- **Phase 8** — Per-league edge map (hide QuickPicks where 30-day ROI < 0)
- **Phase 9** — Sharp-exchange reference prices (Betfair + Polymarket no-vig)
- **Phase 10** — In-play (parked; high infra cost, revisit after 5–9)

**Hard boundary.** All Phase 5+ work is analytics + display only. No custody, no stake placement, no real-money bridge.

## How phases are tracked

- Check-offs for Phase 1–4 live at the bottom of [`plan.md`](../plan.md)
- Check-offs for Phase 5+ live in [`plan-new.md`](../plan-new.md)
- Chronological narrative in [`PROGRESS.md`](../PROGRESS.md)
