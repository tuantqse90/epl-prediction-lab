---
slug: all-time-gap
title: The -2pp gap vs bookmakers all-time — what's actually missing
date: 2026-04-18
excerpt: Our model beats bookies by +2.1pp on recent 30 days, loses by -2.0pp across 3,760 finals since 2019. Here's the honest diagnosis.
tags: [model, calibration, honest]
---

Here are the numbers our /proof page publishes:

| window | matches | model | bookies | delta |
| --- | --- | --- | --- | --- |
| last 30 days | 142 | 52.1% | 50.0% | **+2.1pp** ✓ |
| current season | 1,480 | 50.4% | 53.3% | −2.9pp |
| all-time since 2019 | 3,760 | 52.0% | 54.0% | −2.0pp |

Both the recent win and the long-run loss are honest. Neither was
cherry-picked. This post is about the second one — what keeps the model
from matching bookmakers over the long run.

## Bookmakers are a hard benchmark

Football bookmakers don't price with a 3-leg xG ensemble, but they do
aggregate signals the model can't: team news that leaks hours before
official lineups, market pressure from sharp money, local knowledge
about referee tendencies, and every other non-xG covariate that
eventually trickles into the closing line. The closing price of a major
European match is one of the most informative single numbers you can
buy — the whole sharp-betting industry exists to exploit the thin 2-3%
edge over opening lines.

Beating bookies at argmax accuracy over 3,760 matches would be
extraordinary. Matching them would be state-of-the-art. Being 2pp
behind is not a failure — it's where most public models land. What we
want to know is whether that 2pp gap is closeable or whether it's the
market's edge over any pure xG model.

## Candidates for the gap

Here are the specific things I think contribute to the -2pp, ranked by
likely magnitude:

### 1. Injury / lineup information (~0.8pp estimate)

Our injury data is API-Football's player-status feed, refreshed daily.
Bookmakers react to late fitness tests, which typically land 1–3 hours
before kickoff. For ~10% of high-impact matches, that information is
worth 3–5pp on the 1X2. 10% × 4pp ≈ 0.4pp directly, with a spillover
effect on calibration.

The injury-adjusted λ machinery is in the code
(`predict/service._injury_impact`) but only applies to upcoming
fixtures in production, and uses coarse xg-share shrinkage rather than
position-specific modeling. A GK injury hits differently than a central
defender's, and both hit differently than a striker's. Not modeled.

### 2. Non-xG signals market aggregates (~0.6pp)

xG captures shot quality but ignores:

- Set-piece specialist quality (an xG shot at 0.05 from a poor FK
  taker is different from the same xG from Messi).
- Fatigue signals beyond rest days (midweek European matches, travel,
  weather at training).
- Referee tendencies (pk rate, red-card rate, stoppage time).
- Pre-match tactical story (manager leaving, contract dispute, locker
  room).

Bookmakers get all of this implicitly through market pressure. Our model
gets none of it.

### 3. XGBoost training data limits (~0.3pp)

The booster was trained on all multi-league seasons in DB (2019–2025)
with current season held out. Features are 21 dimensions. For a
classifier operating in a 3-class problem with highly variable base
rates across leagues and seasons, 3,265 training rows is workable but
not abundant. More data or a wider feature set (betting line movement,
referee stats, squad value delta) would likely move the needle.

### 4. Temperature scaling is global (~0.1pp)

T=1.35 applies to every prediction. A proper per-league fit would run
walk-forward with different T values upstream, not just apply T' on top
of stored probs. When we tried it naively (post-hoc), t'≈1.0 for every
league — meaning the stored T=1.35 was already near-optimal *given
everything else*, but that doesn't rule out a better T with different
features feeding in.

### 5. Pre-closing vs closing line comparison (~0.2pp)

Our `/api/stats/comparison` pulls the latest captured odds per match,
which in practice is usually the closing line from Pinnacle or similar.
Comparing our ~48-hours-before-kickoff prediction argmax to a closing-
line argmax compares two signals that had very different amounts of
information. The gap would narrow if we compared our prediction to the
market opening line instead — but we don't have opening lines for most
historical matches.

## What we can realistically fix

In priority order:

**Close (2) by ~0.3pp**: Add referee stats (pk/match, red/match) as
XGBoost features. We have `matches.referee` populated; a simple rolling
stat join is 1 afternoon of work.

**Close (3) by ~0.2pp**: Retrain XGBoost weekly — already shipped as
of today's `ops/weekly.sh`. Over 6 months this should help naturally.

**Close (1) by ~0.3pp**: Move injury-adjusted λ logic to use
position-weighted impact (GK > CB > CM > winger > striker) rather than
flat xg-share. Dataset already has positions on lineups; map to impact
coefficients, refit.

**Partially close (4)**: Set up a proper per-league T fit that runs
walk-forward rather than post-hoc. Half a day of work; might be worth
0.05-0.15pp.

Doing all four brings the expected gap from −2.0pp to around −1.2pp to
−1.4pp. At that point the remaining gap is roughly what a sharp retail
bettor fights for.

## What we can't fix without market data

(5) is structural. The model operates on public data 2–48 hours before
kickoff. The market operates on all-available information up to the
final whistle before money stops flowing in. No feature engineering on
public xG will close that gap.

## The honest answer

The model beats the market on recent form by genuine edge (XGB leg
working for first time + tighter blend weights). It loses cumulatively
because bookmakers aggregate information our feature set doesn't include.
We'll chip at the gap one feature at a time. We'll show both numbers
while we do.

If you want the model to beat bookies at argmax on ≥5,000 future
matches, you want a different product than this one. If you want a
cheap, open, reproducible, hash-committed predictor that's within 2pp
of the global professional average — that's what this site is.
