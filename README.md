```
 ██████╗ ██████╗ ███████╗██████╗ ██╗ ██████╗████████╗ ██████╗ ██████╗
 ██╔══██╗██╔══██╗██╔════╝██╔══██╗██║██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗
 ██████╔╝██████╔╝█████╗  ██║  ██║██║██║        ██║   ██║   ██║██████╔╝
 ██╔═══╝ ██╔══██╗██╔══╝  ██║  ██║██║██║        ██║   ██║   ██║██╔══██╗
 ██║     ██║  ██║███████╗██████╔╝██║╚██████╗   ██║   ╚██████╔╝██║  ██║
 ╚═╝     ╚═╝  ╚═╝╚══════╝╚═════╝ ╚═╝ ╚═════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝
```

> **xG doesn't lie. The bookies do.**
> An opinionated 3-leg ensemble on top-5 European leagues, commitment-hashed before kickoff.

[![live](https://img.shields.io/website?url=https%3A%2F%2Fpredictor.nullshift.sh&style=flat-square&label=live&up_color=E0FF32&up_message=predictor.nullshift.sh)](https://predictor.nullshift.sh)
[![stars](https://img.shields.io/github/stars/tuantqse90/epl-prediction-lab?style=flat-square&color=E0FF32)](https://github.com/tuantqse90/epl-prediction-lab/stargazers)
[![last commit](https://img.shields.io/github/last-commit/tuantqse90/epl-prediction-lab?style=flat-square&color=E0FF32)](https://github.com/tuantqse90/epl-prediction-lab/commits)
[![python](https://img.shields.io/badge/python-3.12-E0FF32?style=flat-square)](https://github.com/tuantqse90/epl-prediction-lab)
[![next](https://img.shields.io/badge/next-15-E0FF32?style=flat-square)](https://github.com/tuantqse90/epl-prediction-lab)

```
[ LIVE ]  https://predictor.nullshift.sh
[ PROOF ] https://predictor.nullshift.sh/proof
[ FEED  ] https://t.me/worldcup_predictor
[ REPO  ] https://github.com/tuantqse90/epl-prediction-lab
```

---

## tl;dr — the numbers

```
┌──────────────────────────────────────────────────────────────┐
│  WINDOW         MATCHES   MODEL   BOOKIES   EDGE             │
│  ─────────────  ───────   ─────   ───────   ──────           │
│  last 30 days   142       52.1%    50.0%    +2.1pp ✓         │
│  season 25/26   ~1.5k     --       --       --               │
│  all-time 2019+ 3,760     52.0%    54.0%    -2.0pp           │
└──────────────────────────────────────────────────────────────┘
```

We beat the market on recent form. Bookies edge us out cumulatively — and we say
so on the homepage. Every prediction is SHA-256 hashed before kickoff, so the
record can't be edited after.

```
log-loss     : 1.01 (vs uniform 1.10, bookies 1.00)
scored       : 3,760 matches since 2019-08-09
stored preds : 5,600+ (every re-predict committed)
cost         : $0 per pick, forever
```

---

## architecture

```
    ┌─────────────────────────────────────────────────────────────┐
    │                      DATA PIPELINE                          │
    │                                                             │
    │  soccerdata ── Understat xG per shot ─┐                     │
    │  API-Football ── live minute+events ─┤                      │
    │  The Odds API ── 1X2 + O/U live ─────┤── Postgres 16 +      │
    │  football-data.co.uk ── hist odds ───┤   pgvector           │
    │  api-football ── lineups + injuries ─┘                      │
    └─────────────────────────────────────────────────────────────┘
                                │
                                ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                   ENSEMBLE (3 legs)                         │
    │                                                             │
    │   ▲  Poisson + Dixon-Coles                                  │
    │      ├── opponent-adjusted xG strengths (last 12)           │
    │      ├── exponential decay (γ=0.9)                          │
    │      ├── venue-split home/away coefficients                 │
    │      └── temperature scaled (T=1.35, per-league tuned)      │
    │                          │                                  │
    │   ● Goal-weighted Elo          │  convex blend 1 (75/25)    │
    │      ├── K=20, HFA=+70         │                            │
    │      └── 3-way via margin CDF  ▼                            │
    │                                                             │
    │   ◆ XGBoost softprob           │  convex blend 2 (85/15)    │
    │      ├── 21 features (strength ×12, Elo ×3, rest ×3, ...)   │
    │      └── trained 2019-2023, held out 24-25 (acc 52.8%)      │
    │                          │                                  │
    │                          ▼                                  │
    │              P(home) · P(draw) · P(away)                    │
    │              E[home goals] · E[away goals]                  │
    │              Top-5 scorelines  ·  Bootstrap CI (15 samples) │
    └─────────────────────────────────────────────────────────────┘
                                │
                                ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                 POST-PROCESSING                             │
    │                                                             │
    │   • injury-adjusted λ (shrink by α × injured_xg_share)      │
    │   • weather multiplier (−8% on wind ≥ 30 km/h)              │
    │   • live λ recompute from remaining minutes + current score │
    │   • SHA-256 commitment hash over canonical payload          │
    │   • Qwen-generated reasoning + post-match recap             │
    └─────────────────────────────────────────────────────────────┘
```

---

## receipts

Walk-forward backtest, **2,263 matches × 6 seasons** of Premier League.
Strengths + Elo computed from matches strictly before kickoff. No future leakage.

```
config                              acc     log-loss    Δ vs baseline
─────────────────────────────────────────────────────────────────────
baseline (raw Poisson)              52.32%  1.0015      —
+ decay (γ=0.9)                     52.15%  1.0018      +0.0003
+ Elo ensemble (25%)                53.29%  0.9866      -0.0149
+ opp-adjusted strengths only       52.37%  0.9969      -0.0046
= full stack                        53.03%  0.9843      -0.0172  ✓
─────────────────────────────────────────────────────────────────────
uniform random                      33.33%  1.0986      +0.1143
```

Calibration test on 2025-26 live predictions (`/stats`):

```
when model says    it happened    n     reliability
────────────────   ───────────    ───   ─────────────
50–60%             55%            312   ████████░ ≈ calibrated
60–70%             66%            94    █████████
70–80%             71%            18    ██████████
```

---

## what you get at `/match/:id`

```
┌──────────────────────────────────────────────────────────────┐
│  MAN UTD  vs  ARSENAL                              sat 16:30 │
│  ────────────────────────────────────────────────────────    │
│                                                              │
│  P(home)  28%  ■■■■■                                         │
│  P(draw)  25%  ■■■■                                          │
│  P(away)  47%  ■■■■■■■■■                                     │
│                                                              │
│  Top scoreline        1–2  (E[goals] 1.21 / 1.74)            │
│  Bootstrap CI         47% / 38%–55%                          │
│  Commitment hash      9e3f...a1c2                            │
│                                                              │
│  Model picks          ARSENAL · 47% · +6% vs market          │
│  Kelly stake          2.1% of bankroll                       │
│                                                              │
│  + injuries · H2H · lineups · xG momentum · BTTS / O-U /     │
│  + HT-FT 9-grid · anytime goalscorer odds · weather · chat   │
└──────────────────────────────────────────────────────────────┘
```

---

## stack

```
backend   Python 3.12 · FastAPI · asyncpg · Pydantic v2 · NumPy · SciPy
          xgboost · soccerdata · LiteLLM → DashScope qwen-turbo
          pytest, 90+ tests, all strict-typed

frontend  Next.js 15 App Router · Tailwind v3 · strict TypeScript (no any)
          5 locales (EN/VI/TH/ZH/KO) with per-locale TZ, RSC-first

db        Postgres 16 + pgvector (self-hosted, Docker volume)

infra     Docker compose · Caddy + LE · Cloudflare · systemd timers
          ├── live ingest   every 10s while a match is live
          ├── lineups       every 15m in 3h pre-kickoff window
          ├── news RSS      every 2h
          ├── daily         06:00 UTC (predict + reason + recap + post)
          └── weekly        Mon 02:05 UTC (full refit)

deploy    `git push vps main` → bare repo post-receive hook rebuilds
          images, restarts containers, smoke-tests api + web. No GH needed.
```

---

## run it

```bash
$ git clone https://github.com/tuantqse90/epl-prediction-lab
$ cd epl-prediction-lab
$ cp .env.example .env          # fill DASHSCOPE_API_KEY at minimum
$ docker compose up -d

# seed
$ docker compose exec api python scripts/ingest_season.py   --season 2025-26
$ docker compose exec api python scripts/ingest_odds.py     --season 2025-26
$ docker compose exec api python scripts/train_xgboost.py   --holdout-season 2024-25

# predict (with Qwen reasoning)
$ docker compose exec api python scripts/predict_upcoming.py \
    --horizon-days 14 --with-reasoning

# backtest any combo
$ docker compose exec api python scripts/compare_configs.py --all-seasons --all-leagues
$ docker compose exec api python scripts/tune_ensemble.py   # grid-search blend weights

# tests
$ cd backend && python -m pytest
```

App at `http://localhost:3500`, API at `http://localhost:8500/docs`.

---

## commitment hashing — why you can trust the record

```
canonical_payload = {
    "schema_version": 1,
    "match_id": 328,
    "model_version": "v5:rho=-0.15:T=1.35:elo=0.25:xgb=0.15",
    "p_home_win": 0.284102,
    "p_draw":     0.253014,
    "p_away_win": 0.462884,
    "top_scoreline": [1, 2],
    "e_home_goals": 1.212341,
    "e_away_goals": 1.743210,
    "kickoff_time": "2026-04-20T15:30:00+00:00",
}
#                                     │
#                                     ▼
#            hashlib.sha256(json.dumps(sorted_keys=True, separators=",:"))
#                                     │
#                                     ▼
#                     9e3f4a...a1c2b7   ← stored in predictions.commitment_hash
```

Probabilities are rounded to 6 decimal places so floating-point re-runs
produce the same hash. Any third party with the payload body can recompute
the hash and verify the server-stored one matches — no trusted computing,
no oracle, no on-chain fees. Honest math, public encoding.

Page: [/proof](https://predictor.nullshift.sh/proof) walks the full
verification flow.

---

## repo layout

```
.
├── backend/
│   ├── app/
│   │   ├── api/           FastAPI routers  (matches, stats, chat, push, …)
│   │   ├── core/          settings + asyncpg pool
│   │   ├── ingest/        source-specific normalizers + upserts
│   │   ├── llm/           prompt builders · Qwen reasoning + recap
│   │   ├── models/        Poisson · Dixon-Coles · Elo · XGBoost · features
│   │   ├── predict/       orchestration + persist + commitment
│   │   ├── weather/       open-meteo adapter
│   │   └── onchain/       SHA-256 commitment (chain-agnostic)
│   ├── scripts/           ingest/backtest/predict/fit/tune/post_*
│   └── tests/             pytest, 90+ tests
├── frontend/
│   ├── app/               /, /match/:id, /proof, /stats, /last-weekend,
│   │                      /teams/:slug, /scorers, /benchmark, /history, …
│   ├── components/        cards · charts · chat · terminal blocks
│   └── lib/               api client · i18n · team colors · TS Poisson port
├── ops/                   daily.sh · weekly.sh · systemd unit files
├── docs/                  architecture · model · principles · deploy
├── docker-compose.yml     api + web + postgres + named volumes
└── README.md              you are here
```

---

## principles

- **Never ask an LLM for a number.** Probabilities, scorelines, stakes all
  come from the math engine. The LLM is there to *explain* the number.
- **Every feature earns its place.** `compare_configs.py` runs walk-forward
  across 6 seasons; if a flag doesn't beat baseline on log-loss, it's reverted.
- **No future leakage.** Backtests filter history by `kickoff_time < as_of`,
  always. Any feature that reads same-day signals is out of scope.
- **Commit before kickoff.** A prediction without a pre-kickoff hash is
  marketing, not a forecast.
- **One accent color.** Pure black surface, neon-lime `#E0FF32`, black text
  on neon fills. Payy-inspired. No feature gets its own color.

---

## license

Personal project. Unlicensed — read, fork, learn. Don't expect support,
don't bet your rent, and if the model costs you money, that's on you.
