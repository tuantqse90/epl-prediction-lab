"""GET /api/stats/power-rankings — elo-ranked table + week-over-week delta.

Computes two elo snapshots from the canonical match stream:
  - current: all finals up to NOW
  - prior:   all finals up to NOW - 7 days

The delta is the week-over-week rating change per team. Biggest movers
(top 3 up, top 3 down) surface as a "movers" strip.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.models.elo import compute_ratings


router = APIRouter(prefix="/api/stats", tags=["stats"])


class PowerTeam(BaseModel):
    rank: int
    slug: str
    short_name: str
    name: str
    elo: float
    elo_prior: float | None
    delta: float | None
    rank_prior: int | None
    rank_delta: int | None


class PowerMover(BaseModel):
    slug: str
    short_name: str
    delta: float


class PowerRankingsResponse(BaseModel):
    league_code: str
    season: str
    as_of: datetime
    snapshot_prior: datetime
    teams: list[PowerTeam]
    top_risers: list[PowerMover]
    top_fallers: list[PowerMover]


@router.get("/power-rankings", response_model=PowerRankingsResponse)
async def power_rankings(
    request: Request,
    league: str = Query(..., description="league code"),
    season: str = Query("2025-26"),
    lookback_days: int = Query(7, ge=3, le=30),
) -> PowerRankingsResponse:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT m.kickoff_time AS date,
                   ht.slug AS home_team, at.slug AS away_team,
                   ht.short_name AS home_short, at.short_name AS away_short,
                   ht.name AS home_name, at.name AS away_name,
                   m.home_goals, m.away_goals
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.league_code = $1 AND m.season = $2
              AND m.status = 'final' AND m.home_goals IS NOT NULL
            ORDER BY m.kickoff_time ASC
            """,
            league, season,
        )

    if not rows:
        now = datetime.now(timezone.utc)
        return PowerRankingsResponse(
            league_code=league, season=season, as_of=now,
            snapshot_prior=now - timedelta(days=lookback_days),
            teams=[], top_risers=[], top_fallers=[],
        )

    df = pd.DataFrame([
        {
            "date": r["date"],
            "home_team": r["home_team"], "away_team": r["away_team"],
            "home_goals": int(r["home_goals"]), "away_goals": int(r["away_goals"]),
            "is_result": True,
        }
        for r in rows
    ])

    now = datetime.now(timezone.utc)
    prior_cutoff = now - timedelta(days=lookback_days)

    ratings_now = compute_ratings(df)
    prior_df = df[df["date"] < prior_cutoff]
    ratings_prior = compute_ratings(prior_df) if not prior_df.empty else {}

    # Team meta (short_name, full name) from the match rows
    meta: dict[str, dict] = {}
    for r in rows:
        meta[r["home_team"]] = {"short_name": r["home_short"], "name": r["home_name"]}
        meta[r["away_team"]] = {"short_name": r["away_short"], "name": r["away_name"]}

    # Build sorted tables (rank by current elo desc)
    slugs_now = sorted(ratings_now.keys(), key=lambda s: -ratings_now[s])
    rank_by_slug_now = {slug: i + 1 for i, slug in enumerate(slugs_now)}

    slugs_prior = sorted(ratings_prior.keys(), key=lambda s: -ratings_prior[s])
    rank_by_slug_prior = {slug: i + 1 for i, slug in enumerate(slugs_prior)}

    teams: list[PowerTeam] = []
    for slug in slugs_now:
        elo = ratings_now[slug]
        elo_prior = ratings_prior.get(slug)
        delta = (elo - elo_prior) if elo_prior is not None else None
        rank_prior = rank_by_slug_prior.get(slug)
        rank_delta = (
            rank_prior - rank_by_slug_now[slug]  # positive = moved up
            if rank_prior is not None else None
        )
        m = meta.get(slug, {"short_name": slug, "name": slug})
        teams.append(PowerTeam(
            rank=rank_by_slug_now[slug],
            slug=slug,
            short_name=m["short_name"],
            name=m["name"],
            elo=elo,
            elo_prior=elo_prior,
            delta=delta,
            rank_prior=rank_prior,
            rank_delta=rank_delta,
        ))

    with_delta = [t for t in teams if t.delta is not None]
    with_delta.sort(key=lambda t: t.delta or 0, reverse=True)
    top_risers = [PowerMover(slug=t.slug, short_name=t.short_name, delta=t.delta) for t in with_delta[:3]]
    top_fallers = [
        PowerMover(slug=t.slug, short_name=t.short_name, delta=t.delta)
        for t in with_delta[-3:][::-1] if t.delta and t.delta < 0
    ]

    return PowerRankingsResponse(
        league_code=league, season=season, as_of=now,
        snapshot_prior=prior_cutoff,
        teams=teams,
        top_risers=top_risers,
        top_fallers=top_fallers,
    )
