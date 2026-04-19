# Launch post drafts

## Hacker News (Show HN)

**Title:** Show HN: EPL Prediction Lab — open-methodology Poisson+Elo+xGBoost ensemble for top-5 European football

https://predictor.nullshift.sh

I built a solo-hosted football prediction site over the past month. Every
piece is publicly recomputable:

- **Model**: Dixon-Coles Poisson on recent xG → temperature-scaled → blended
  with a goal-weighted Elo (25%) → a second-pass XGBoost classifier (30%).
  Each match's xG is opponent-defense-adjusted so 2.0 xG against a weak
  defense counts less than 1.5 against a strong one.
- **Validation**: walk-forward backtest across 2,263 EPL matches / 6 seasons
  shows the full ensemble beats raw Poisson by +0.71% accuracy, −1.73%
  log-loss. Every prediction ships with a SHA-256 commitment hash you can
  recompute from the public body to verify the model view wasn't retconned.
- **Live mode**: 10-second systemd timer polls API-Football during match
  windows, recomputes remaining-Poisson from (90 − minute), publishes score
  + in-play probabilities + goal-event timeline. Telegram + web push goal
  alerts for followed teams.
- **Markets beyond 1X2**: Half-time / HT-FT 9-grid, O/U 1.5/2.5/3.5, BTTS,
  clean sheets, anytime goalscorer per player (share of team xG × match λ).
  Each market comes with fractional Kelly stake next to the bookmaker odds.
- **Stack**: Python 3.12 / FastAPI / asyncpg, Next.js 15 / Tailwind,
  Postgres 16 + pgvector, LiteLLM→Qwen for plain-language analysis, Docker
  Compose on a single Hostinger VPS. 90+ unit tests. Engine + FE on GitHub:
  https://github.com/tuantqse90/epl-prediction-lab

Current scope: EPL, La Liga, Serie A, Bundesliga, Ligue 1. Five locales
(EN / VI / TH / ZH / KO). Things I'd love feedback on:

1. Is the opponent-adjusted xG double-counting anything? I'm computing raw
   strengths first, then rescaling each match's xG by the opponent's raw
   defense coefficient, then rebuilding — but this feels like it could be
   unstable for early-season teams.
2. XGBoost weight 0.30 vs Elo 0.25 — what would you pick? My backtest data
   isn't big enough to grid-search cleanly; right now it's gut feel.
3. The "always honest" framing (commitment hash + publicly reproducible
   math) is my marketing angle — is anyone actually skeptical that Opta/
   FiveThirtyEight retroactively tweaked predictions? Or is this solving a
   problem nobody has?

Not a product; no monetization, no ads, no email capture. The model runs
and the page loads.

---

## r/soccerbetting

**Title:** [Free tool] Poisson+Elo+XGBoost ensemble, open methodology, top-5 European leagues — looking for brutal feedback

Hi all. Solo dev here. Built https://predictor.nullshift.sh because I
wanted to see what an honest, auditable model would look like for value
betting.

**What's in the box:**
- 1X2 probabilities with 68% bootstrap confidence bands — model admits when
  it doesn't know. No more "70%" with zero context.
- Kelly stake column next to every outcome, fractional (capped 25%).
- Derived markets from the same Poisson matrix: O/U 2.5, BTTS, first-goal-
  scorer per player, HT winner, HT-FT 9-grid.
- /roi page shows cumulative P&L at selectable edge thresholds (3/5/7/10%)
  this season per league.
- /benchmark page publicly tracks model vs "always home" vs uniform-random,
  rolling 7/30/90 day + full season.
- Every prediction has an on-page SHA-256 fingerprint so you can verify I
  didn't sneak-edit after the fact.

**What's NOT in the box:** affiliate bookmaker links, betting tips with
"confidence 95%" emoji, account sign-up, paywall.

**Honest gaps I'd love pushback on:**
- Only top-5 have real xG depth. Championship / Eredivisie / MLS / J-League
  are registered on the backend but don't have enough history yet.
- Injury impact shrinks team λ by 0.6 × xG-share-missing. Crude — no
  distinction between "key CB out" vs "4th striker out".
- The Telegram bot posts picks but I haven't shipped automated accountability
  recaps yet (manual weekly post).

DM or reply with findings. I ship fast — bad pick yesterday gets a fix
today.

---

## Twitter/X thread

1/  I built a football prediction model. Entire methodology public. Every
    prediction hashable so you can prove I didn't rewrite history.
    https://predictor.nullshift.sh

2/  The math: Dixon-Coles Poisson on xG → temperature calibration → 25%
    Elo ensemble → 30% XGBoost second-pass. Opponent-defense-adjusted so
    xG against a bottom team doesn't inflate ratings.

3/  Validated on 6 seasons × 2,263 finals. Full ensemble beats raw Poisson
    by −1.73% log-loss. Lower = better. Baseline "always home" gets 41.7%;
    model sits at 53.0%.

4/  Markets: 1X2, O/U 2.5, BTTS, HT winner, HT-FT grid, anytime scorer
    per player. Each outcome carries a Kelly stake so you know how much
    of bankroll to risk.

5/  Every prediction shows 68% confidence intervals from a 30-sample
    bootstrap of the team history. Model that doesn't admit uncertainty
    is selling you something.

6/  Commitment hash on every prediction. Recompute from public data, prove
    the probabilities weren't retconned. Not onchain, just honest.

7/  Free forever. No ads, no email capture, no affiliate links. Five
    languages (EN/VI/TH/ZH/KO). Tell me what's broken.
