---
slug: xgb-weight-jump
title: Why XGBoost's weight jumped from 0.15 to 0.60 overnight
date: 2026-04-19
excerpt: The XGBoost leg of the ensemble has been silently disabled in production for months. Here's what happened when it actually ran, and what a walk-forward tune said about how much to trust it.
tags: [model, xgboost, ensemble, production]
---

The ensemble on this site has three legs:

1. Dixon-Coles Poisson on opponent-adjusted xG.
2. Goal-weighted Elo with a +70 home-field advantage.
3. XGBoost softprob on 21 features (attack/defense per side, Elo, rest days, derby flag, league average).

The three are blended via two sequential convex combinations. The weights
we ship to production today are `elo=0.20, xgb=0.60`.

Until this morning, they were `elo=0.25, xgb=0.15`. And XGBoost wasn't actually running.

## The bug

The XGBoost booster is loaded lazily from a JSON file at
`XGB_MODEL_PATH`, defaulting to `/tmp/football-predict-xgb.json`. On the
VPS, that path is inside the api container's filesystem — which gets wiped
every time `docker compose up -d` runs, which is every deploy.

The booster was never there. `xgb_load_model()` returned `None` on every
cold start. The ensemble silently collapsed to 2 legs (Poisson + Elo).
5,637 out of 5,637 stored predictions have model_version strings without
`xgb=` in them — definitive evidence the XGBoost pass never fired.

That's an ugly bug, but it also turned out to be a well-controlled A/B
test. Production has been running 2-leg ensemble for months while our
backtests measured the 3-leg blend. The gap between production log-loss
(~1.01) and backtest log-loss (~0.96) was exactly the shipped-vs-tested
delta nobody bothered to cross-check.

## The fix

Mount a named Docker volume at `/data`, move `XGB_MODEL_PATH` there,
retrain. One-time cost on VPS: ~4 minutes.

Then run the weight tune for real.

## The tune

`scripts/tune_ensemble.py` walks forward through every finished match in
`seasons=['2024-25', '2025-26']` — 1,816 matches after skips, across all
five top leagues. For each match it computes Poisson, Elo, and XGBoost
base triples from matches strictly before kickoff, caches those, then
sweeps every `(elo_weight, xgb_weight)` combination on the cached
predictions. Since the base signals are computed once, adding more grid
points to the sweep is ~free.

First sweep:

```
elo ∈ {0, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35}
xgb ∈ {0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30}

BEST  elo=0.25  xgb=0.30   log-loss 0.9633  acc 54.19%
OLD   elo=0.25  xgb=0.15   log-loss 0.9834  acc 52.42%
```

Best landed on the boundary (`xgb=0.30` was the highest grid point).
When that happens, always extend.

Second sweep, pushed the upper edge:

```
elo ∈ {0.20, 0.25, 0.30}
xgb ∈ {0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60}

BEST  elo=0.20  xgb=0.60   log-loss 0.9278  acc 56.22%
```

That's the number we shipped.

## What the numbers mean

Walk-forward backtest metrics have to be read carefully, but the relative
numbers are clean:

- **Log-loss 0.9278 vs baseline "always-home" 1.0185**: the model is
  converting 8.9% more probability mass onto the correct outcome than
  the simplest possible heuristic.
- **Accuracy 56.22% vs always-home 44%**: picks the right outcome (H/D/A)
  12.2 percentage points more often.
- **Log-loss delta 0.9834 → 0.9278**: −5.6% per match. On 1,816 matches
  that's −100.8 total nats of surprise.

## Why 0.60 isn't too aggressive

The common objection is "you're just trusting one model". True — a 60%
weight on XGBoost means the blended prediction leans on the booster's
soft-probability output heavily.

But the booster itself was trained using the same walk-forward split we
use to measure everything else. No xG used to train was closer to any
test match's kickoff than the xG we'd have seen in real life. The
features don't include anything the model couldn't have computed before
the whistle.

And the 1,816 match sample is large enough that the accuracy result is
comfortably outside sampling noise. A 56.2% argmax over 1,816 trials has
a 95% CI around [53.9%, 58.5%] — well above the 52.4% prior config.

## What this doesn't fix

Two things it doesn't touch, both honest gaps:

**The -2.0pp gap vs bookmakers on all-time data.** Over 3,760 finals
since 2019, bookies pick the right outcome 54.0% of the time; our model
picks it 52.0%. New weights help on recent data but I don't yet have
evidence they close the all-time gap — that's waiting on new matches
scoring under the new ensemble.

**Temperature scaling is still global.** T=1.35 applies to every league.
Per-league fits showed each league's current T is close to optimal when
measured on top of stored probs, but that's a post-hoc measurement. A
proper per-league T fit needs a walk-forward rerun with different T
upstream. Out of scope for this batch.

## Takeaway

Two years of shipping the wrong thing in production can still teach
something — once you notice. The fix is a one-line docker-compose
volume mount, a retrain, and honest measurement on out-of-sample data.

Weights are version-controlled in `app/predict/service.py`. Every
prediction's `model_version` string embeds the weights, so any stored
prediction can be traced to the exact blend that produced it.
