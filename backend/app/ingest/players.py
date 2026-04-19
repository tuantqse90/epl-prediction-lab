"""Understat player-season stats → `player_season_stats` rows.

Pure translator is tested; the upsert side is glue.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import asyncpg
import pandas as pd


@dataclass(frozen=True)
class PlayerRow:
    player_name: str
    team_name: str
    season: str
    games: int
    goals: int
    assists: int
    xg: float
    xa: float
    npxg: float
    key_passes: int
    position: str | None


def _f(v) -> float | None:
    return None if pd.isna(v) else float(v)


def _i(v) -> int | None:
    return None if pd.isna(v) else int(v)


def player_stats_to_rows(df: pd.DataFrame, season: str) -> list[PlayerRow]:
    """Flatten Understat's (league, season, team, player) MultiIndex into DTOs."""
    wide = df.reset_index()
    out: list[PlayerRow] = []
    for row in wide.itertuples(index=False):
        out.append(
            PlayerRow(
                player_name=row.player,
                team_name=row.team,
                season=season,
                games=_i(row.matches) or 0,
                goals=_i(row.goals) or 0,
                assists=_i(row.assists) or 0,
                xg=_f(row.xg) or 0.0,
                xa=_f(row.xa) or 0.0,
                npxg=_f(getattr(row, "np_xg", row.np_goals)) or 0.0,
                key_passes=_i(row.key_passes) or 0,
                position=(None if pd.isna(row.position) else str(row.position)),
            )
        )
    return out


async def upsert_player_stats(
    pool: asyncpg.Pool,
    season: str,
    rows: Iterable[PlayerRow],
) -> int:
    """Delete+insert per season — BUT only for teams represented in `rows`.

    Prior version wiped every season row before re-inserting, which meant
    re-running for league B after league A destroyed league A's data. We
    now scope the delete to the team names touched by this ingest so each
    league keeps the others intact.
    """
    rows = list(rows)
    team_names = sorted({r.team_name for r in rows})
    async with pool.acquire() as conn:
        async with conn.transaction():
            if team_names:
                await conn.execute(
                    """
                    DELETE FROM player_season_stats
                    WHERE season = $1
                      AND team_id IN (SELECT id FROM teams WHERE name = ANY($2::text[]))
                    """,
                    season, team_names,
                )
            inserted = 0
            for r in rows:
                team_id = await conn.fetchval(
                    "SELECT id FROM teams WHERE name = $1", r.team_name
                )
                if team_id is None:
                    continue
                await conn.execute(
                    """
                    INSERT INTO player_season_stats (
                        player_name, team_id, season, games, goals, assists,
                        xg, xa, npxg, key_passes, position
                    )
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                    """,
                    r.player_name, team_id, r.season,
                    r.games, r.goals, r.assists,
                    r.xg, r.xa, r.npxg,
                    r.key_passes, r.position,
                )
                inserted += 1
    return inserted
