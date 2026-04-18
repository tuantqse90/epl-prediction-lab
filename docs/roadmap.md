# Roadmap — MVP → v2

## Phase 1: MVP (2–3 days of focused work)

1. Set up repo + project structure
2. Postgres (self-hosted, VPS) + `pgvector` + migrations
3. Scraper: pull current season EPL from Understat via `soccerdata`
4. Poisson engine: compute predictions for upcoming fixtures
5. LLM reasoning layer: Qwen-Turbo integration via LiteLLM
6. FastAPI endpoints: `/matches`, `/predictions/:id`
7. Next.js dashboard with match cards + prediction bars
8. Deploy: backend on Railway, frontend on Cloudflare Pages

## Phase 2: Chat killer feature

9. Chat endpoint with Qwen streaming
10. RAG context builder (pull match + player data)
11. Chat widget UI with streaming
12. Suggested prompts per match

## Phase 3: Polish

13. xG table page
14. Team profile pages
15. Historical accuracy tracking (did our predictions work?)
16. Backfill 3 seasons of historical data

## Phase 4: (optional) NullShift ecosystem integration

17. Prediction commits on-chain (Monad testnet) — proof of prediction timestamp
18. Non-custodial prediction market (NullShift Escrow pattern)
