# Project Structure

```
epl-lab/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry
│   │   ├── api/
│   │   │   ├── matches.py       # /api/matches endpoints
│   │   │   ├── predictions.py   # /api/predictions
│   │   │   ├── chat.py          # /api/chat (streaming)
│   │   │   └── teams.py
│   │   ├── core/
│   │   │   ├── config.py        # env, LiteLLM setup
│   │   │   ├── db.py            # asyncpg / SQLAlchemy — DATABASE_URL-driven
│   │   │   └── llm.py           # LiteLLM router
│   │   ├── scrapers/
│   │   │   ├── understat.py     # soccerdata wrapper
│   │   │   ├── fbref.py
│   │   │   └── api_football.py
│   │   ├── models/
│   │   │   ├── poisson.py       # Dixon-Coles engine
│   │   │   └── features.py      # team strength calc
│   │   └── prompts/
│   │       ├── reasoning.py     # prompt templates
│   │       └── chat.py
│   ├── scripts/
│   │   ├── scrape_weekly.py     # cron job entry
│   │   └── backfill_history.py
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # dashboard
│   │   ├── match/[id]/page.tsx
│   │   ├── table/page.tsx
│   │   └── teams/[slug]/page.tsx
│   ├── components/
│   │   ├── PredictionBar.tsx
│   │   ├── MatchCard.tsx
│   │   ├── ChatWidget.tsx
│   │   ├── XGComparison.tsx
│   │   └── TerminalBlock.tsx    # for reasoning output
│   ├── lib/
│   │   └── api.ts
│   ├── tailwind.config.ts
│   └── package.json
│
├── .github/workflows/
│   └── scrape-weekly.yml        # GH Actions cron
│
├── docker-compose.yml           # local dev
├── CLAUDE.md
└── README.md
```
