"""GET /api/live-edge — in-play edge across every currently-live match.

For each live match we have:
  - Live 3-way prob from the Poisson residual model (queries.record_to_match_dict).
  - Current best-of-books 1X2 odds from match_odds_history (most recent per source).

Edge = prob × odds − 1, per outcome per match. Surface the best-edge
outcome per match, >= threshold. This is a live value-bet scanner.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel


router = APIRouter(prefix="/api", tags=["live"])


class LiveEdgeRow(BaseModel):
    match_id: int
    league_code: str | None
    home_short: str
    away_short: str
    home_goals: int
    away_goals: int
    minute: int
    # Live 3-way probabilities (residual-time model)
    p_home_win: float
    p_draw: float
    p_away_win: float
    # Best odds currently available, per outcome
    best_home: float | None
    best_draw: float | None
    best_away: float | None
    # Best edge + which outcome it's on
    best_edge_pp: float
    best_edge_outcome: str    # H | D | A
    best_edge_odds: float
    best_edge_source: str | None


class LiveEdgeResponse(BaseModel):
    as_of: datetime
    matches: list[LiveEdgeRow]


@router.get("/live-edge", response_model=LiveEdgeResponse)
async def live_edge(
    request: Request,
    min_edge_pp: float = Query(2.0, ge=0.0, le=50.0),
) -> LiveEdgeResponse:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH live AS (
                SELECT m.id, m.league_code, m.minute, m.home_goals, m.away_goals,
                       ht.short_name AS home_short, at.short_name AS away_short,
                       m.matchweek, m.season
                FROM matches m
                JOIN teams ht ON ht.id = m.home_team_id
                JOIN teams at ON at.id = m.away_team_id
                WHERE m.status = 'live'
                  AND m.home_goals IS NOT NULL AND m.away_goals IS NOT NULL
                  AND m.minute IS NOT NULL
            ),
            latest_pred AS (
                SELECT DISTINCT ON (p.match_id)
                    p.match_id,
                    p.expected_home_goals, p.expected_away_goals
                FROM predictions p
                ORDER BY p.match_id, p.created_at DESC
            ),
            latest_odds AS (
                SELECT DISTINCT ON (h.match_id, h.source)
                    h.match_id, h.source,
                    h.odds_home, h.odds_draw, h.odds_away
                FROM match_odds_history h
                ORDER BY h.match_id, h.source, h.captured_at DESC
            )
            SELECT live.*, lp.expected_home_goals AS ehg, lp.expected_away_goals AS eag,
                   lo.source, lo.odds_home, lo.odds_draw, lo.odds_away
            FROM live
            JOIN latest_pred lp ON lp.match_id = live.id
            LEFT JOIN latest_odds lo ON lo.match_id = live.id
            """,
        )

    # Group by match; pick best odds per outcome across sources.
    per_match: dict[int, dict] = {}
    for r in rows:
        mid = r["id"]
        m = per_match.setdefault(mid, {
            "id": mid,
            "league_code": r["league_code"],
            "home_short": r["home_short"],
            "away_short": r["away_short"],
            "home_goals": int(r["home_goals"]),
            "away_goals": int(r["away_goals"]),
            "minute": int(r["minute"]),
            "ehg": float(r["ehg"]),
            "eag": float(r["eag"]),
            "best_home": None, "home_source": None,
            "best_draw": None, "draw_source": None,
            "best_away": None, "away_source": None,
        })
        if r["odds_home"]:
            oh = float(r["odds_home"])
            if m["best_home"] is None or oh > m["best_home"]:
                m["best_home"] = oh; m["home_source"] = r["source"]
        if r["odds_draw"]:
            od = float(r["odds_draw"])
            if m["best_draw"] is None or od > m["best_draw"]:
                m["best_draw"] = od; m["draw_source"] = r["source"]
        if r["odds_away"]:
            oa = float(r["odds_away"])
            if m["best_away"] is None or oa > m["best_away"]:
                m["best_away"] = oa; m["away_source"] = r["source"]

    # Compute live probs and find best edge per match
    from app.models.poisson import live_probabilities

    out: list[LiveEdgeRow] = []
    for m in per_match.values():
        lp = live_probabilities(
            m["ehg"], m["eag"], m["home_goals"], m["away_goals"],
            minute=m["minute"], rho=-0.15,
        )
        probs = {"H": lp.p_home_win, "D": lp.p_draw, "A": lp.p_away_win}
        odds = {"H": m["best_home"], "D": m["best_draw"], "A": m["best_away"]}
        src = {"H": m["home_source"], "D": m["draw_source"], "A": m["away_source"]}
        best = None
        for side in ("H", "D", "A"):
            if odds[side] is None or odds[side] <= 1:
                continue
            edge_pp = (probs[side] * odds[side] - 1) * 100
            if best is None or edge_pp > best[0]:
                best = (edge_pp, side, odds[side], src[side])
        if best is None or best[0] < min_edge_pp:
            continue
        out.append(LiveEdgeRow(
            match_id=m["id"], league_code=m["league_code"],
            home_short=m["home_short"], away_short=m["away_short"],
            home_goals=m["home_goals"], away_goals=m["away_goals"],
            minute=m["minute"],
            p_home_win=lp.p_home_win, p_draw=lp.p_draw, p_away_win=lp.p_away_win,
            best_home=m["best_home"], best_draw=m["best_draw"], best_away=m["best_away"],
            best_edge_pp=best[0], best_edge_outcome=best[1],
            best_edge_odds=best[2], best_edge_source=best[3],
        ))
    out.sort(key=lambda r: -r.best_edge_pp)
    return LiveEdgeResponse(as_of=datetime.utcnow(), matches=out)
