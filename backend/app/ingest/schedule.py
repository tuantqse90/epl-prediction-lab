"""Pure translation of an Understat schedule DataFrame into DB row DTOs.

Kept separate from the asyncpg upsert so the logic stays unit-testable without
standing up a Postgres instance. The upsert side is glue (one `INSERT ... ON
CONFLICT` per table) and verified by running the ingest CLI against a real DB.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class TeamRow:
    slug: str
    name: str
    short_name: str


@dataclass(frozen=True)
class MatchRow:
    external_id: str
    season: str
    kickoff_time: pd.Timestamp
    home_slug: str
    away_slug: str
    home_goals: int | None
    away_goals: int | None
    home_xg: float | None
    away_xg: float | None
    status: str


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s


def _short(name: str) -> str:
    """Three-letter-ish abbreviation fallback when source lacks team_code."""
    words = [w for w in re.split(r"\s+", name) if w]
    if len(words) == 1:
        return words[0][:3].upper()
    return "".join(w[0] for w in words[:3]).upper()


def schedule_to_rows(df: pd.DataFrame, season: str) -> tuple[list[TeamRow], list[MatchRow]]:
    """Split an Understat schedule into (unique team rows, match rows)."""
    names = pd.unique(pd.concat([df["home_team"], df["away_team"]]))
    teams = [TeamRow(slug=slugify(n), name=n, short_name=_short(n)) for n in sorted(names)]

    matches: list[MatchRow] = []
    for row in df.itertuples(index=False):
        is_final = bool(getattr(row, "is_result"))
        matches.append(
            MatchRow(
                external_id=str(row.game_id),
                season=season,
                kickoff_time=row.date,
                home_slug=slugify(row.home_team),
                away_slug=slugify(row.away_team),
                home_goals=int(row.home_goals) if pd.notna(row.home_goals) else None,
                away_goals=int(row.away_goals) if pd.notna(row.away_goals) else None,
                home_xg=float(row.home_xg) if pd.notna(row.home_xg) else None,
                away_xg=float(row.away_xg) if pd.notna(row.away_xg) else None,
                status="final" if is_final else "scheduled",
            )
        )
    return teams, matches
