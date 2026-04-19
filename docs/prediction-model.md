# Prediction Model (Ensemble: Poisson + Dixon-Coles + Elo + XGBoost)

> The engine is a weighted blend of three legs, not a single Poisson. Each leg produces an independent `(p_H, p_D, p_A)` triplet; the ensemble weights them, then applies injury + weather shrinks to the goal rates before the final scoreline matrix is rebuilt.

## Why ensemble?

Each leg catches a different signal:

- **Poisson + Dixon-Coles** — xG-based scoring rate, correct on low-score skew
- **Elo** — rating-level form, robust when xG is noisy (early season, promoted teams)
- **XGBoost** — nonlinear interactions across rest days, derby flag, strength differentials that the other two legs can't model

Walk-forward backtest on 2,263 matches across 7 seasons:

- Composite ensemble: **52.3% 1X2 accuracy · log-loss ≈ 1.02**
- Poisson alone: **~50%**
- Always-home baseline: **41.8%**
- Bookmaker closing price baseline: **~55%** (the ceiling)

## Leg 1 — Poisson + Dixon-Coles

```python
def compute_team_strength(team_id, season, last_n=10):
    """Return (attack_strength, defense_strength) normalised to league avg.
    Pulls last-N matches, takes opponent-adjusted xG-for and xG-against, weights
    recent matches higher (exponential decay, half-life ≈ 5 matches)."""

def match_lambdas(home_id, away_id, season):
    home_att, home_def = compute_team_strength(home_id, season)
    away_att, away_def = compute_team_strength(away_id, season)
    HOME_ADV = 1.3
    lambda_home = home_att * away_def * HOME_ADV
    lambda_away = away_att * home_def
    return lambda_home, lambda_away
```

The 6×6 scoreline matrix is built from independent Poisson PMFs, then scaled by the **Dixon-Coles ρ correction** for the four low-score cells `(0,0) (0,1) (1,0) (1,1)`. ρ is calibrated at **−0.10** per walk-forward tuning (not the textbook 0.1 which under-corrects for modern EPL).

See: `backend/app/models/poisson.py`, `backend/app/models/features.py`.

## Leg 2 — Elo

Classic Elo with:

- Rating update `K = 32` (doubled to 64 for derby / cup weight matches)
- Home-field constant: **+65 Elo** to home side's effective rating
- Decay to league mean at season end (20% regression)

`elo_to_3way(home_elo, away_elo)` returns a 1X2 triplet via a logistic mapping that's tuned (on the same 7 seasons) to match empirical win rates at each rating delta bucket.

See: `backend/app/models/elo.py`.

## Leg 3 — XGBoost

21 engineered features per match:

- Attack/defence strengths (both teams)
- Elo-rating delta
- Rest days (both teams)
- Derby flag, cup flag
- Venue strength differential
- Form strings (last-5 points)
- League_code one-hot (so one model serves all 5 leagues)

Output: 3-way softmax probabilities.

Model file: `/tmp/football-predict-xgb.json`. If absent at boot, the ensemble **silently skips** the XGB leg and re-normalises the other two weights — never crashes on a missing model.

See: `backend/app/models/xgb_model.py`.

## Ensemble weights

In `backend/app/predict/service.py`:

```python
FINAL = 0.20 * P_poisson + 0.20 * P_elo + 0.60 * P_xgb
```

Weights tuned via grid search against held-out 2024-25 season log-loss. XGB dominates because it effectively absorbs the other two as features (Elo + strength ratings are in its training set), but keeping the other two as independent legs protects against XGB overfitting on a niche league.

## λ adjustments (applied before scoreline matrix rebuild)

After the ensemble produces a provisional `(λ_home, λ_away)`, two context multipliers shrink them.

### Injury adjustment

```python
INJURY_ALPHA = 0.6  # max shrink per team capped at 0.5 total

def injury_factor(team_slug, kickoff):
    hurt = _sum_xg_share_of_listed_injuries(team_slug, kickoff)  # 0..1
    return max(0.5, 1.0 - INJURY_ALPHA * hurt)

lambda_home *= injury_factor(home_slug, kickoff)
lambda_away *= injury_factor(away_slug, kickoff)
```

Data: `player_injuries` joined with `player_season_stats` for xG share. Only considers injuries marked `Out` or `Doubtful` as of kickoff.

### Weather adjustment

```python
def weather_multiplier(weather_row):
    if weather_row is None: return 1.0
    m = 1.0
    if weather_row.wind_kmh  >= 30: m *= 0.92
    if weather_row.precip_mm >= 2:  m *= 0.95
    return m

lambda_home *= w; lambda_away *= w  # same multiplier both sides
```

Data: `match_weather` table, populated by `scripts/ingest_weather.py` at T-2h.

## Confidence intervals

`backend/app/models/ci.py` — bootstrap 30 resamples of the input strength estimates, re-predicts each sample, returns 16 / 84 percentile bands for `(p_H, p_D, p_A, λ_home, λ_away)`.

Used on `/match/[id]` to show the CI chip under each probability.

## Halftime + markets

- `app/models/half_time.py` — separate 45-minute λ estimate for live HT probabilities
- `app/models/markets.py` — over/under total-goals probabilities derived from the final scoreline matrix; being extended in **Phase 6** ([`plan-new.md`](../plan-new.md)) to cover BTTS, Asian handicap, same-game parlay

## Outputs per match

- `p_home_win`, `p_draw`, `p_away_win` (sum to 1.0)
- `expected_home_goals`, `expected_away_goals` (post-adjustment)
- `top_scorelines`: top-5 exact scores with probabilities
- `confidence`: `1 − H(p)/log(3)` where `H` is Shannon entropy
- `commitment_hash`: SHA-256 of the canonical-JSON body (for public recompute)

## Calibration

Quarterly check via `scripts/backtest.py`. Current state (2026-04-19):

- **50–60% bin**: model under-confident by ≈3pp (implies temperature scaling could be loosened from current T=1.35 → T≈1.25)
- **60–70% bin**: under-confident by ≈4pp
- **33–50% bin**: nearly perfect
- **70%+ bin**: sparse, noisy, not actionable

Decision rule hedges (floor the draw at X%, skew argmax above Y%, etc.) were simulated in detail against the 2024-25 + 2025-26 seasons and **none beat raw argmax** — the ensemble is already well-calibrated enough that a rule-based override subtracts signal. See `PROGRESS.md` 2026-04-19 entries.
