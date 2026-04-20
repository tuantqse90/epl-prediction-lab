"""Lineup-sum attack multiplier.

Pre-kickoff (typically T-60min when line-ups lock), we know exactly who's
on the pitch. At that moment the team-level rolling xG average loses to
a lineup-specific aggregate: you can't score with a striker who's on the
bench, and conversely a world-class sub coming back from injury should
lift λ the moment their name hits the team sheet.

We compute `lineup_xg = Σ (player_xg / player_games)` for the starting XI,
plus a damped contribution from the bench (typical subs play ~20 minutes),
then divide by the team's historical average xG-per-match to get a
multiplicative λ adjustment — clamped so a single outlier lineup can't
more than 30% move the prediction.
"""
from __future__ import annotations


# Bench players contribute at ~22 minutes / 90 = 0.24 of full impact.
BENCH_WEIGHT = 0.24

# Safety band on the lineup multiplier. Bigger swings become plausible
# only when the model has seen much more lineup history per player.
MULTIPLIER_MIN = 0.70
MULTIPLIER_MAX = 1.30


def _xg_per_game(stats: dict) -> float:
    xg = stats.get("xg") or 0.0
    games = stats.get("games") or 0
    if games <= 0:
        return 0.0
    return float(xg) / float(games)


def lineup_xg_rating(
    *,
    starters: list[str],
    bench: list[str],
    stats_by_name: dict[str, dict],
) -> float:
    """Aggregate lineup attack potential as xG per match.

    Starters count at 1.0 (expected 90 minutes). Bench count at BENCH_WEIGHT
    (~22 minutes typical). Players missing from `stats_by_name` silently
    contribute 0 — new signings / youth promotions without a season row.
    """
    total = 0.0
    for p in starters:
        stats = stats_by_name.get(p)
        if stats is None:
            continue
        total += _xg_per_game(stats)
    for p in bench:
        stats = stats_by_name.get(p)
        if stats is None:
            continue
        total += _xg_per_game(stats) * BENCH_WEIGHT
    return total


def lineup_multiplier(lineup_xg, team_avg_xg: float) -> float:
    """Ratio of lineup-sum xG to the team's historical avg xG-per-match.

    Returns 1.0 (no-op) on missing data. Clamped to [MULTIPLIER_MIN, MAX] so
    a single lopsided lineup can't more than ±30% move λ."""
    if lineup_xg is None:
        return 1.0
    if team_avg_xg is None or team_avg_xg <= 0:
        return 1.0
    raw = float(lineup_xg) / float(team_avg_xg)
    return max(MULTIPLIER_MIN, min(MULTIPLIER_MAX, raw))
