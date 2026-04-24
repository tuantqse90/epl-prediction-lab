"""GET /api/stats/accuracy-by-team — model hit rate per team.

For every team that has ≥ N final predictions in the sample, compute:
- scored
- correct (model's argmax matched actual)
- accuracy
- mean_log_loss
"""

from __future__ import annotations

import math

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel


router = APIRouter(prefix="/api/stats", tags=["stats"])


class TeamAccuracy(BaseModel):
    slug: str
    short_name: str
    name: str
    league_code: str | None
    scored: int
    correct: int
    accuracy: float
    mean_log_loss: float


class AccuracyByTeamResponse(BaseModel):
    season: str | None
    min_sample: int
    teams: list[TeamAccuracy]


@router.get("/accuracy-by-team", response_model=AccuracyByTeamResponse)
async def accuracy_by_team(
    request: Request,
    season: str | None = Query(None),
    min_sample: int = Query(5, ge=1, le=50),
    league: str | None = Query(None),
) -> AccuracyByTeamResponse:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH latest AS (
                SELECT DISTINCT ON (p.match_id)
                  p.match_id, p.p_home_win, p.p_draw, p.p_away_win
                FROM predictions p
                ORDER BY p.match_id, p.created_at DESC
            ),
            graded AS (
                SELECT m.id, m.league_code, m.home_goals, m.away_goals,
                       m.home_team_id, m.away_team_id,
                       l.p_home_win, l.p_draw, l.p_away_win
                FROM matches m
                JOIN latest l ON l.match_id = m.id
                WHERE m.status = 'final'
                  AND m.home_goals IS NOT NULL
                  AND ($1::text IS NULL OR m.season = $1)
                  AND ($2::text IS NULL OR m.league_code = $2)
            ),
            per_team AS (
                -- Home rows
                SELECT home_team_id AS team_id, league_code,
                       p_home_win, p_draw, p_away_win,
                       home_goals, away_goals,
                       'H' AS side
                FROM graded
                UNION ALL
                SELECT away_team_id, league_code,
                       p_home_win, p_draw, p_away_win,
                       home_goals, away_goals,
                       'A'
                FROM graded
            )
            SELECT t.slug, t.name, t.short_name,
                   MAX(pt.league_code) AS league_code,
                   COUNT(*)::int AS scored,
                   COUNT(*) FILTER (
                     WHERE (p_home_win >= p_draw AND p_home_win >= p_away_win AND home_goals > away_goals)
                        OR (p_away_win >= p_home_win AND p_away_win >= p_draw AND home_goals < away_goals)
                        OR (p_draw >= p_home_win AND p_draw >= p_away_win AND home_goals = away_goals)
                   )::int AS correct,
                   -- Log-loss = -log(p_assigned_to_actual). Average across rows.
                   AVG(
                     -LN(GREATEST(1e-6, LEAST(1 - 1e-6,
                       CASE
                         WHEN home_goals > away_goals THEN p_home_win
                         WHEN home_goals < away_goals THEN p_away_win
                         ELSE p_draw
                       END
                     )))
                   ) AS mean_log_loss
            FROM per_team pt
            JOIN teams t ON t.id = pt.team_id
            GROUP BY t.slug, t.name, t.short_name
            HAVING COUNT(*) >= $3
            ORDER BY (COUNT(*) FILTER (
              WHERE (p_home_win >= p_draw AND p_home_win >= p_away_win AND home_goals > away_goals)
                 OR (p_away_win >= p_home_win AND p_away_win >= p_draw AND home_goals < away_goals)
                 OR (p_draw >= p_home_win AND p_draw >= p_away_win AND home_goals = away_goals)
            )::float / COUNT(*)) DESC
            """,
            season, league, min_sample,
        )
    teams = [
        TeamAccuracy(
            slug=r["slug"], name=r["name"], short_name=r["short_name"],
            league_code=r["league_code"],
            scored=int(r["scored"]), correct=int(r["correct"]),
            accuracy=(int(r["correct"]) / int(r["scored"])) if r["scored"] else 0.0,
            mean_log_loss=float(r["mean_log_loss"] or 0.0),
        )
        for r in rows
    ]
    return AccuracyByTeamResponse(
        season=season, min_sample=min_sample, teams=teams,
    )
