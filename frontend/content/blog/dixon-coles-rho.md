---
slug: dixon-coles-rho
title: Dixon-Coles ρ = −0.15, and why the low-score cells need a correction
date: 2026-04-15
excerpt: Independence is a lie. Small adjustments to the four low-score cells (0-0, 1-0, 0-1, 1-1) buy measurable log-loss. Here's the empirical case.
tags: [model, poisson, math]
---

Independent Poisson on `λ_home, λ_away` makes an uncomfortable assumption:
the home and away goal counts are independent. That's false in the tails
near 0–0. Real matches have a slight tendency toward tight draws that
pure independence underprices, and a slight over-count of 1–0 and 0–1
that it overprices.

Dixon and Coles (1997) proposed fixing this by multiplying the four
low-score cells by a correction factor τ parameterized by ρ:

```
τ(0,0) = 1 - λ_h·λ_a·ρ
τ(1,0) = 1 + λ_a·ρ
τ(0,1) = 1 + λ_h·ρ
τ(1,1) = 1 - ρ
τ(i,j) = 1          otherwise
```

Every other cell (2+ goals by either side) stays independent. ρ shifts
probability mass around among the four low-score cells only. The whole
matrix is renormalized after.

## Why ρ < 0 instead of ρ > 0

Fit on real finals, ρ consistently lands in the negative range. On our
multi-league data spanning 2019–2025, the MLE converges near **ρ = −0.15**.

Negative ρ means:

- τ(0,0) = 1 − λ_h·λ_a·(−0.15) = **up** (more 0–0 than independence says)
- τ(1,0), τ(0,1) = 1 + λ·(−0.15) = **down** (fewer 1–0, 0–1)
- τ(1,1) = 1 − (−0.15) = **up** (more 1–1)

Draws-at-zero-and-one get a small lift; one-goal wins get a small cut.
That matches the empirical draw rate: leagues average around 24–27% draws,
which is notably higher than independent Poisson predicts for typical
λ values (often 22–24%).

## The delta on log-loss

We ran `scripts/grid_search.py` across ρ ∈ {−0.20, −0.15, −0.10, −0.05, 0}
on EPL 2023-24:

```
ρ        log-loss   draw-rate-predicted   draw-rate-actual
-----    --------   -------------------   ----------------
 0.00    0.9921          22.8%                 26.1%
-0.05    0.9887          23.7%                 26.1%
-0.10    0.9862          24.6%                 26.1%
-0.15    0.9848          25.5%                 26.1%
-0.20    0.9852          26.3%                 26.1%
```

The minimum sits near −0.15, matching simulation literature. At ρ=0
we're under-predicting draws by ~3pp and losing 0.0073 log-loss per
match to that alone. On 380 EPL matches that's 2.8 nats of surprise we
didn't need to eat.

## What ρ doesn't do

It doesn't fix high-scoring correlation. If λ_h·λ_a = 9, the correction
factor for (3,3) is 1.0 by definition — still independent. The DC paper
notes this explicitly; they considered extending the correction but the
empirical evidence didn't support it on their data.

It also doesn't fix systematic miscalibration. ρ shifts mass among 4
specific cells. If your λ estimates are biased (say, because you're
using raw xG instead of opponent-adjusted xG), ρ won't save you — you'll
just rebalance the same bad prediction.

## Why this matters for betting odds

Bookmakers price draw odds with the actual draw rate baked in. A naive
independent-Poisson model will consistently under-price draws relative
to market, giving a false "edge" signal on every draw bet. Every time
the market offers you 3.50 on a draw and your 22% draw probability says
the fair price is 4.50, you're about to donate to whoever takes the
other side.

DC correction closes that specific blind spot. Combined with temperature
scaling on the 3-way probabilities (T=1.35 on our data), the result is
probability estimates that track calibration on both 1X2 argmax and
bookmaker-price comparison.

## Where this lives in the code

- `app/models/poisson.py:apply_dixon_coles` — the tau function
- `app/models/poisson.py:predict_match` — call site, takes rho as a param
- `app/core/config.py:default_rho` — shipped value (−0.15)
- `scripts/grid_search.py` — rerun the fit on any season/league
- `scripts/calibrate_rho.py` — dedicated MLE for just ρ (faster than full
  grid search when you only want to verify)

The rho stays a hyperparameter rather than getting fit per prediction,
which means it's one number to audit for the entire production model.
Verifying ρ=−0.15 is reasonable for your data is a matter of running
one script.
