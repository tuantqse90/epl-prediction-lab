# Development Principles

## Code style

- **Python**: `black` + `ruff`, type hints everywhere, async by default
- **TypeScript**: strict mode, no `any`, Prettier
- **No over-engineering**: solo project, optimize for iteration speed
- **Tests**: unit tests for Poisson math (critical), skip tests for glue code

## LLM usage principles

- **Never** ask the LLM for numbers (probabilities, scores). Math engine only.
- **Always** ground LLM output in data (prompt templates enforce this)
- **Cache** LLM outputs in DB (reasoning rarely changes between scrapes)
- **Monitor** token usage weekly; alert if over $5/month

## Data principles

- **Source priority**: Understat (xG) > FBref (depth) > API-Football (live)
- **Scrape cadence**: weekly for historical, on-demand for fixtures
- **Cache everything**: Understat rate limits are tight (8 req/min)
