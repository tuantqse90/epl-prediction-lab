"""Top-scorer race — project end-of-season goals.

Cheapest-possible model: assume xG/match rate holds for remaining games,
and the player plays in every one of those fixtures. That's naive (subs,
injuries, tactics) but surfaces a directional "who's most likely to win
the Golden Boot" that we can back-test when the season ends.

No Monte Carlo here — the linear projection is the median outcome and
variance would be huge anyway (players score 0 or 1 per match, not their
xG). Display only; don't use for betting.
"""

from __future__ import annotations


def project_end_of_season(
    *,
    current_goals: int,
    xg_per_match: float,
    team_remaining: int,
) -> float:
    """current + xg_per_match * remaining, floored at current_goals.

    Negative xG/match is impossible but we clamp to 0 just in case.
    """
    if team_remaining <= 0:
        return float(current_goals)
    rate = max(0.0, xg_per_match)
    return float(current_goals) + rate * team_remaining


def rank_scorer_race(rows: list[dict]) -> list[dict]:
    """Given rows each having {player, goals, xg, games, team_remaining},
    return sorted list with `projected` + `gap_to_leader`.

    Sort key: projected desc, goals desc, xg desc.
    """
    enriched = []
    for r in rows:
        xgm = float(r["xg"]) / r["games"] if r["games"] > 0 else 0.0
        proj = project_end_of_season(
            current_goals=r["goals"],
            xg_per_match=xgm,
            team_remaining=r["team_remaining"],
        )
        enriched.append({**r, "xg_per_match": xgm, "projected": proj})
    enriched.sort(key=lambda x: (-x["projected"], -x["goals"], -x["xg"]))
    leader_proj = enriched[0]["projected"] if enriched else 0.0
    for r in enriched:
        r["gap_to_leader"] = r["projected"] - leader_proj
    return enriched
