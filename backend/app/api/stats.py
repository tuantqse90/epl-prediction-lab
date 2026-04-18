"""GET /api/stats/* — accuracy + calibration breakdown of stored predictions."""

from __future__ import annotations

import math
from datetime import date

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/stats", tags=["stats"])


class AccuracyOut(BaseModel):
    season: str
    scored: int
    correct: int
    accuracy: float
    baseline_home_accuracy: float
    mean_log_loss: float
    uniform_log_loss: float


class WeekBucket(BaseModel):
    week: int
    week_start: date
    n: int
    accuracy: float
    mean_log_loss: float


class CalibrationBin(BaseModel):
    bin_lo: float
    bin_hi: float
    n: int
    mean_predicted: float   # average confidence (max prob) across picks in this bin
    actual_hit_rate: float  # fraction where argmax matches outcome


class StatsOut(BaseModel):
    season: str
    overall: AccuracyOut
    brier: float
    by_week: list[WeekBucket]
    by_confidence: list[CalibrationBin]


class RecentMatchResult(BaseModel):
    match_id: int
    kickoff_time: date
    home_slug: str
    home_short: str
    away_slug: str
    away_short: str
    home_goals: int
    away_goals: int
    home_xg: float | None
    away_xg: float | None
    p_home_win: float
    p_draw: float
    p_away_win: float
    predicted_outcome: str
    actual_outcome: str
    hit: bool
    confidence: float


class RecentWindowOut(BaseModel):
    days: int
    scored: int
    correct: int
    accuracy: float
    mean_log_loss: float
    matches: list[RecentMatchResult]


class RoiPoint(BaseModel):
    date: date
    bets: int
    cumulative_pnl: float


class RoiOut(BaseModel):
    season: str
    threshold: float
    total_bets: int
    total_pnl: float
    roi_percent: float
    points: list[RoiPoint]


class ScorerOut(BaseModel):
    rank: int
    player_name: str
    position: str | None
    team_slug: str
    team_name: str
    team_short: str
    games: int
    minutes: int | None
    goals: int
    xg: float
    npxg: float
    assists: int
    xa: float
    key_passes: int
    goals_minus_xg: float



_ROI_QUERY = """
WITH latest AS (
    SELECT DISTINCT ON (p.match_id)
        p.match_id, p.p_home_win, p.p_draw, p.p_away_win
    FROM predictions p
    ORDER BY p.match_id, p.created_at DESC
)
SELECT m.kickoff_time, m.home_goals, m.away_goals,
       l.p_home_win, l.p_draw, l.p_away_win,
       o.odds_home, o.odds_draw, o.odds_away
FROM matches m
JOIN latest l ON l.match_id = m.id
JOIN match_odds o ON o.match_id = m.id
WHERE m.status = 'final' AND m.season = $1
  AND m.home_goals IS NOT NULL
ORDER BY m.kickoff_time ASC
"""


_RECENT_QUERY = """
WITH latest AS (
    SELECT DISTINCT ON (p.match_id)
        p.match_id, p.p_home_win, p.p_draw, p.p_away_win
    FROM predictions p
    ORDER BY p.match_id, p.created_at DESC
)
SELECT
    m.id AS match_id, m.kickoff_time, m.home_goals, m.away_goals,
    m.home_xg, m.away_xg,
    ht.slug AS home_slug, ht.short_name AS home_short,
    at.slug AS away_slug, at.short_name AS away_short,
    l.p_home_win, l.p_draw, l.p_away_win
FROM matches m
JOIN teams ht ON ht.id = m.home_team_id
JOIN teams at ON at.id = m.away_team_id
JOIN latest l ON l.match_id = m.id
WHERE m.status = 'final'
  AND m.home_goals IS NOT NULL
  AND m.kickoff_time >= NOW() - ($1 || ' days')::INTERVAL
  AND m.kickoff_time <= NOW()
ORDER BY m.kickoff_time DESC
"""


_QUERY = """
WITH latest AS (
    SELECT DISTINCT ON (p.match_id)
        p.match_id, p.p_home_win, p.p_draw, p.p_away_win
    FROM predictions p
    ORDER BY p.match_id, p.created_at DESC
)
SELECT
    m.id, m.home_goals, m.away_goals, m.kickoff_time,
    l.p_home_win, l.p_draw, l.p_away_win
FROM matches m
JOIN latest l ON l.match_id = m.id
WHERE m.status = 'final'
  AND m.season = $1
  AND m.home_goals IS NOT NULL
ORDER BY m.kickoff_time ASC
"""

_CAL_BINS: list[tuple[float, float]] = [
    (0.33, 0.40),
    (0.40, 0.50),
    (0.50, 0.60),
    (0.60, 0.70),
    (0.70, 0.80),
    (0.80, 1.01),
]


def _outcome(hg: int, ag: int) -> str:
    return "H" if hg > ag else ("A" if hg < ag else "D")


async def _fetch_scored(pool, season: str):
    async with pool.acquire() as conn:
        return await conn.fetch(_QUERY, season)


def _aggregate(rows):
    scored = 0
    correct = 0
    baseline_home = 0
    ll_sum = 0.0
    brier_sum = 0.0

    for r in rows:
        scored += 1
        hg, ag = r["home_goals"], r["away_goals"]
        probs = {"H": float(r["p_home_win"]), "D": float(r["p_draw"]), "A": float(r["p_away_win"])}
        outcome = _outcome(hg, ag)
        predicted = max(probs, key=probs.get)
        if predicted == outcome:
            correct += 1
        if outcome == "H":
            baseline_home += 1
        ll_sum += -math.log(max(probs[outcome], 1e-12))
        # Brier = mean squared error over 3 one-hot classes
        for k in "HDA":
            diff = probs[k] - (1.0 if k == outcome else 0.0)
            brier_sum += diff * diff

    return scored, correct, baseline_home, ll_sum, brier_sum


@router.get("/accuracy", response_model=AccuracyOut)
async def accuracy(
    request: Request,
    season: str = Query("2025-26"),
) -> AccuracyOut:
    rows = await _fetch_scored(request.app.state.pool, season)
    scored, correct, baseline_home, ll_sum, _ = _aggregate(rows)

    return AccuracyOut(
        season=season,
        scored=scored,
        correct=correct,
        accuracy=(correct / scored) if scored else 0.0,
        baseline_home_accuracy=(baseline_home / scored) if scored else 0.0,
        mean_log_loss=(ll_sum / scored) if scored else 0.0,
        uniform_log_loss=-math.log(1 / 3),
    )


@router.get("/calibration", response_model=StatsOut)
async def calibration(request: Request, season: str = Query("2025-26")) -> StatsOut:
    """Breakdown of accuracy + reliability by matchweek and confidence bin."""
    rows = await _fetch_scored(request.app.state.pool, season)

    scored, correct, baseline_home, ll_sum, brier_sum = _aggregate(rows)
    overall = AccuracyOut(
        season=season,
        scored=scored,
        correct=correct,
        accuracy=(correct / scored) if scored else 0.0,
        baseline_home_accuracy=(baseline_home / scored) if scored else 0.0,
        mean_log_loss=(ll_sum / scored) if scored else 0.0,
        uniform_log_loss=-math.log(1 / 3),
    )
    brier = (brier_sum / scored) if scored else 0.0

    # --- by week bucket (7-day buckets from season's first match) ---
    by_week: list[WeekBucket] = []
    if rows:
        season_start = min(r["kickoff_time"] for r in rows).date()
        buckets: dict[int, list] = {}
        for r in rows:
            days = (r["kickoff_time"].date() - season_start).days
            w = days // 7  # 0-based week bucket
            buckets.setdefault(w, []).append(r)
        for w in sorted(buckets):
            sub = buckets[w]
            s, c, _, ll, _ = _aggregate(sub)
            from datetime import timedelta
            by_week.append(
                WeekBucket(
                    week=w + 1,
                    week_start=season_start + timedelta(days=w * 7),
                    n=s,
                    accuracy=(c / s) if s else 0.0,
                    mean_log_loss=(ll / s) if s else 0.0,
                )
            )

    # --- by confidence bin ---
    by_conf: list[CalibrationBin] = []
    for lo, hi in _CAL_BINS:
        in_bin = []
        for r in rows:
            probs = {"H": float(r["p_home_win"]), "D": float(r["p_draw"]), "A": float(r["p_away_win"])}
            conf = max(probs.values())
            if lo <= conf < hi:
                in_bin.append((r, probs, conf))
        if not in_bin:
            continue
        hits = 0
        mean_pred_sum = 0.0
        for r, probs, conf in in_bin:
            outcome = _outcome(r["home_goals"], r["away_goals"])
            predicted = max(probs, key=probs.get)
            if predicted == outcome:
                hits += 1
            mean_pred_sum += conf
        n = len(in_bin)
        by_conf.append(
            CalibrationBin(
                bin_lo=lo,
                bin_hi=min(hi, 1.0),
                n=n,
                mean_predicted=mean_pred_sum / n,
                actual_hit_rate=hits / n,
            )
        )

    return StatsOut(
        season=season,
        overall=overall,
        brier=brier,
        by_week=by_week,
        by_confidence=by_conf,
    )


@router.get("/recent", response_model=RecentWindowOut)
async def recent(request: Request, days: int = Query(7, ge=1, le=30)) -> RecentWindowOut:
    """Finals in the last N days with how the model scored each pick."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(_RECENT_QUERY, str(days))

    out_rows: list[RecentMatchResult] = []
    correct = 0
    ll_sum = 0.0
    for r in rows:
        probs = {"H": float(r["p_home_win"]), "D": float(r["p_draw"]), "A": float(r["p_away_win"])}
        actual = _outcome(r["home_goals"], r["away_goals"])
        predicted = max(probs, key=probs.get)
        hit = predicted == actual
        if hit:
            correct += 1
        ll_sum += -math.log(max(probs[actual], 1e-12))
        out_rows.append(
            RecentMatchResult(
                match_id=r["match_id"],
                kickoff_time=r["kickoff_time"].date(),
                home_slug=r["home_slug"],
                home_short=r["home_short"],
                away_slug=r["away_slug"],
                away_short=r["away_short"],
                home_goals=r["home_goals"],
                away_goals=r["away_goals"],
                home_xg=float(r["home_xg"]) if r["home_xg"] is not None else None,
                away_xg=float(r["away_xg"]) if r["away_xg"] is not None else None,
                p_home_win=probs["H"],
                p_draw=probs["D"],
                p_away_win=probs["A"],
                predicted_outcome=predicted,
                actual_outcome=actual,
                hit=hit,
                confidence=probs[predicted],
            )
        )

    n = len(out_rows)
    return RecentWindowOut(
        days=days,
        scored=n,
        correct=correct,
        accuracy=(correct / n) if n else 0.0,
        mean_log_loss=(ll_sum / n) if n else 0.0,
        matches=out_rows,
    )


@router.get("/roi", response_model=RoiOut)
async def roi(
    request: Request,
    season: str = Query("2025-26"),
    threshold: float = Query(0.05, ge=0.0, le=0.5),
) -> RoiOut:
    """Cumulative 1-unit flat-stake P&L across every ≥threshold edge bet."""
    from app.ingest.odds import fair_probs

    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(_ROI_QUERY, season)

    by_date: dict[date, dict[str, float]] = {}
    total_pnl = 0.0
    total_bets = 0
    for r in rows:
        probs = {"H": float(r["p_home_win"]), "D": float(r["p_draw"]), "A": float(r["p_away_win"])}
        odds = {"H": r["odds_home"], "D": r["odds_draw"], "A": r["odds_away"]}
        fair = fair_probs(odds["H"], odds["D"], odds["A"])
        if fair is None:
            continue
        fair_map = {"H": fair[0], "D": fair[1], "A": fair[2]}
        outcome = _outcome(r["home_goals"], r["away_goals"])
        day = r["kickoff_time"].date()
        entry = by_date.setdefault(day, {"pnl": 0.0, "bets": 0})
        for side in "HDA":
            edge = probs[side] - fair_map[side]
            if edge < threshold:
                continue
            entry["bets"] += 1
            total_bets += 1
            pnl = (float(odds[side]) - 1.0) if side == outcome else -1.0
            entry["pnl"] += pnl
            total_pnl += pnl

    points: list[RoiPoint] = []
    cumulative = 0.0
    cum_bets = 0
    for day in sorted(by_date):
        cumulative += by_date[day]["pnl"]
        cum_bets += int(by_date[day]["bets"])
        points.append(
            RoiPoint(
                date=day,
                bets=cum_bets,
                cumulative_pnl=round(cumulative, 4),
            )
        )

    return RoiOut(
        season=season,
        threshold=threshold,
        total_bets=total_bets,
        total_pnl=round(total_pnl, 4),
        roi_percent=(total_pnl / total_bets * 100) if total_bets else 0.0,
        points=points,
    )


@router.get("/scorers", response_model=list[ScorerOut])
async def scorers(
    request: Request,
    season: str = Query("2025-26"),
    sort: str = Query("goals", pattern="^(goals|xg|assists|goals_minus_xg)$"),
    limit: int = Query(25, ge=1, le=100),
) -> list[ScorerOut]:
    pool = request.app.state.pool
    sort_col = {
        "goals": "p.goals DESC NULLS LAST, p.xg DESC NULLS LAST",
        "xg": "p.xg DESC NULLS LAST, p.goals DESC NULLS LAST",
        "assists": "p.assists DESC NULLS LAST, p.xa DESC NULLS LAST",
        "goals_minus_xg": "(p.goals::float - COALESCE(p.xg, 0)) DESC NULLS LAST",
    }[sort]
    query = f"""
    SELECT p.player_name, p.position, p.goals, p.xg, p.npxg, p.assists, p.xa,
           p.key_passes, p.games,
           t.slug AS team_slug, t.name AS team_name, t.short_name AS team_short
    FROM player_season_stats p
    JOIN teams t ON t.id = p.team_id
    WHERE p.season = $1
    ORDER BY {sort_col}
    LIMIT $2
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, season, limit)
    out: list[ScorerOut] = []
    for i, r in enumerate(rows, 1):
        goals = int(r["goals"] or 0)
        xg = float(r["xg"] or 0.0)
        out.append(
            ScorerOut(
                rank=i,
                player_name=r["player_name"],
                position=r["position"],
                team_slug=r["team_slug"],
                team_name=r["team_name"],
                team_short=r["team_short"],
                games=int(r["games"] or 0),
                minutes=None,
                goals=goals,
                xg=round(xg, 2),
                npxg=round(float(r["npxg"] or 0.0), 2),
                assists=int(r["assists"] or 0),
                xa=round(float(r["xa"] or 0.0), 2),
                key_passes=int(r["key_passes"] or 0),
                goals_minus_xg=round(goals - xg, 2),
            )
        )
    return out
