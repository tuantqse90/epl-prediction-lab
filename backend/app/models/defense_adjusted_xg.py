"""Scale player xG by opponent defense quality.

A striker averaging 0.5 xG/match against an elite defense is more
valuable than 0.5 xG/match against a porous one. Divide by the opponent's
defense coefficient (normalized to league average = 1.0). Clamp to a
[0.5, 2.0] band so extreme defensive stats don't produce absurd
projections.
"""

from __future__ import annotations


MIN_DEF = 0.5
MAX_DEF = 2.0


def adjusted_xg(*, raw_xg: float, opp_defense_coef: float) -> float:
    coef = max(MIN_DEF, min(MAX_DEF, opp_defense_coef))
    return raw_xg / coef


def schedule_adjusted_xg_sum(
    *, xg_per_match: float, opponent_defense_coefs: list[float],
) -> float:
    return sum(
        adjusted_xg(raw_xg=xg_per_match, opp_defense_coef=c)
        for c in opponent_defense_coefs
    )
