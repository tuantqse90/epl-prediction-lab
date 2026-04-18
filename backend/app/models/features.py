"""Team-strength feature pipeline.

Turns a schedule DataFrame (Understat shape) into per-team attack/defense
strengths normalized to the league average xG, then combines them into the
(lambda_home, lambda_away) rates consumed by the Poisson engine.

Strengths are computed strictly from matches with `date < as_of` and
`is_result == True` — no future leakage.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class TeamStrength:
    attack: float    # avg xG scored / league avg xG per team per match
    defense: float   # avg xG conceded / league avg — LOWER is a better defense


def compute_team_strengths(
    schedule: pd.DataFrame,
    as_of: pd.Timestamp,
    last_n: int | None = None,
) -> dict[str, TeamStrength]:
    """Return {team_name: TeamStrength} using only matches strictly before `as_of`.

    `last_n` optionally limits to the most recent N matches per team.
    """
    done = schedule.loc[(schedule["date"] < as_of) & schedule["is_result"].astype(bool)]
    if done.empty:
        return {}

    home = done[["date", "home_team", "away_team", "home_xg", "away_xg"]].rename(
        columns={"home_team": "team", "away_team": "opp", "home_xg": "xg_for", "away_xg": "xg_against"}
    )
    away = done[["date", "away_team", "home_team", "away_xg", "home_xg"]].rename(
        columns={"away_team": "team", "home_team": "opp", "away_xg": "xg_for", "home_xg": "xg_against"}
    )
    team_matches = pd.concat([home, away], ignore_index=True).sort_values("date")

    if last_n is not None:
        team_matches = team_matches.groupby("team").tail(last_n)

    league_avg = team_matches[["xg_for", "xg_against"]].stack().mean()

    strengths: dict[str, TeamStrength] = {}
    for team, grp in team_matches.groupby("team"):
        attack = grp["xg_for"].mean() / league_avg
        defense = grp["xg_against"].mean() / league_avg
        strengths[team] = TeamStrength(attack=float(attack), defense=float(defense))
    return strengths


def match_lambdas(
    home: TeamStrength,
    away: TeamStrength,
    league_avg_goals: float,
    home_adv: float = 1.3,
) -> tuple[float, float]:
    """Return (lambda_home, lambda_away) — expected goals for each side."""
    lam_h = league_avg_goals * home.attack * away.defense * home_adv
    lam_a = league_avg_goals * away.attack * home.defense
    return lam_h, lam_a
