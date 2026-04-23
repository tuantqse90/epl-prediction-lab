"""GET /api/stats/title-race — Monte Carlo league finish distribution.

Fetches current standings + remaining fixtures (with model λ per side)
and calls simulate_title_race to produce per-team P(champions), P(top-4),
P(relegate), mean_points, and a position histogram.

Cached at the edge for 10 minutes — sims are deterministic given seed
and inputs rarely change intra-day.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.models.title_race import simulate_title_race


router = APIRouter(prefix="/api/stats", tags=["stats"])


class TeamSummary(BaseModel):
    slug: str
    short_name: str
    name: str
    played: int
    points: int
    gd: int
    gf: int
    p_champions: float
    p_top_four: float
    p_relegate: float
    mean_points: float
    position_histogram: list[float]


class TitleRaceResponse(BaseModel):
    league_code: str
    season: str
    n_teams: int
    n_simulations: int
    remaining_fixtures: int
    teams: list[TeamSummary]


@router.get("/title-race", response_model=TitleRaceResponse)
async def title_race(
    request: Request,
    league: str = Query(..., description="league code e.g. ENG-Premier League"),
    season: str = Query("2025-26"),
    n: int = Query(5000, ge=500, le=20000),
) -> TitleRaceResponse:
    pool = request.app.state.pool
    standings, team_meta = await _fetch_standings(pool, league, season)
    remaining = await _fetch_remaining_with_lambdas(pool, league, season)
    # Relegation count varies by league; Bundesliga officially drops 2 + 1
    # playoff but we treat "bottom 3 direct" uniformly — close enough for
    # drama-surface purposes.
    result = simulate_title_race(
        standings=standings, remaining=remaining,
        n_simulations=n, seed=42,
        relegation_count=3, top_count=4,
    )
    teams_out: list[TeamSummary] = []
    for slug, st in standings.items():
        meta = team_meta[slug]
        r = result[slug]
        teams_out.append(TeamSummary(
            slug=slug,
            short_name=meta["short_name"],
            name=meta["name"],
            played=st["played"],
            points=st["points"],
            gd=st["gd"],
            gf=st["gf"],
            p_champions=r["p_champions"],
            p_top_four=r["p_top_four"],
            p_relegate=r["p_relegate"],
            mean_points=r["mean_points"],
            position_histogram=r["position_histogram"],
        ))
    # Sort by mean_points desc as the canonical display order
    teams_out.sort(key=lambda t: -t.mean_points)
    return TitleRaceResponse(
        league_code=league,
        season=season,
        n_teams=len(teams_out),
        n_simulations=n,
        remaining_fixtures=len(remaining),
        teams=teams_out,
    )


# ---------------------------------------------------------------------------
# DB fetchers
# ---------------------------------------------------------------------------


async def _fetch_standings(pool, league: str, season: str) -> tuple[dict, dict]:
    """Current table from `final` matches. Returns (standings_by_slug,
    team_meta_by_slug). Only includes teams that have played ≥ 1 match
    this season — brand new promoted teams with no fixture yet would be
    missing."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH teams_in AS (
                SELECT DISTINCT
                  CASE WHEN m.home_team_id = t.id THEN t.id ELSE NULL END AS ht_id,
                  CASE WHEN m.away_team_id = t.id THEN t.id ELSE NULL END AS at_id,
                  m.id, m.home_team_id, m.away_team_id, m.status,
                  m.home_goals, m.away_goals
                FROM matches m
                JOIN teams t ON (t.id = m.home_team_id OR t.id = m.away_team_id)
                WHERE m.league_code = $1 AND m.season = $2
            ),
            season_matches AS (
                SELECT DISTINCT id, home_team_id, away_team_id, status,
                       home_goals, away_goals
                FROM teams_in
                WHERE status = 'final' AND home_goals IS NOT NULL
            ),
            per_team AS (
                -- Home rows
                SELECT
                  home_team_id AS team_id,
                  1 AS played,
                  CASE WHEN home_goals > away_goals THEN 3
                       WHEN home_goals = away_goals THEN 1
                       ELSE 0 END AS points,
                  home_goals - away_goals AS gd,
                  home_goals AS gf
                FROM season_matches
                UNION ALL
                SELECT
                  away_team_id AS team_id,
                  1 AS played,
                  CASE WHEN away_goals > home_goals THEN 3
                       WHEN away_goals = home_goals THEN 1
                       ELSE 0 END AS points,
                  away_goals - home_goals AS gd,
                  away_goals AS gf
                FROM season_matches
            )
            SELECT t.slug, t.name, t.short_name,
                   SUM(p.played) AS played,
                   SUM(p.points) AS points,
                   SUM(p.gd)     AS gd,
                   SUM(p.gf)     AS gf
            FROM per_team p
            JOIN teams t ON t.id = p.team_id
            GROUP BY t.slug, t.name, t.short_name
            ORDER BY SUM(p.points) DESC
            """,
            league, season,
        )
    standings: dict = {}
    meta: dict = {}
    for r in rows:
        standings[r["slug"]] = {
            "played": int(r["played"] or 0),
            "points": int(r["points"] or 0),
            "gd": int(r["gd"] or 0),
            "gf": int(r["gf"] or 0),
        }
        meta[r["slug"]] = {"name": r["name"], "short_name": r["short_name"]}
    return standings, meta


async def _fetch_remaining_with_lambdas(pool, league: str, season: str) -> list[dict]:
    """Scheduled fixtures in this season with model λ per side.

    λ comes from predictions.top_scorelines proxy (expected home + away
    goals from the Poisson matrix). For a match with prediction we
    recover λ by weighting argmax scorelines; fallback is a prior of
    (1.4, 1.1) — league-average home/away.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH latest AS (
                SELECT DISTINCT ON (p.match_id)
                  p.match_id, p.top_scorelines,
                  p.p_home_win, p.p_draw, p.p_away_win
                FROM predictions p
                ORDER BY p.match_id, p.created_at DESC
            )
            SELECT m.id, ht.slug AS home, at.slug AS away,
                   l.top_scorelines, l.p_home_win, l.p_draw, l.p_away_win
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            LEFT JOIN latest l ON l.match_id = m.id
            WHERE m.league_code = $1 AND m.season = $2
              AND m.status = 'scheduled'
            """,
            league, season,
        )
    out = []
    for r in rows:
        lam_h, lam_a = _derive_lambdas(
            r["top_scorelines"],
            r["p_home_win"], r["p_draw"], r["p_away_win"],
        )
        out.append({
            "home": r["home"], "away": r["away"],
            "lambda_h": lam_h, "lambda_a": lam_a,
        })
    return out


def _derive_lambdas(
    top_scorelines, p_home: float | None, p_draw: float | None, p_away: float | None,
) -> tuple[float, float]:
    """Recover (λ_home, λ_away) from stored prediction artefacts."""
    # Path 1: top_scorelines is a JSON list of {home, away, prob}. If the
    # model wrote them, expected goals = Σ prob_i × home_i (and same for
    # away). Small bias (≤top-10 scorelines cover ~60% of mass) but fast.
    if top_scorelines:
        try:
            if isinstance(top_scorelines, str):
                import json
                top_scorelines = json.loads(top_scorelines)
            total_p = sum(float(s.get("prob", 0)) for s in top_scorelines) or 1.0
            eh = sum(float(s.get("home", 0)) * float(s.get("prob", 0)) for s in top_scorelines)
            ea = sum(float(s.get("away", 0)) * float(s.get("prob", 0)) for s in top_scorelines)
            # Rescale to full probability mass (top-k only covers part of it).
            eh /= total_p
            ea /= total_p
            # Blend with league prior so unknown tail doesn't over-pull to 0.
            # Weight = total_p (how much of the mass we actually saw).
            eh = eh * total_p + 1.4 * (1 - total_p)
            ea = ea * total_p + 1.1 * (1 - total_p)
            if 0.1 < eh < 6 and 0.1 < ea < 6:
                return (eh, ea)
        except Exception:
            pass
    # Fallback: league-average home/away.
    return (1.4, 1.1)
