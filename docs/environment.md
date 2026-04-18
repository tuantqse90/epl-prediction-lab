# Environment, Scope, Open Questions

## Secrets / env vars

```bash
# Backend
DASHSCOPE_API_KEY=sk-...                                 # Qwen
ANTHROPIC_API_KEY=sk-...                                 # fallback
DATABASE_URL=postgresql://epl:...@db:5432/epl            # asyncpg DSN, self-hosted PG on VPS
API_FOOTBALL_KEY=...                                     # optional secondary source

# Frontend
NEXT_PUBLIC_API_URL=https://api.predictor.nullshift.sh
```

## Out of scope (do not build)

- User accounts / auth (solo use for v1)
- Betting integration (regulatory risk, Vietnam context)
- Other leagues (EPL first; expand only if this works)
- Mobile app (responsive web is enough)
- Auto-post to Nerf Dev blog (explicitly decided against)
- Social features / leaderboards

## Open questions (resolve during build)

- [ ] Historical data depth: backfill 3 seasons or 5?
- [x] ~~Dixon-Coles `rho` parameter: calibrate or use standard `0.1`?~~ **Resolved 2026-04-18**: joint grid (last_n × ρ) on 2024-25, verified on 2025-26 holdout → best is **last_n=12, ρ=−0.15** (log-loss 0.9762 / 1.0438, acc 57% / 47%). Baked into `DEFAULT_LAST_N=12`, `DEFAULT_RHO=-0.15`, `MODEL_VERSION="poisson-dc-v2"`.
- [ ] Chat history: session-only, or persist per device fingerprint?
- [ ] Cache TTL for predictions: regenerate on every scrape, or daily?
