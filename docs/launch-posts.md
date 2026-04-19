# Launch posts — ready to publish

Copy-paste ready. Each post is self-contained; pick the channel, copy the body.

---

## 1. Show HN

**Title:** `Show HN: An xG Poisson + Elo + XGBoost ensemble that commits before kickoff`

**URL:** `https://github.com/tuantqse90/epl-prediction-lab`

**Body:**

```
Predictor.nullshift.sh — https://predictor.nullshift.sh

I got tired of "prediction sites" that never admit when they're wrong, so I
built one that can't hide.

Every fixture prediction is SHA-256 hashed from the probability body + kickoff
time and stored before the whistle. The exact canonical encoding is public
(sorted-keys JSON, probs rounded to 6dp). Anyone can recompute the hash from
the displayed numbers and verify I didn't edit them after full-time.

The model is a 3-leg ensemble:

  * Dixon-Coles Poisson on opponent-adjusted xG (last 12 matches, γ=0.9 decay,
    venue-split strengths, temperature scaled)
  * Goal-weighted Elo (K=20, HFA +70, 3-way via margin CDF)
  * XGBoost softprob on 21 features (attack/defense per side, Elo, rest days,
    derby flag)

Blended via two sequential convex combinations. The blend weights come from a
walk-forward grid search on 1,816 out-of-sample matches across EPL, La Liga,
Serie A, Bundesliga, and Ligue 1.

Current ensemble (elo=0.20, xgb=0.60): log-loss 0.9278, accuracy 56.2%.
Baseline (always-home): log-loss 1.0185, accuracy 44%.
Uniform random: log-loss 1.0986.

Last 30 days the model beats bookmakers by +2.1pp on 1X2 argmax (same matches,
devigged market probabilities). Over all 3,760 scored matches since 2019 it
loses to them by -2.0pp. I show both on /proof because cherry-picking recent
form is the whole game I'm trying not to play.

Stack:
  * Python 3.12 · FastAPI · asyncpg · Pydantic v2 · pytest
  * Next.js 15 App Router · Tailwind · strict TypeScript
  * Postgres 16 + pgvector (self-hosted VPS, Docker compose)
  * LiteLLM → Qwen for pre-match reasoning and post-match recap
  * systemd timers: 10s live, 15m lineups, 2h news, daily predict+reason,
    weekly backtest + XGB retrain
  * Caddy + LetsEncrypt + Cloudflare

5 locales (EN/VI/TH/ZH/KO) with per-locale timezone. No auth, no ads, no
tracking beyond first-party Plausible.

Repo (AGPL-free, personal): https://github.com/tuantqse90/epl-prediction-lab
Live: https://predictor.nullshift.sh
Methodology deep-dive: https://predictor.nullshift.sh/proof

Happy to answer anything about the math or the walk-forward methodology.
```

**Submit tips:**
- Post between 07:00–09:00 PT (16:00–18:00 Asia) weekdays to hit US morning
- First comment should answer "how is this different from [other prediction
  site]?" preemptively. Draft below.

**First comment (seed discussion):**

```
Two specific differences from most prediction sites I've looked at:

1. Commitment hash. Every probability triple is SHA-256 hashed from the
   exact JSON body at prediction time. If I silently edit a number after
   the match, the hash no longer matches. Third parties can verify.

2. Negative evidence is front-and-center. /proof shows 30-day, season, and
   all-time model vs bookie head-to-head — the model beats bookies on
   recent form by +2.1pp and loses cumulative by -2.0pp. If I was trying
   to sell tips I'd hide the second number.

Also the walk-forward backtest is all in the repo (scripts/compare_configs,
scripts/tune_ensemble, scripts/backtest). You can rerun it locally with
docker compose up and verify my claims.
```

---

## 2. Reddit — r/soccer

**Title:** `[OC] Open-source 3-leg ensemble for top-5 European leagues — commits probabilities before kickoff so you can verify I don't edit them after`

**Body:**

```
Link: https://predictor.nullshift.sh

Built a hobby prediction lab for EPL, La Liga, Serie A, Bundesliga, Ligue 1.
Model is open source. Methodology is public. Every prediction is hash-
committed before the match starts so if I edit the numbers after full-time,
the hash breaks and you can tell.

What you get on a match page:
- 1X2 probabilities + top-5 scorelines + expected goals per side
- Bootstrap 68% CI on each outcome
- Anytime goalscorer odds (xG-derived, not bookmaker-copied)
- Over/Under 1.5/2.5/3.5, BTTS, Clean Sheet, HT winner, HT/FT 9-grid
- Kelly stake when there's edge vs the market
- Qwen-generated reasoning per fixture + post-match recap (what model got
  right and wrong and why)

Model is 3 legs:
- Dixon-Coles Poisson on opponent-adjusted xG from Understat
- Goal-weighted Elo (K=20, home advantage +70)
- XGBoost softprob on 21 features (attack/defense ratings, Elo, rest days,
  derby flag)

Blended via walk-forward grid search — weights optimized on 1,816 out-of-sample
matches. No future leakage: every feature computed strictly from matches
before kickoff.

Honest numbers on /proof:
- Last 30 days: 52.1% model vs 50.0% bookmakers (+2.1pp)
- All-time 3,760 matches: 52.0% model vs 54.0% bookmakers (-2.0pp)

No ads, no tracking, no bet-now buttons, no signup. Repo:
https://github.com/tuantqse90/epl-prediction-lab
```

---

## 3. Reddit — r/algobetting

**Title:** `Open-source 3-leg ensemble (Dixon-Coles + Elo + XGBoost) — beats market recent, loses all-time, here's the walk-forward methodology`

**Body:**

```
https://predictor.nullshift.sh · code https://github.com/tuantqse90/epl-prediction-lab

3-leg ensemble on top-5 European leagues:

1. Dixon-Coles Poisson — strengths from opponent-adjusted xG, last 12
   matches, γ=0.9 exponential decay, venue split, temperature scaled T=1.35.
   Standard DC rho correction on low-score cells.

2. Goal-weighted Elo — K=20, home advantage +70 points, 3-way via margin
   CDF (exp fit to historical draw rates). Rebuilt from scratch every
   prediction — no stateful drift.

3. XGBoost multi:softprob on 21 features:
   - attack/defense coefficients per side (overall + home + away) = 12
   - Elo ratings per side + diff = 3
   - days rest per side + diff = 3
   - league average goals + home advantage constant + is-derby flag = 3

Blended with two sequential convex combinations. Weights picked by grid
search over 1,816 out-of-sample matches (2024-25 + 2025-26 across 5 leagues).

Current weights: elo=0.20, xgb=0.60. Log-loss 0.9278, accuracy 56.22%.
Uniform baseline 1.0986. Always-home 44%.

Backtest methodology is strict walk-forward. Scripts in the repo:
- scripts/backtest.py — single-config evaluation
- scripts/compare_configs.py — feature-flag ablation
- scripts/tune_ensemble.py — grid search over blend weights
- scripts/fit_temperature.py — T calibration

Bookmaker comparison on /proof: model beats the argmax of devigged 1X2 prices
by +2.1pp over the last 30 days (n=142), loses by -2.0pp cumulatively since
2019 (n=3,760). I display both because either alone would be cherry-picking.

Kelly staking is shown per outcome when model edge ≥ 5pp vs fair price.
Fractional Kelly capped at 25% of bankroll.

What's NOT in the model yet (honest list):
- No injury-impact features during backtest (injury-adjusted λ is applied
  only to upcoming fixtures via xg-share shrinkage, not stored historical).
- No per-league temperature (fit showed global T=1.35 is near-optimal).
- No weather features (applied multiplicatively to upcoming λ only, not in
  XGB features).
- XGB trained on all prior seasons → held out on current season. Retrained
  every Monday from systemd.

Curious if anyone has pointers on features that materially beat xG-derived
strengths. I've tried rest days, derby flag, Elo; all help. Venue-weighted
referee stats? Squad-value delta? Haven't tested these.
```

---

## 4. Twitter / X thread

**(hook tweet 1)**

```
"xG doesn't lie. The bookies do."

Built an open-source football prediction lab. Every 1X2 probability gets SHA-256
hashed before kickoff so I can't silently edit it after.

Last 30 days: model 52.1% vs bookies 50.0% ✓
All-time 3,760 matches: model 52.0% vs bookies 54.0% ✗

Both numbers visible. 🧵
```

**(tweet 2)**

```
Model is a 3-leg ensemble:

▲ Dixon-Coles Poisson on opponent-adjusted xG
● Goal-weighted Elo (K=20, HFA +70)
◆ XGBoost softprob on 21 features

Weights picked by walk-forward grid search on 1,816 out-of-sample matches.

Optimal: elo=0.20, xgb=0.60 → log-loss 0.9278, acc 56.2%
```

**(tweet 3)**

```
Commitment hash works like this:

1. Compute prediction: P(home)=0.284, P(draw)=0.253, P(away)=0.463
2. Canonical-encode: sorted-keys JSON, probs rounded to 6dp
3. SHA-256: 9e3f...a1c2
4. Store in DB with the prediction row
5. Third party recomputes from displayed probs → verifies

Receipts, not vibes.
```

**(tweet 4)**

```
Stack:

Python 3.12 + FastAPI + asyncpg
Next.js 15 App Router + Tailwind
Postgres 16 + pgvector
Qwen-Turbo for reasoning / recap
Docker compose on a €8/mo VPS
systemd timers: 10s live, 15m lineups, daily predict+reason, weekly retrain

No ads. No signup. No tracking.
```

**(tweet 5 — CTA)**

```
Live: predictor.nullshift.sh
Proof: predictor.nullshift.sh/proof
Code: github.com/tuantqse90/epl-prediction-lab
Telegram feed: t.me/worldcup_predictor

If you spot a bug or a better feature, PR welcome. 5 locales supported:
EN · VI · TH · ZH · KO.
```

---

## 5. Product Hunt — optional

**Tagline:** `Open-source football model that commits its probabilities before kickoff`

**Description:**

```
A 3-leg ensemble (Dixon-Coles Poisson + Elo + XGBoost) for top-5 European
leagues. Every prediction is SHA-256 hashed before the match starts, so the
model can't hide when it's wrong. 5 languages. No signup. Repo open.
```

---

## Checklist before posting

- [ ] Verify /proof page shows current numbers, not stale backtest
- [ ] README has 5 working badges (live / stars / last-commit / python / next)
- [ ] Repo has License file (or explicit "personal project, unlicensed")
- [ ] GitHub Discussions + Issues enabled
- [ ] Telegram channel @worldcup_predictor has recent posts
- [ ] Twitter/X handle ready to reply (if posting thread)
- [ ] First comment for Show HN pre-drafted
- [ ] Monitor repo for issues / stars in first 2 hours after post

## Timing

| Channel | Best window (Asia time) | Why |
|---|---|---|
| Show HN | 16:00–18:00 Tue/Wed | US morning weekday |
| r/soccer | 21:00–23:00 Sat/Sun | European evening, match-day peak |
| r/algobetting | 22:00+ Tue–Fri | Niche, less timing-sensitive |
| X/Twitter | 20:00–22:00 any | Asia + US overlap |

Do not post to all channels in the same hour — you want time to respond to
each before the next surge.

## Response templates

**"How is this different from [X prediction site]?"**
```
Two specific differences: (1) commitment hash on every prediction — third
parties can verify I don't edit numbers after full-time. (2) I publish negative
evidence front-and-center. The model beats bookies recent but loses all-time
over 3,760 matches. Both shown on /proof. Most sites hide the bad number.
```

**"Can I actually bet with this?"**
```
Kelly stake is shown where the model sees edge, but I'd think of it as a
peer-reviewed number, not advice. Fractional Kelly capped at 25%. No
guarantee on any individual match. I run no ads and take no percentage.
```

**"Why Vietnamese as the primary reasoning language?"**
```
Personal project — I'm Vietnamese. UI is 5 locales (EN/VI/TH/ZH/KO) but the
Qwen-generated reasoning was originally tuned for VN voice. English reasoning
is on the roadmap if there's demand.
```
