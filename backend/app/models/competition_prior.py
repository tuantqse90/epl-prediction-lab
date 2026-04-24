"""League-vs-cup prior adjustment.

Cup fixtures (FA Cup, Copa del Rey, DFB-Pokal, Coupe de France) have
different incentives from league matches:
  * Top teams rotate heavily in early rounds → attack strength weaker.
  * Underdogs raise their ceiling for a one-off → defense strength of
    the favourite gets less respect.
  * Draws are less likely once extra time / penalties enter the picture
    (but our model predicts 90-min result, so ρ nudges toward neutral).

We encode this as a per-competition blend of the team's normal strength
with a "league-average" neutral coefficient of 1.0. The blend weight
favourite_reduction=0.20 means a team with attack=1.3 in a cup match
gets attack=0.2×1.0 + 0.8×1.3 = 1.24 — softer edge.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompetitionPrior:
    favourite_reduction: float   # 0.0 = no blend, 1.0 = flat league-average
    rho_shift: float             # additive shift to Dixon-Coles ρ


_COMP_PRIORS: dict[str, CompetitionPrior] = {
    "league": CompetitionPrior(favourite_reduction=0.0, rho_shift=0.0),
    "cup":    CompetitionPrior(favourite_reduction=0.20, rho_shift=+0.05),
    "europe": CompetitionPrior(favourite_reduction=0.10, rho_shift=0.0),
}


def prior_for(competition_type: str | None) -> CompetitionPrior:
    return _COMP_PRIORS.get(competition_type or "league", _COMP_PRIORS["league"])


def blend_coef(coef: float, reduction: float) -> float:
    """Pull a strength coefficient toward 1.0 (league average) by
    `reduction` ∈ [0, 1]."""
    return (1.0 - reduction) * coef + reduction * 1.0
