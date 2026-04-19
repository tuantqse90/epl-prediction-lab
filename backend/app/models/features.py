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
    attack: float                         # overall attack coefficient (all venues)
    defense: float                        # overall defense coefficient (LOWER is better)
    attack_home: float | None = None      # None → fall back to overall in match_lambdas
    defense_home: float | None = None
    attack_away: float | None = None
    defense_away: float | None = None

    def home_attack(self) -> float:
        return self.attack_home if self.attack_home is not None else self.attack

    def home_defense(self) -> float:
        return self.defense_home if self.defense_home is not None else self.defense

    def away_attack(self) -> float:
        return self.attack_away if self.attack_away is not None else self.attack

    def away_defense(self) -> float:
        return self.defense_away if self.defense_away is not None else self.defense


def compute_team_strengths(
    schedule: pd.DataFrame,
    as_of: pd.Timestamp,
    last_n: int | None = None,
    decay: float = 0.9,
    opponent_adjust: bool = False,
) -> dict[str, TeamStrength]:
    """Return {team_name: TeamStrength} using only matches strictly before `as_of`.

    Pipeline:
      1. `last_n` caps history per team to the most recent N matches.
      2. `decay` gives exponential weight by recency (decay=1 → uniform).
      3. `opponent_adjust` divides each match's xG_for by the opponent's raw
         defense coefficient (and xG_against by opponent's attack) before
         averaging — so xG piled against a weak defense counts less than
         xG earned against a strong one. Implemented as a two-pass: we
         compute raw strengths first, then redo the aggregation with the
         per-match opponent multiplier applied.
    """
    done = schedule.loc[(schedule["date"] < as_of) & schedule["is_result"].astype(bool)]
    if done.empty:
        return {}

    home = done[["date", "home_team", "away_team", "home_xg", "away_xg"]].rename(
        columns={"home_team": "team", "away_team": "opp", "home_xg": "xg_for", "away_xg": "xg_against"}
    )
    home["venue"] = "home"
    away = done[["date", "away_team", "home_team", "away_xg", "home_xg"]].rename(
        columns={"away_team": "team", "home_team": "opp", "away_xg": "xg_for", "home_xg": "xg_against"}
    )
    away["venue"] = "away"
    team_matches = pd.concat([home, away], ignore_index=True).sort_values("date")

    if last_n is not None:
        team_matches = team_matches.groupby("team").tail(last_n)

    # League-average still uses unweighted mean so the normalization scale
    # is stable; decay only reshapes each team's own profile.
    league_avg = team_matches[["xg_for", "xg_against"]].stack().mean()

    def _weighted(sub: pd.DataFrame, col: str) -> float | None:
        if sub.empty:
            return None
        n = len(sub)
        if decay == 1.0 or n <= 1:
            return float(sub[col].mean() / league_avg)
        ordered = sub.sort_values("date", ascending=False).reset_index(drop=True)
        weights = pd.Series([decay ** i for i in range(n)])
        return float((ordered[col] * weights).sum() / weights.sum() / league_avg)

    def _build(matches: pd.DataFrame) -> dict[str, TeamStrength]:
        out: dict[str, TeamStrength] = {}
        for team, grp in matches.groupby("team"):
            home_rows = grp[grp["venue"] == "home"]
            away_rows = grp[grp["venue"] == "away"]
            out[team] = TeamStrength(
                attack=_weighted(grp, "xg_for") or 1.0,
                defense=_weighted(grp, "xg_against") or 1.0,
                attack_home=_weighted(home_rows, "xg_for"),
                defense_home=_weighted(home_rows, "xg_against"),
                attack_away=_weighted(away_rows, "xg_for"),
                defense_away=_weighted(away_rows, "xg_against"),
            )
        return out

    raw = _build(team_matches)
    if not opponent_adjust:
        return raw

    # Second pass: rescale each row's xG by the opponent's raw coefficient,
    # then rebuild. Guard against zero-coefficient div by clipping to a
    # sane band — defense of 0.5 means 'half as porous as average', not
    # 'impossible to score on'.
    adjusted = team_matches.copy()
    opp_def = adjusted["opp"].map(lambda t: (raw.get(t).defense if t in raw else 1.0))
    opp_att = adjusted["opp"].map(lambda t: (raw.get(t).attack  if t in raw else 1.0))
    adjusted["xg_for"]    = adjusted["xg_for"]    / opp_def.clip(lower=0.3, upper=2.5)
    adjusted["xg_against"] = adjusted["xg_against"] / opp_att.clip(lower=0.3, upper=2.5)
    return _build(adjusted)


def match_lambdas(
    home: TeamStrength,
    away: TeamStrength,
    league_avg_goals: float,
    home_adv: float = 1.3,
    venue_blend: float = 0.6,
) -> tuple[float, float]:
    """Return (lambda_home, lambda_away) — expected goals for each side.

    Uses a convex blend of venue-specific and overall strengths so that
    teams with short home/away sample get a graceful fallback. At
    `venue_blend=0` we recover the original overall-only formula; at 1.0
    we rely entirely on the venue-specific coefficients.
    """
    def blend(overall: float, venue: float | None) -> float:
        if venue is None:
            return overall
        return (1.0 - venue_blend) * overall + venue_blend * venue

    home_att = blend(home.attack, home.attack_home)
    home_def = blend(home.defense, home.defense_home)
    away_att = blend(away.attack, away.attack_away)
    away_def = blend(away.defense, away.defense_away)

    lam_h = league_avg_goals * home_att * away_def * home_adv
    lam_a = league_avg_goals * away_att * home_def
    return lam_h, lam_a
