"""Pull RAG context for the chat Q&A layer — last-5 summaries, H2H, scorers."""

from __future__ import annotations

from datetime import datetime

import asyncpg

from app import queries


async def _recent_match_summaries(
    pool: asyncpg.Pool,
    team_name: str,
    before: datetime,
    n: int = 5,
) -> str:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT ht.name AS home, at.name AS away, m.home_goals, m.away_goals
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.status = 'final' AND m.kickoff_time < $2
              AND (ht.name = $1 OR at.name = $1)
              AND m.home_goals IS NOT NULL AND m.away_goals IS NOT NULL
            ORDER BY m.kickoff_time DESC
            LIMIT $3
            """,
            team_name, before, n,
        )
    if not rows:
        return "(chưa có trận nào trong DB)"
    return "; ".join(
        f"{r['home']} {r['home_goals']}-{r['away_goals']} {r['away']}" for r in rows
    )


async def _h2h_summaries(
    pool: asyncpg.Pool,
    home: str,
    away: str,
    before: datetime,
    n: int = 3,
) -> str:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT ht.name AS home, at.name AS away, m.home_goals, m.away_goals
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.status = 'final' AND m.kickoff_time < $3
              AND m.home_goals IS NOT NULL AND m.away_goals IS NOT NULL
              AND ((ht.name = $1 AND at.name = $2) OR (ht.name = $2 AND at.name = $1))
            ORDER BY m.kickoff_time DESC
            LIMIT $4
            """,
            home, away, before, n,
        )
    if not rows:
        return "(không có H2H trong DB)"
    return "; ".join(
        f"{r['home']} {r['home_goals']}-{r['away_goals']} {r['away']}" for r in rows
    )


async def _top_scorers(pool: asyncpg.Pool, team_name: str) -> str:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT p.player_name, p.goals
            FROM player_season_stats p
            JOIN teams t ON t.id = p.team_id
            WHERE t.name = $1
            ORDER BY p.goals DESC NULLS LAST
            LIMIT 3
            """,
            team_name,
        )
    if not rows:
        return "(player stats chưa được ingest)"
    return ", ".join(f"{r['player_name']} {r['goals']}g" for r in rows)


async def build_chat_context(pool: asyncpg.Pool, match_id: int) -> dict:
    m = await queries.get_match(pool, match_id)
    if m is None:
        raise ValueError(f"match {match_id} not found")

    kickoff: datetime = m["kickoff_time"]
    home, away = m["home_name"], m["away_name"]

    return dict(
        home_team=home,
        away_team=away,
        kickoff=kickoff.strftime("%Y-%m-%d %H:%M UTC"),
        p_home_win=float(m["p_home_win"] or 0),
        p_draw=float(m["p_draw"] or 0),
        p_away_win=float(m["p_away_win"] or 0),
        model_reasoning=m["reasoning"] or "",
        home_recent=await _recent_match_summaries(pool, home, kickoff),
        away_recent=await _recent_match_summaries(pool, away, kickoff),
        h2h=await _h2h_summaries(pool, home, away, kickoff),
        top_scorers_home=await _top_scorers(pool, home),
        top_scorers_away=await _top_scorers(pool, away),
    )
