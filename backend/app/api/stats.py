"""GET /api/stats/* — accuracy + calibration breakdown of stored predictions."""

from __future__ import annotations

import math
from datetime import date

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.core.cache import TTLCache
from app.leagues import get_league

router = APIRouter(prefix="/api/stats", tags=["stats"])

# 5-min cache for expensive multi-season aggregation queries.
_STATS_CACHE = TTLCache(ttl_seconds=300)


def _resolve_league_code(league: str | None) -> str | None:
    if not league:
        return None
    try:
        return get_league(league).code
    except KeyError:
        return None


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
    league_code: str | None
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
    recap: str | None = None


class RecentWindowOut(BaseModel):
    days: int
    scored: int
    correct: int
    accuracy: float
    mean_log_loss: float
    # Excluding actual-draws from the denominator. The 3-way argmax
    # almost never picks D (draws average 25% real-world but sit below
    # both H and A in per-match probability), so argmax-accuracy is
    # structurally capped around 75%. Showing no-draw accuracy alongside
    # makes the model's real hit-rate on predictable matches visible.
    accuracy_excl_draws: float = 0.0
    scored_excl_draws: int = 0
    draws_in_window: int = 0
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
    photo_url: str | None = None
    league_code: str | None = None



_ROI_QUERY = """
WITH latest AS (
    SELECT DISTINCT ON (p.match_id)
        p.match_id, p.p_home_win, p.p_draw, p.p_away_win
    FROM predictions p
    ORDER BY p.match_id, p.created_at DESC
),
avg_odds AS (
    -- One aggregate-odds row per match. Preference order: 'the-odds-api:avg'
    -- (multi-book average, freshest), then 'football-data:avg' (historical
    -- pooled), then per-book average fallback.
    SELECT DISTINCT ON (match_id) match_id, odds_home, odds_draw, odds_away
    FROM match_odds
    WHERE source LIKE '%:avg'
       OR source LIKE 'odds-api:%'
    ORDER BY match_id,
             CASE WHEN source = 'the-odds-api:avg' THEN 0
                  WHEN source = 'football-data:avg' THEN 1
                  ELSE 2 END,
             captured_at DESC
),
best_odds AS (
    -- Best (maximum) per-outcome price across every odds-api:<book> row
    -- for the match. Falls back to the avg row when no per-book rows exist.
    SELECT match_id,
           MAX(odds_home) AS best_home,
           MAX(odds_draw) AS best_draw,
           MAX(odds_away) AS best_away
    FROM match_odds
    WHERE source LIKE 'odds-api:%'
    GROUP BY match_id
)
SELECT m.kickoff_time, m.league_code, m.home_goals, m.away_goals,
       l.p_home_win, l.p_draw, l.p_away_win,
       a.odds_home, a.odds_draw, a.odds_away,
       COALESCE(b.best_home, a.odds_home) AS best_home,
       COALESCE(b.best_draw, a.odds_draw) AS best_draw,
       COALESCE(b.best_away, a.odds_away) AS best_away
FROM matches m
JOIN latest l ON l.match_id = m.id
JOIN avg_odds a ON a.match_id = m.id
LEFT JOIN best_odds b ON b.match_id = m.id
WHERE m.status = 'final' AND m.season = $1
  AND m.home_goals IS NOT NULL
  AND ($2::text IS NULL OR m.league_code = $2)
ORDER BY m.kickoff_time ASC
"""


# Variant of _ROI_QUERY that supports a rolling time window instead of a
# fixed season. Used by /roi/by-league with window=7d|30d|season.
_ROI_QUERY_WINDOW = """
WITH latest AS (
    SELECT DISTINCT ON (p.match_id)
        p.match_id, p.p_home_win, p.p_draw, p.p_away_win
    FROM predictions p
    ORDER BY p.match_id, p.created_at DESC
),
avg_odds AS (
    SELECT DISTINCT ON (match_id) match_id, odds_home, odds_draw, odds_away
    FROM match_odds
    WHERE source LIKE '%:avg'
       OR source LIKE 'odds-api:%'
    ORDER BY match_id,
             CASE WHEN source = 'the-odds-api:avg' THEN 0
                  WHEN source = 'football-data:avg' THEN 1
                  ELSE 2 END,
             captured_at DESC
),
best_odds AS (
    SELECT match_id,
           MAX(odds_home) AS best_home,
           MAX(odds_draw) AS best_draw,
           MAX(odds_away) AS best_away
    FROM match_odds
    WHERE source LIKE 'odds-api:%'
    GROUP BY match_id
)
SELECT m.kickoff_time, m.league_code, m.home_goals, m.away_goals,
       l.p_home_win, l.p_draw, l.p_away_win,
       a.odds_home, a.odds_draw, a.odds_away,
       COALESCE(b.best_home, a.odds_home) AS best_home,
       COALESCE(b.best_draw, a.odds_draw) AS best_draw,
       COALESCE(b.best_away, a.odds_away) AS best_away
FROM matches m
JOIN latest l ON l.match_id = m.id
JOIN avg_odds a ON a.match_id = m.id
LEFT JOIN best_odds b ON b.match_id = m.id
WHERE m.status = 'final'
  AND m.home_goals IS NOT NULL
  AND m.kickoff_time >= NOW() - ($1 || ' days')::INTERVAL
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
    m.home_xg, m.away_xg, m.league_code, m.recap,
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
  AND ($2::text IS NULL OR m.league_code = $2)
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
  AND ($2::text IS NULL OR m.league_code = $2)
ORDER BY m.kickoff_time ASC
"""

def _compute_roi_metrics(rows, threshold: float) -> dict:
    """Flat 1-unit stake PnL across every model side with edge ≥ threshold.

    ``rows`` is any iterable of asyncpg-like rows exposing the prediction
    probabilities, reference + best odds, and final goals. Accepts attr-style
    access (asyncpg Record, SimpleNamespace) and mapping-style (dict) rows.
    """
    from app.ingest.odds import fair_probs

    pnl_vig = 0.0
    pnl_nov = 0.0
    bets = 0
    wins = 0
    ll_sum = 0.0
    ll_n = 0

    for r in rows:
        p = {"H": float(_g(r, "p_home_win")),
             "D": float(_g(r, "p_draw")),
             "A": float(_g(r, "p_away_win"))}
        avg = {"H": _g(r, "odds_home"), "D": _g(r, "odds_draw"), "A": _g(r, "odds_away")}
        best = {"H": _g(r, "best_home"), "D": _g(r, "best_draw"), "A": _g(r, "best_away")}
        if any(v is None for v in avg.values()) or any(v is None for v in best.values()):
            continue
        fair = fair_probs(avg["H"], avg["D"], avg["A"])
        if fair is None:
            continue
        fair_map = {"H": fair[0], "D": fair[1], "A": fair[2]}
        outcome = _outcome(int(_g(r, "home_goals")), int(_g(r, "away_goals")))
        ll_sum += -math.log(max(p[outcome], 1e-12))
        ll_n += 1
        for side in "HDA":
            edge = p[side] - fair_map[side]
            if edge < threshold:
                continue
            bets += 1
            hit = side == outcome
            if hit:
                wins += 1
            pnl_vig += (float(best[side]) - 1.0) if hit else -1.0
            if fair_map[side] > 0:
                nv_odds = 1.0 / fair_map[side]
                pnl_nov += (nv_odds - 1.0) if hit else -1.0

    return {
        "bets": bets,
        "wins": wins,
        "pnl_vig": round(pnl_vig, 4),
        "pnl_nov": round(pnl_nov, 4),
        "roi_vig_pct": (pnl_vig / bets * 100.0) if bets else 0.0,
        "roi_nov_pct": (pnl_nov / bets * 100.0) if bets else 0.0,
        "mean_log_loss": (ll_sum / ll_n) if ll_n else 0.0,
        "scored": ll_n,
    }


def _compute_roi_by_league(rows, threshold: float) -> list[dict]:
    """Group rows by league_code, run _compute_roi_metrics per group, sort
    by bets desc. Leagues with zero bets are kept so the caller can show the
    full universe; sort still places the busier markets first."""
    buckets: dict[str, list] = {}
    for r in rows:
        lg = _g(r, "league_code") or "unknown"
        buckets.setdefault(lg, []).append(r)

    out: list[dict] = []
    for lg, sub in buckets.items():
        metrics = _compute_roi_metrics(sub, threshold)
        out.append({"league_code": lg, **metrics})
    out.sort(key=lambda x: (-x["bets"], x["league_code"]))
    return out


def _g(r, key):
    """Row-accessor that works with both asyncpg Records (attr + subscript)
    and SimpleNamespace test stand-ins (attr only)."""
    if hasattr(r, key):
        return getattr(r, key)
    return r[key]


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


async def _fetch_scored(pool, season: str, league_code: str | None = None):
    async with pool.acquire() as conn:
        return await conn.fetch(_QUERY, season, league_code)


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
    league: str | None = Query(None),
) -> AccuracyOut:
    league_code = _resolve_league_code(league)
    rows = await _fetch_scored(request.app.state.pool, season, league_code)
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
async def calibration(
    request: Request,
    season: str = Query("2025-26"),
    league: str | None = Query(None),
) -> StatsOut:
    """Breakdown of accuracy + reliability by matchweek and confidence bin."""
    league_code = _resolve_league_code(league)
    rows = await _fetch_scored(request.app.state.pool, season, league_code)

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
async def recent(
    request: Request,
    days: int = Query(7, ge=1, le=30),
    league: str | None = Query(None),
) -> RecentWindowOut:
    """Finals in the last N days with how the model scored each pick."""
    pool = request.app.state.pool
    league_code = _resolve_league_code(league)
    async with pool.acquire() as conn:
        rows = await conn.fetch(_RECENT_QUERY, str(days), league_code)

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
                league_code=r["league_code"],
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
                recap=r["recap"],
            )
        )

    n = len(out_rows)
    draws = sum(1 for r in out_rows if r.actual_outcome == "D")
    non_draw_n = n - draws
    non_draw_correct = sum(
        1 for r in out_rows if r.actual_outcome != "D" and r.hit
    )
    return RecentWindowOut(
        days=days,
        scored=n,
        correct=correct,
        accuracy=(correct / n) if n else 0.0,
        mean_log_loss=(ll_sum / n) if n else 0.0,
        accuracy_excl_draws=(non_draw_correct / non_draw_n) if non_draw_n else 0.0,
        scored_excl_draws=non_draw_n,
        draws_in_window=draws,
        matches=out_rows,
    )


class Comparison(BaseModel):
    """Side-by-side accuracy of four predictors over the chosen window."""
    days: int
    league_code: str | None
    scored: int
    model_accuracy: float
    bookmaker_accuracy: float     # argmax of fair-probs from market odds
    home_baseline_accuracy: float
    uniform_baseline_accuracy: float
    model_log_loss: float


_COMPARISON_QUERY_WINDOWED = """
WITH latest AS (
    SELECT DISTINCT ON (p.match_id)
        p.match_id, p.p_home_win, p.p_draw, p.p_away_win
    FROM predictions p
    ORDER BY p.match_id, p.created_at DESC
)
SELECT m.home_goals, m.away_goals,
       l.p_home_win, l.p_draw, l.p_away_win,
       o.odds_home, o.odds_draw, o.odds_away
FROM matches m
JOIN latest l ON l.match_id = m.id
LEFT JOIN LATERAL (
    SELECT odds_home, odds_draw, odds_away
    FROM match_odds WHERE match_id = m.id
    ORDER BY captured_at DESC LIMIT 1
) o ON TRUE
WHERE m.status = 'final'
  AND m.home_goals IS NOT NULL
  AND m.kickoff_time >= NOW() - ($1 || ' days')::INTERVAL
  AND ($2::text IS NULL OR m.league_code = $2)
"""

_COMPARISON_QUERY_ALL = """
WITH latest AS (
    SELECT DISTINCT ON (p.match_id)
        p.match_id, p.p_home_win, p.p_draw, p.p_away_win
    FROM predictions p
    ORDER BY p.match_id, p.created_at DESC
)
SELECT m.home_goals, m.away_goals,
       l.p_home_win, l.p_draw, l.p_away_win,
       o.odds_home, o.odds_draw, o.odds_away
FROM matches m
JOIN latest l ON l.match_id = m.id
LEFT JOIN LATERAL (
    SELECT odds_home, odds_draw, odds_away
    FROM match_odds WHERE match_id = m.id
    ORDER BY captured_at DESC LIMIT 1
) o ON TRUE
WHERE m.status = 'final'
  AND m.home_goals IS NOT NULL
  AND ($1::text IS NULL OR m.league_code = $1)
"""


@router.get("/comparison", response_model=Comparison)
async def comparison(
    request: Request,
    days: int = Query(30, ge=0, le=9999, description="0 = all-time"),
    league: str | None = Query(None),
) -> Comparison:
    """Four-way accuracy: model vs bookmakers vs always-home vs uniform.

    Pass ``days=0`` to ignore the time window and score all finals in the DB.
    """
    from app.ingest.odds import fair_probs

    pool = request.app.state.pool
    league_code = _resolve_league_code(league)
    cache_key = ("comparison", days, league_code)
    cached = _STATS_CACHE.get(cache_key)
    if cached is not None:
        return cached

    async with pool.acquire() as conn:
        if days == 0:
            rows = await conn.fetch(_COMPARISON_QUERY_ALL, league_code)
        else:
            rows = await conn.fetch(_COMPARISON_QUERY_WINDOWED, str(days), league_code)

    scored = 0
    model_correct = 0
    bk_correct = 0
    home_correct = 0
    ll_sum = 0.0

    for r in rows:
        hg, ag = int(r["home_goals"]), int(r["away_goals"])
        actual = _outcome(hg, ag)

        probs = {"H": float(r["p_home_win"]), "D": float(r["p_draw"]), "A": float(r["p_away_win"])}
        model_pick = max(probs, key=probs.get)
        if model_pick == actual:
            model_correct += 1
        ll_sum += -math.log(max(probs[actual], 1e-12))

        if actual == "H":
            home_correct += 1

        if r["odds_home"] is not None:
            fair = fair_probs(r["odds_home"], r["odds_draw"], r["odds_away"])
            if fair:
                bk_probs = {"H": fair[0], "D": fair[1], "A": fair[2]}
                if max(bk_probs, key=bk_probs.get) == actual:
                    bk_correct += 1
        scored += 1

    def _acc(n: int) -> float:
        return n / scored if scored else 0.0

    out = Comparison(
        days=days,
        league_code=league_code,
        scored=scored,
        model_accuracy=_acc(model_correct),
        bookmaker_accuracy=_acc(bk_correct),
        home_baseline_accuracy=_acc(home_correct),
        uniform_baseline_accuracy=1.0 / 3.0,
        model_log_loss=(ll_sum / scored) if scored else 0.0,
    )
    _STATS_CACHE.set(cache_key, out)
    return out


class SinceUpgrade(BaseModel):
    """Live log-loss + accuracy on matches scored with a specific model version.

    Used by the /proof banner to demonstrate the v2 ensemble in the wild,
    not just in backtest.
    """
    pattern: str
    scored: int
    correct: int
    accuracy: float
    log_loss: float
    earliest: date | None
    latest: date | None


_SINCE_UPGRADE_QUERY = """
WITH v2 AS (
    SELECT DISTINCT ON (p.match_id)
        p.match_id, p.p_home_win, p.p_draw, p.p_away_win, p.model_version, p.created_at
    FROM predictions p
    WHERE p.model_version LIKE '%' || $1::text || '%'
    ORDER BY p.match_id, p.created_at DESC
)
SELECT m.home_goals, m.away_goals, m.kickoff_time,
       v2.p_home_win, v2.p_draw, v2.p_away_win
FROM matches m
JOIN v2 ON v2.match_id = m.id
WHERE m.status = 'final'
  AND m.home_goals IS NOT NULL
"""


@router.get("/since-upgrade", response_model=SinceUpgrade)
async def since_upgrade(
    request: Request,
    pattern: str = Query("xgb=0.6", description="Substring that must appear in predictions.model_version"),
) -> SinceUpgrade:
    """Aggregate log-loss + accuracy for matches predicted with a specific model.

    Pattern matches `model_version` via SQL LIKE. The default `xgb=0.6`
    filters to predictions written after the 2026-04-19 ensemble upgrade.
    """
    pool = request.app.state.pool
    cache_key = ("since_upgrade", pattern)
    cached = _STATS_CACHE.get(cache_key)
    if cached is not None:
        return cached

    async with pool.acquire() as conn:
        rows = await conn.fetch(_SINCE_UPGRADE_QUERY, pattern)

    scored = 0
    correct = 0
    ll_sum = 0.0
    dates: list = []
    for r in rows:
        hg, ag = int(r["home_goals"]), int(r["away_goals"])
        actual = _outcome(hg, ag)
        probs = {"H": float(r["p_home_win"]), "D": float(r["p_draw"]), "A": float(r["p_away_win"])}
        if max(probs, key=probs.get) == actual:
            correct += 1
        ll_sum += -math.log(max(probs[actual], 1e-12))
        scored += 1
        dates.append(r["kickoff_time"].date())

    out = SinceUpgrade(
        pattern=pattern,
        scored=scored,
        correct=correct,
        accuracy=correct / scored if scored else 0.0,
        log_loss=ll_sum / scored if scored else 0.0,
        earliest=min(dates) if dates else None,
        latest=max(dates) if dates else None,
    )
    _STATS_CACHE.set(cache_key, out)
    return out


class HistorySeason(BaseModel):
    season: str
    scored: int
    correct: int
    accuracy: float
    mean_log_loss: float
    baseline_home_accuracy: float


@router.get("/history", response_model=list[HistorySeason])
async def history(
    request: Request,
    league: str | None = Query(None),
) -> list[HistorySeason]:
    """Per-season accuracy across all seasons in the DB, scoped by league."""
    pool = request.app.state.pool
    league_code = _resolve_league_code(league)
    cached = _STATS_CACHE.get(("history", league_code))
    if cached is not None:
        return cached
    async with pool.acquire() as conn:
        seasons = await conn.fetch(
            """
            SELECT DISTINCT season
            FROM matches
            WHERE status = 'final'
              AND ($1::text IS NULL OR league_code = $1)
            ORDER BY season ASC
            """,
            league_code,
        )

    out: list[HistorySeason] = []
    for row in seasons:
        season = row["season"]
        rows = await _fetch_scored(pool, season, league_code)
        scored, correct, baseline_home, ll_sum, _ = _aggregate(rows)
        if scored == 0:
            continue
        out.append(
            HistorySeason(
                season=season,
                scored=scored,
                correct=correct,
                accuracy=correct / scored,
                mean_log_loss=ll_sum / scored,
                baseline_home_accuracy=baseline_home / scored,
            )
        )
    _STATS_CACHE.set(("history", league_code), out)
    return out


class RoiLeagueOut(BaseModel):
    """Per-league ROI row for /api/stats/roi/by-league."""
    league_code: str
    bets: int
    wins: int
    pnl_vig: float
    pnl_nov: float
    roi_vig_pct: float
    roi_nov_pct: float
    mean_log_loss: float
    scored: int


class RoiByLeagueOut(BaseModel):
    window: str        # 'season' | '7d' | '30d' | '90d'
    threshold: float
    season: str | None # only set when window == 'season'
    leagues: list[RoiLeagueOut]


_ROI_WINDOWS = {"7d": 7, "30d": 30, "90d": 90}


@router.get("/roi/by-league", response_model=RoiByLeagueOut)
async def roi_by_league(
    request: Request,
    window: str = Query("season", pattern="^(season|7d|30d|90d)$"),
    season: str = Query("2025-26", description="Only used when window=season"),
    threshold: float = Query(0.05, ge=0.0, le=0.5),
) -> RoiByLeagueOut:
    """Per-league flat-stake ROI. Edge ≥ `threshold` on devigged market fair,
    PnL at best available price. Window is either the fixed season or a
    rolling N-day interval from now.
    """
    pool = request.app.state.pool
    cache_key = ("roi_by_league", window, season if window == "season" else None, threshold)
    cached = _STATS_CACHE.get(cache_key)
    if cached is not None:
        return cached

    async with pool.acquire() as conn:
        if window == "season":
            rows = await conn.fetch(_ROI_QUERY, season, None)
        else:
            rows = await conn.fetch(_ROI_QUERY_WINDOW, str(_ROI_WINDOWS[window]))

    leagues = _compute_roi_by_league(rows, threshold)
    out = RoiByLeagueOut(
        window=window,
        threshold=threshold,
        season=season if window == "season" else None,
        leagues=[RoiLeagueOut(**lg) for lg in leagues],
    )
    _STATS_CACHE.set(cache_key, out)
    return out


@router.get("/roi", response_model=RoiOut)
async def roi(
    request: Request,
    season: str = Query("2025-26"),
    threshold: float = Query(0.05, ge=0.0, le=0.5),
    league: str | None = Query(None),
) -> RoiOut:
    """Cumulative 1-unit flat-stake P&L across every ≥threshold edge bet."""
    from app.ingest.odds import fair_probs

    pool = request.app.state.pool
    league_code = _resolve_league_code(league)
    async with pool.acquire() as conn:
        rows = await conn.fetch(_ROI_QUERY, season, league_code)

    by_date: dict[date, dict[str, float]] = {}
    total_pnl = 0.0
    total_bets = 0
    for r in rows:
        probs = {"H": float(r["p_home_win"]), "D": float(r["p_draw"]), "A": float(r["p_away_win"])}
        # Edge is measured against the average / reference odds (devigged
        # market fair). A bettor would NOT get the average price — they
        # shop around and take the best quote available across books.
        avg_odds = {"H": r["odds_home"], "D": r["odds_draw"], "A": r["odds_away"]}
        best_odds = {"H": r["best_home"], "D": r["best_draw"], "A": r["best_away"]}
        fair = fair_probs(avg_odds["H"], avg_odds["D"], avg_odds["A"])
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
            pnl = (float(best_odds[side]) - 1.0) if side == outcome else -1.0
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
    league: str | None = Query(None),
) -> list[ScorerOut]:
    pool = request.app.state.pool
    league_code = _resolve_league_code(league)
    sort_col = {
        "goals": "p.goals DESC NULLS LAST, p.xg DESC NULLS LAST",
        "xg": "p.xg DESC NULLS LAST, p.goals DESC NULLS LAST",
        "assists": "p.assists DESC NULLS LAST, p.xa DESC NULLS LAST",
        "goals_minus_xg": "(p.goals::float - COALESCE(p.xg, 0)) DESC NULLS LAST",
    }[sort]
    query = f"""
    SELECT p.player_name, p.position, p.goals, p.xg, p.npxg, p.assists, p.xa,
           p.key_passes, p.games, p.photo_url,
           t.slug AS team_slug, t.name AS team_name, t.short_name AS team_short,
           (SELECT league_code FROM matches m
            WHERE (m.home_team_id = p.team_id OR m.away_team_id = p.team_id)
              AND m.season = $1
            LIMIT 1) AS league_code
    FROM player_season_stats p
    JOIN teams t ON t.id = p.team_id
    WHERE p.season = $1
      AND ($3::text IS NULL OR EXISTS (
          SELECT 1 FROM matches m
          WHERE (m.home_team_id = p.team_id OR m.away_team_id = p.team_id)
            AND m.season = $1
            AND m.league_code = $3
      ))
    ORDER BY {sort_col}
    LIMIT $2
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, season, limit, league_code)
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
                photo_url=r["photo_url"],
                league_code=r["league_code"],
            )
        )
    return out
