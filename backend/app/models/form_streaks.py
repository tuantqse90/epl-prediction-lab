"""Form streak + xG-vs-actual regression flag.

A team that has scored > xG for 5 matches running is due for regression
(goals are lower-variance than xG short-term). Surfaces as "hot" or
"cold" flag on the team page.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StreakFlag:
    label: str                # "hot-finishing", "cold-finishing", "neutral"
    xg_delta: float           # recent goals - recent xG
    n_matches: int


def classify_streak(
    *, last_n_goals: list[int], last_n_xg: list[float],
) -> StreakFlag:
    n = min(len(last_n_goals), len(last_n_xg))
    if n == 0:
        return StreakFlag(label="neutral", xg_delta=0.0, n_matches=0)
    delta = sum(last_n_goals[:n]) - sum(last_n_xg[:n])
    if delta > 2.0 and n >= 5:
        return StreakFlag(label="hot-finishing", xg_delta=delta, n_matches=n)
    if delta < -2.0 and n >= 5:
        return StreakFlag(label="cold-finishing", xg_delta=delta, n_matches=n)
    return StreakFlag(label="neutral", xg_delta=delta, n_matches=n)
