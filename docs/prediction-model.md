# Prediction Model (Poisson + Dixon-Coles)

## Why Poisson?

- Football goals follow a Poisson distribution (well-established literature)
- Input: team **expected goals (xG)** — less noisy than actual goals
- Output: probability of each possible scoreline → collapses to P(H) / P(D) / P(A)

## Why Dixon-Coles adjustment?

- Raw Poisson **underestimates** low-score games: 0-0, 1-1, 1-0, 0-1
- Dixon-Coles adds a correction factor for those specific scorelines
- Well-documented, simple to implement

## Feature Pipeline

```python
def compute_team_strength(team_id, season, last_n=10):
    """Return (attack_strength, defense_strength) normalized to league avg."""
    # Pull last N matches
    # Weighted avg of xG for/against (more weight to recent)
    # Adjust for opponent quality (Elo)
    # Return normalized values
    ...

def predict_match(home_team_id, away_team_id, season):
    home_att, home_def = compute_team_strength(home_team_id, season)
    away_att, away_def = compute_team_strength(away_team_id, season)

    # Home advantage factor (~1.3 historically for EPL)
    HOME_ADV = 1.3

    # Expected goals
    lambda_home = home_att * away_def * HOME_ADV
    lambda_away = away_att * home_def

    # Build scoreline probability matrix (0-0 to 5-5)
    # Apply Dixon-Coles adjustment for low-score cells
    # Collapse to P(H win), P(draw), P(A win) + top scorelines
    ...
```

## Outputs per match

- `p_home_win`, `p_draw`, `p_away_win` (sum to 1.0)
- `expected_home_goals`, `expected_away_goals`
- `top_scorelines`: top-5 most likely exact scores with probabilities
- `confidence`: derived from entropy of the scoreline distribution
