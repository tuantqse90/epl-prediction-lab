"""GET /api/matches — upcoming fixtures with latest prediction joined."""

from __future__ import annotations

import math

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app import queries
from app.core.cache import TTLCache
from app.schemas import MatchOut

router = APIRouter(prefix="/api/matches", tags=["matches"])

# Bootstrap CI is ~300ms; 10-min cache per match keeps UI snappy without
# going stale faster than the hourly predict cron could refresh it anyway.
_CI_CACHE = TTLCache(ttl_seconds=600)


class H2HMatch(BaseModel):
    match_id: int
    kickoff_date: str
    season: str
    league_code: str | None
    home_slug: str
    home_short: str
    home_goals: int
    away_slug: str
    away_short: str
    away_goals: int


class Injury(BaseModel):
    team_slug: str
    player_name: str
    reason: str | None
    status_label: str | None
    last_seen_at: str


class MatchInjuries(BaseModel):
    home: list[Injury]
    away: list[Injury]


class WeatherOut(BaseModel):
    temp_c: float | None
    wind_kmh: float | None
    precip_mm: float | None
    condition: str | None
    fetched_at: str | None


class HalfTimeOut(BaseModel):
    p_home_lead: float
    p_draw: float
    p_away_lead: float
    top_scorelines: list[tuple[int, int, float]]
    # HT/FT 9-cell grid flattened into an array of dicts for JSON friendliness.
    htft: list[dict]  # [{"ht": "H", "ft": "H", "p": 0.37}, ...]


class ConfidenceInterval(BaseModel):
    p_home_low: float
    p_home_high: float
    p_draw_low: float
    p_draw_high: float
    p_away_low: float
    p_away_high: float
    n_samples: int


class MarketsOut(BaseModel):
    prob_over_0_5: float
    prob_over_1_5: float
    prob_over_2_5: float
    prob_over_3_5: float
    prob_btts: float
    prob_home_clean_sheet: float
    prob_away_clean_sheet: float
    lam_home: float
    lam_away: float
    # Asian handicap (home-perspective; away = 1 − home).
    # Lines kept compact: the most-traded EU/Asian-book quotes.
    prob_ah_home_minus_1_5: float = 0.0
    prob_ah_home_minus_0_5: float = 0.0
    prob_ah_home_plus_0_5: float = 0.0
    prob_ah_home_plus_1_5: float = 0.0
    # Same-game parlay: the correlated bet books most often misprice.
    prob_sgp_btts_over_2_5: float = 0.0


class ScorerOdds(BaseModel):
    player_name: str
    team_slug: str
    team_short: str
    position: str | None
    season_xg: float
    season_games: int
    expected_goals: float    # xG contribution for this match
    p_anytime: float         # probability of scoring ≥ 1 goal


class TeamInjuryImpact(BaseModel):
    team_slug: str
    injured_xg_share: float        # fraction of team season xG currently out
    lambda_multiplier: float       # what we multiply pre-adjust λ by (≤ 1.0)
    top_absent: list[str]          # player names ordered by xG contribution


class InjuryImpact(BaseModel):
    home: TeamInjuryImpact
    away: TeamInjuryImpact


class LineupPlayer(BaseModel):
    player_name: str
    player_number: int | None
    position: str | None
    is_starting: bool


class TeamLineup(BaseModel):
    team_slug: str
    formation: str | None
    starting: list[LineupPlayer]
    bench: list[LineupPlayer]


class MatchLineups(BaseModel):
    home: TeamLineup | None
    away: TeamLineup | None


@router.get("", response_model=list[MatchOut])
async def list_matches(
    request: Request,
    upcoming_only: bool = Query(True, description="Only matches with kickoff in the future"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    league: str | None = Query(None, description="league slug or code (e.g. epl, laliga)"),
    tricky: bool = Query(False, description="Only matches where top-2 prob margin < 10pp"),
) -> list[MatchOut]:
    from app.leagues import get_league
    league_code = get_league(league).code if league else None
    rows = await queries.list_matches(
        request.app.state.pool,
        upcoming_only=upcoming_only,
        # Pull extra rows when filtering so the page still has `limit` after
        # the tricky filter trims them. 4x is a safe over-fetch factor.
        limit=(limit * 4) if tricky else limit,
        offset=offset,
        league_code=league_code,
    )
    out = [MatchOut.model_validate(queries.record_to_match_dict(r)) for r in rows]
    if tricky:
        out = [m for m in out if _is_tricky(m)]
        out = out[:limit]
    return out


def _is_tricky(m) -> bool:
    p = m.prediction
    if not p:
        return False
    probs = sorted([p.p_home_win, p.p_draw, p.p_away_win], reverse=True)
    return (probs[0] - probs[1]) < 0.10


@router.get("/{match_id}", response_model=MatchOut)
async def get_match(match_id: int, request: Request) -> MatchOut:
    pool = request.app.state.pool
    row = await queries.get_match(pool, match_id)
    if row is None:
        raise HTTPException(404, f"match {match_id} not found")
    data = queries.record_to_match_dict(row)
    data["events"] = await queries.get_match_events(pool, match_id)
    return MatchOut.model_validate(data)


@router.get("/{match_id}/story")
async def match_story(
    match_id: int,
    request: Request,
    lang: str = "vi",
) -> dict:
    """Phase 42.1 — long-form 400-500 word narrative for a finished match.

    `lang` selects the language: 'vi' (default) reads matches.story
    directly; 'en'/'th'/'zh'/'ko' reads from match_story_translations
    (populated by the daily translate_stories cron). Falls back to VI
    if the translation hasn't been generated yet.

    Returns `{story, model, generated_at, lang}` or 404 if no story
    in any language.
    """
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        base = await conn.fetchrow(
            "SELECT story, story_model, story_generated_at "
            "FROM matches WHERE id = $1",
            match_id,
        )
        if base is None or not base["story"]:
            raise HTTPException(404, "story not available for this match")
        served_lang = "vi"
        story = base["story"]
        if lang in ("en", "th", "zh", "ko"):
            tr = await conn.fetchrow(
                "SELECT story, model, translated_at "
                "FROM match_story_translations "
                "WHERE match_id = $1 AND lang = $2",
                match_id, lang,
            )
            if tr:
                served_lang = lang
                story = tr["story"]
    return {
        "story": story,
        "lang": served_lang,
        "model": base["story_model"],
        "generated_at": (
            base["story_generated_at"].isoformat()
            if base["story_generated_at"] else None
        ),
    }


@router.get("/{match_id}/h2h", response_model=list[H2HMatch])
async def match_h2h(
    match_id: int,
    request: Request,
    limit: int = Query(5, ge=1, le=20),
) -> list[H2HMatch]:
    """Last N completed meetings between the two teams (any league, any season)."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        pair = await conn.fetchrow(
            """
            SELECT ht.name AS home_name, at.name AS away_name, m.kickoff_time
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.id = $1
            """,
            match_id,
        )
        if pair is None:
            raise HTTPException(404, f"match {match_id} not found")

        rows = await conn.fetch(
            """
            SELECT m.id AS match_id, m.kickoff_time, m.season, m.league_code,
                   m.home_goals, m.away_goals,
                   ht.slug AS home_slug, ht.short_name AS home_short,
                   at.slug AS away_slug, at.short_name AS away_short
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.status = 'final'
              AND m.kickoff_time < $3
              AND m.home_goals IS NOT NULL
              AND (
                (ht.name = $1 AND at.name = $2)
                OR (ht.name = $2 AND at.name = $1)
              )
            ORDER BY m.kickoff_time DESC
            LIMIT $4
            """,
            pair["home_name"], pair["away_name"], pair["kickoff_time"], limit,
        )
    return [
        H2HMatch(
            match_id=r["match_id"],
            kickoff_date=r["kickoff_time"].date().isoformat(),
            season=r["season"],
            league_code=r["league_code"],
            home_slug=r["home_slug"],
            home_short=r["home_short"],
            home_goals=int(r["home_goals"]),
            away_slug=r["away_slug"],
            away_short=r["away_short"],
            away_goals=int(r["away_goals"]),
        )
        for r in rows
    ]


@router.get("/{match_id}/injuries", response_model=MatchInjuries)
async def match_injuries(match_id: int, request: Request) -> MatchInjuries:
    """Currently-reported absentees on each side (cached from API-Football)."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        pair = await conn.fetchrow(
            """
            SELECT ht.slug AS home_slug, at.slug AS away_slug, m.season
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.id = $1
            """,
            match_id,
        )
        if pair is None:
            raise HTTPException(404, f"match {match_id} not found")

        # API-Football /injuries returns every "Missing Fixture" event for
        # the season — most are historical. Status_label ∈ {'Missing Fixture',
        # 'Questionable'}. Only the latter is forward-looking; the former is a
        # past-absence record. We dedupe historical noise by selecting only
        # the most-recent row per player.
        rows = await conn.fetch(
            """
            SELECT DISTINCT ON (team_slug, player_name)
                   team_slug, player_name, reason, status_label, last_seen_at
            FROM player_injuries
            WHERE team_slug = ANY($1::text[])
              AND season = $2
              AND last_seen_at >= NOW() - INTERVAL '3 days'
              AND status_label <> 'Missing Fixture'
            ORDER BY team_slug, player_name, last_seen_at DESC
            """,
            [pair["home_slug"], pair["away_slug"]],
            pair["season"],
        )

    home_list: list[Injury] = []
    away_list: list[Injury] = []
    for r in rows:
        item = Injury(
            team_slug=r["team_slug"],
            player_name=r["player_name"],
            reason=r["reason"],
            status_label=r["status_label"],
            last_seen_at=r["last_seen_at"].isoformat(),
        )
        if r["team_slug"] == pair["home_slug"]:
            home_list.append(item)
        else:
            away_list.append(item)
    return MatchInjuries(home=home_list, away=away_list)


@router.get("/{match_id}/lineups", response_model=MatchLineups)
async def match_lineups(match_id: int, request: Request) -> MatchLineups:
    """Starting XI + bench per team (populated ~60min before kickoff)."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        pair = await conn.fetchrow(
            """
            SELECT ht.slug AS home_slug, at.slug AS away_slug
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.id = $1
            """,
            match_id,
        )
        if pair is None:
            raise HTTPException(404, f"match {match_id} not found")

        rows = await conn.fetch(
            """
            SELECT team_slug, player_name, player_number, position,
                   is_starting, formation
            FROM match_lineups
            WHERE match_id = $1
            ORDER BY team_slug, is_starting DESC, player_number NULLS LAST
            """,
            match_id,
        )

    def _build(team_slug: str) -> TeamLineup | None:
        subset = [r for r in rows if r["team_slug"] == team_slug]
        if not subset:
            return None
        formation = next((r["formation"] for r in subset if r["formation"]), None)
        starting = [
            LineupPlayer(
                player_name=r["player_name"],
                player_number=r["player_number"],
                position=r["position"],
                is_starting=True,
            )
            for r in subset if r["is_starting"]
        ]
        bench = [
            LineupPlayer(
                player_name=r["player_name"],
                player_number=r["player_number"],
                position=r["position"],
                is_starting=False,
            )
            for r in subset if not r["is_starting"]
        ]
        return TeamLineup(
            team_slug=team_slug, formation=formation, starting=starting, bench=bench,
        )

    return MatchLineups(home=_build(pair["home_slug"]), away=_build(pair["away_slug"]))


async def _compute_ci(
    pool, match_id: int,
) -> "ConfidenceInterval | None":
    """Shared bootstrap-CI calc used by both the HTTP endpoint and the
    post-predict warmup. Writes into _CI_CACHE on success so subsequent
    reads return instantly."""
    import pandas as pd
    from app import queries as _queries
    from app.models.ci import bootstrap_1x2_ci as _boot

    cached = _CI_CACHE.get(("ci", match_id))
    if cached is not None:
        return cached

    match = await _queries.get_match(pool, match_id)
    if match is None:
        return None

    league_code = match["league_code"] or None
    df = await _queries.fetch_finished_matches_df(pool, league_code=league_code)
    if df.empty:
        return None
    league_avg = float(pd.concat([df["home_goals"], df["away_goals"]]).mean())

    ci_raw = _boot(
        df,
        match["home_name"], match["away_name"],
        as_of=match["kickoff_time"],
        league_avg_goals=league_avg,
        rho=-0.15,
        n_samples=15, last_n=12, temperature=1.35,
        seed=match_id,
    )
    if ci_raw.n_samples == 0:
        return None
    out = ConfidenceInterval(
        p_home_low=round(ci_raw.p_home_low, 4),
        p_home_high=round(ci_raw.p_home_high, 4),
        p_draw_low=round(ci_raw.p_draw_low, 4),
        p_draw_high=round(ci_raw.p_draw_high, 4),
        p_away_low=round(ci_raw.p_away_low, 4),
        p_away_high=round(ci_raw.p_away_high, 4),
        n_samples=ci_raw.n_samples,
    )
    _CI_CACHE.set(("ci", match_id), out)
    return out


@router.get("/{match_id}/ci", response_model=ConfidenceInterval | None)
async def match_ci(match_id: int, request: Request) -> ConfidenceInterval | None:
    """1-sigma bootstrap CI on (p_home, p_draw, p_away). 10-min cache.

    Cold-path triggers on first hit; pre-warmed from predict/service after
    every new prediction so real users rarely hit cold.
    """
    pool = request.app.state.pool
    out = await _compute_ci(pool, match_id)
    if out is None:
        raise HTTPException(404, f"CI unavailable for match {match_id}")
    return out


@router.get("/{match_id}/halftime", response_model=HalfTimeOut | None)
async def match_halftime(match_id: int, request: Request) -> HalfTimeOut | None:
    """Half-time winner + HT correct-score + HT/FT 9-grid from latest prediction."""
    from app.models.half_time import halftime_correct_score_top, ht_winner_probs, htft_grid

    pool = request.app.state.pool
    row = await pool.fetchrow(
        """
        SELECT expected_home_goals, expected_away_goals
        FROM predictions
        WHERE match_id = $1
        ORDER BY created_at DESC LIMIT 1
        """,
        match_id,
    )
    if row is None or row["expected_home_goals"] is None:
        return None
    lam_h = float(row["expected_home_goals"])
    lam_a = float(row["expected_away_goals"])

    w = ht_winner_probs(lam_h, lam_a)
    top = halftime_correct_score_top(lam_h, lam_a, n=3)
    grid = htft_grid(lam_h, lam_a)
    htft_list = [
        {"ht": ht, "ft": ft, "p": round(p, 4)}
        for (ht, ft), p in sorted(grid.cells.items(), key=lambda kv: kv[1], reverse=True)
    ]
    return HalfTimeOut(
        p_home_lead=w.p_home_lead,
        p_draw=w.p_draw,
        p_away_lead=w.p_away_lead,
        top_scorelines=[(h, a, round(p, 4)) for h, a, p in top],
        htft=htft_list,
    )


@router.get("/{match_id}/markets", response_model=MarketsOut | None)
async def match_markets(match_id: int, request: Request) -> MarketsOut | None:
    """Derived O/U + BTTS + clean-sheet probabilities from the latest prediction.

    Reuses the pre-computed λ stored in predictions to rebuild the scoreline
    matrix — no DB re-ingest, ~0.5ms per call.
    """
    from app.models.markets import (
        markets_from_matrix,
        prob_asian_handicap,
        prob_sgp_btts_and_over,
    )
    from app.models.poisson import apply_dixon_coles, poisson_score_matrix

    pool = request.app.state.pool
    row = await pool.fetchrow(
        """
        SELECT p.expected_home_goals, p.expected_away_goals
        FROM predictions p
        WHERE p.match_id = $1
        ORDER BY p.created_at DESC
        LIMIT 1
        """,
        match_id,
    )
    if row is None or row["expected_home_goals"] is None:
        return None
    lam_h = float(row["expected_home_goals"])
    lam_a = float(row["expected_away_goals"])
    rho = -0.15  # matches the value used in predict_upcoming; stable across runs
    base = poisson_score_matrix(lam_h, lam_a, max_goals=5)
    adjusted = apply_dixon_coles(base, lam_h, lam_a, rho)
    m = markets_from_matrix(adjusted)
    return MarketsOut(
        prob_over_0_5=m.prob_over_0_5,
        prob_over_1_5=m.prob_over_1_5,
        prob_over_2_5=m.prob_over_2_5,
        prob_over_3_5=m.prob_over_3_5,
        prob_btts=m.prob_btts,
        prob_home_clean_sheet=m.prob_home_clean_sheet,
        prob_away_clean_sheet=m.prob_away_clean_sheet,
        lam_home=lam_h,
        lam_away=lam_a,
        prob_ah_home_minus_1_5=prob_asian_handicap(adjusted, -1.5, "home"),
        prob_ah_home_minus_0_5=prob_asian_handicap(adjusted, -0.5, "home"),
        prob_ah_home_plus_0_5=prob_asian_handicap(adjusted, +0.5, "home"),
        prob_ah_home_plus_1_5=prob_asian_handicap(adjusted, +1.5, "home"),
        prob_sgp_btts_over_2_5=prob_sgp_btts_and_over(adjusted, 2.5),
    )


class MarketEdgeRow(BaseModel):
    key: str                     # 'over_2_5', 'btts_yes', 'ah_home_minus_0_5', …
    label: str                   # 'Over 2.5', 'BTTS Yes', 'AH Home -0.5'
    market_code: str             # 'OU' | 'BTTS' | 'AH'
    line: float | None
    outcome_code: str
    model_prob: float
    fair_odds: float
    best_book_odds: float | None = None
    best_source: str | None = None
    edge_pp: float | None = None
    flagged: bool = False
    # Sharp-consensus reference: devigged probability from Pinnacle (lowest
    # retail vig, ~2%) for the same outcome. When our model disagrees with
    # Pinnacle by more than `sharp_disagreement_pp`, it's worth second-
    # guessing the pick.
    pinnacle_prob: float | None = None
    sharp_disagreement_pp: float | None = None


class MarketsEdgeOut(BaseModel):
    match_id: int
    edge_threshold_pp: float
    rows: list[MarketEdgeRow]


# (key, market_code, line, outcome_code) — the single source of truth for
# which markets we price and how they map to stored book-odds rows.
_MARKET_KEYS = [
    ("over_2_5",            "OU",   2.5,   "OVER",  "Over 2.5"),
    ("under_2_5",           "OU",   2.5,   "UNDER", "Under 2.5"),
    ("over_1_5",            "OU",   1.5,   "OVER",  "Over 1.5"),
    ("over_3_5",            "OU",   3.5,   "OVER",  "Over 3.5"),
    ("btts_yes",            "BTTS", None,  "YES",   "BTTS Yes"),
    ("btts_no",             "BTTS", None,  "NO",    "BTTS No"),
    ("ah_home_minus_1_5",   "AH",   -1.5,  "HOME",  "AH Home -1.5"),
    ("ah_home_minus_0_5",   "AH",   -0.5,  "HOME",  "AH Home -0.5"),
    ("ah_home_plus_0_5",    "AH",   +0.5,  "HOME",  "AH Home +0.5"),
    ("ah_home_plus_1_5",    "AH",   +1.5,  "HOME",  "AH Home +1.5"),
]


def _build_market_edge_rows(
    *, probs: dict, book_rows, edge_threshold_pp: float = 5.0,
) -> list[dict]:
    """Join model market probs with stored book odds, emit per-outcome rows.

    Best book odds = MAX across per-bookmaker sources (highest price for
    the bettor). `source LIKE 'odds-api:%'` filters out pooled-average rows
    so we only compare against real quotes. If no book row matches, the
    row still comes back with fair_odds and None for book/edge — the UI
    then falls back to the manual-comparison view.
    """
    def _get(r, key):
        # asyncpg.Record: subscript OK, attr NOT. SimpleNamespace: attr OK.
        # Plain dict: .get. Try them in that order.
        if isinstance(r, dict):
            return r.get(key)
        try:
            return r[key]
        except (KeyError, TypeError):
            return getattr(r, key, None)

    by_key: dict[tuple[str, float | None, str], list] = {}
    # Pinnacle-only index for devig → sharp reference probability. Grouped
    # by (market, line) so we can pair H/A outcomes for OU/BTTS/AH devig.
    pinnacle_by_family: dict[tuple[str, float | None], dict[str, float]] = {}
    for r in book_rows:
        src = _get(r, "source") or ""
        if src.endswith(":avg"):
            continue  # pooled avg excluded — best-odds shopping uses real books
        if not (src.startswith("odds-api:") or src.startswith("af:")):
            continue
        k = (_get(r, "market_code"), _get(r, "line"), _get(r, "outcome_code"))
        by_key.setdefault(k, []).append(r)

        # Separately index Pinnacle (sharp) rows by market family.
        if src == "af:Pinnacle":
            fam = (_get(r, "market_code"), _get(r, "line"))
            pinnacle_by_family.setdefault(fam, {})[_get(r, "outcome_code")] = float(_get(r, "odds"))

    # Devig each Pinnacle family: raw implied = 1/odds each outcome; divide
    # by sum → probabilities sum to 1 after overround is removed. Handles
    # 2-way (OU/BTTS) and 3-way (1X2) uniformly.
    pinnacle_probs: dict[tuple[str, float | None, str], float] = {}
    for (market, line), outcomes in pinnacle_by_family.items():
        if not outcomes:
            continue
        implied = {o: 1.0 / v for o, v in outcomes.items() if v > 0}
        s = sum(implied.values())
        if s <= 0:
            continue
        for o, p in implied.items():
            pinnacle_probs[(market, line, o)] = p / s

    out: list[dict] = []
    for key, market, line, outcome, label in _MARKET_KEYS:
        prob = probs.get(key)
        if prob is None or prob <= 0.0:
            continue
        row = {
            "key": key,
            "label": label,
            "market_code": market,
            "line": line,
            "outcome_code": outcome,
            "model_prob": round(float(prob), 4),
            "fair_odds": round(1.0 / float(prob), 3),
            "best_book_odds": None,
            "best_source": None,
            "edge_pp": None,
            "flagged": False,
            "pinnacle_prob": None,
            "sharp_disagreement_pp": None,
        }
        matches = by_key.get((market, line, outcome)) or []
        if matches:
            best = max(matches, key=lambda r: float(_get(r, "odds")))
            best_odds = float(_get(best, "odds"))
            edge_pp = (float(prob) * best_odds - 1.0) * 100.0
            row["best_book_odds"] = round(best_odds, 3)
            row["best_source"] = _get(best, "source")
            row["edge_pp"] = round(edge_pp, 2)
            row["flagged"] = edge_pp >= edge_threshold_pp

        pinnacle_p = pinnacle_probs.get((market, line, outcome))
        if pinnacle_p is not None:
            row["pinnacle_prob"] = round(pinnacle_p, 4)
            row["sharp_disagreement_pp"] = round((float(prob) - pinnacle_p) * 100.0, 2)

        out.append(row)
    return out


@router.get("/{match_id}/markets-edge", response_model=MarketsEdgeOut)
async def match_markets_edge(
    match_id: int,
    request: Request,
    threshold_pp: float = Query(5.0, ge=0.0, le=50.0),
) -> MarketsEdgeOut:
    """Per-outcome edge table joining derived-market model probs with stored
    book odds. Neon-highlighted rows on the FE when edge_pp ≥ threshold_pp."""
    from app.models.markets import (
        markets_from_matrix,
        prob_asian_handicap,
        prob_sgp_btts_and_over,
    )
    from app.models.poisson import apply_dixon_coles, poisson_score_matrix

    pool = request.app.state.pool
    async with pool.acquire() as conn:
        pred = await conn.fetchrow(
            """
            SELECT expected_home_goals, expected_away_goals
            FROM predictions WHERE match_id = $1
            ORDER BY created_at DESC LIMIT 1
            """,
            match_id,
        )
        if pred is None or pred["expected_home_goals"] is None:
            return MarketsEdgeOut(match_id=match_id, edge_threshold_pp=threshold_pp, rows=[])
        book_rows = await conn.fetch(
            """
            SELECT source, market_code, line, outcome_code, odds
            FROM match_odds_markets
            WHERE match_id = $1
            """,
            match_id,
        )

    lam_h = float(pred["expected_home_goals"])
    lam_a = float(pred["expected_away_goals"])
    rho = -0.15
    base = poisson_score_matrix(lam_h, lam_a, max_goals=5)
    adjusted = apply_dixon_coles(base, lam_h, lam_a, rho)
    m = markets_from_matrix(adjusted)

    probs = {
        "over_2_5":          m.prob_over_2_5,
        "under_2_5":         1.0 - m.prob_over_2_5,
        "over_1_5":          m.prob_over_1_5,
        "over_3_5":          m.prob_over_3_5,
        "btts_yes":          m.prob_btts,
        "btts_no":           1.0 - m.prob_btts,
        "ah_home_minus_1_5": prob_asian_handicap(adjusted, -1.5, "home"),
        "ah_home_minus_0_5": prob_asian_handicap(adjusted, -0.5, "home"),
        "ah_home_plus_0_5":  prob_asian_handicap(adjusted, +0.5, "home"),
        "ah_home_plus_1_5":  prob_asian_handicap(adjusted, +1.5, "home"),
    }

    rows = _build_market_edge_rows(probs=probs, book_rows=book_rows, edge_threshold_pp=threshold_pp)
    return MarketsEdgeOut(
        match_id=match_id,
        edge_threshold_pp=threshold_pp,
        rows=[MarketEdgeRow(**r) for r in rows],
    )


class LineupStrength(BaseModel):
    home_multiplier: float
    away_multiplier: float
    home_covered: bool          # True = has confirmed starting XI
    away_covered: bool


@router.get("/{match_id}/lineup-strength", response_model=LineupStrength | None)
async def match_lineup_strength(match_id: int, request: Request) -> LineupStrength | None:
    """Lineup-sum xG multiplier per side. Shows a "lineup-adjusted" chip on
    `/match/:id` when either team has a confirmed starting XI."""
    from app.predict.service import _lineup_multiplier

    pool = request.app.state.pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT home_team_id, away_team_id, season FROM matches WHERE id = $1",
            match_id,
        )
        if row is None:
            return None
        covered_home = await conn.fetchval(
            "SELECT COUNT(*) >= 11 FROM match_lineups ml "
            "WHERE ml.match_id = $1 AND ml.is_starting "
            "AND ml.team_slug = (SELECT slug FROM teams WHERE id = $2)",
            match_id, row["home_team_id"],
        )
        covered_away = await conn.fetchval(
            "SELECT COUNT(*) >= 11 FROM match_lineups ml "
            "WHERE ml.match_id = $1 AND ml.is_starting "
            "AND ml.team_slug = (SELECT slug FROM teams WHERE id = $2)",
            match_id, row["away_team_id"],
        )
        mh = await _lineup_multiplier(conn, row["home_team_id"], row["season"], match_id)
        ma = await _lineup_multiplier(conn, row["away_team_id"], row["season"], match_id)

    return LineupStrength(
        home_multiplier=round(mh, 4),
        away_multiplier=round(ma, 4),
        home_covered=bool(covered_home),
        away_covered=bool(covered_away),
    )


class FatigueContext(BaseModel):
    rest_days_home: int
    rest_days_away: int
    rest_diff: int
    congestion_home: int
    congestion_away: int
    is_midweek: bool


class DerbyInfo(BaseModel):
    name: str
    description: str
    variance_multiplier: float


@router.get("/{match_id}/derby", response_model=DerbyInfo | None)
async def match_derby(match_id: int, request: Request) -> DerbyInfo | None:
    """Null unless the fixture is a known rivalry pair."""
    from app.models.derbies import derby_tag

    pool = request.app.state.pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT ht.slug AS home_slug, at.slug AS away_slug
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.id = $1
            """,
            match_id,
        )
    if not row:
        return None
    tag = derby_tag(row["home_slug"], row["away_slug"])
    if not tag:
        return None
    return DerbyInfo(
        name=tag.name,
        description=tag.description,
        variance_multiplier=tag.variance_multiplier,
    )


@router.get("/{match_id}/fatigue", response_model=FatigueContext | None)
async def match_fatigue(match_id: int, request: Request) -> FatigueContext | None:
    """Rest + 14-day congestion + midweek flag. Displayed as a chip on
    /match/:id so users can weight predictions for tired teams."""
    from app.models.fatigue import compute_fixture_context

    pool = request.app.state.pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT ht.name AS home_name, at.name AS away_name, m.kickoff_time,
                   m.league_code
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.id = $1
            """,
            match_id,
        )
        if row is None:
            return None
        prior = await conn.fetch(
            """
            SELECT m.kickoff_time AS date, ht.name AS home_team, at.name AS away_team
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.league_code = $1
              AND m.kickoff_time < $2
              AND m.kickoff_time >= $2 - INTERVAL '30 days'
            """,
            row["league_code"], row["kickoff_time"],
        )

    import pandas as pd
    df = pd.DataFrame(
        [(r["date"], r["home_team"], r["away_team"]) for r in prior],
        columns=["date", "home_team", "away_team"],
    )
    # Ensure pandas-native Timestamp comparisons (asyncpg returns aware datetimes).
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    kickoff = pd.to_datetime(row["kickoff_time"])
    ctx = compute_fixture_context(df, home=row["home_name"], away=row["away_name"], kickoff=kickoff)
    return FatigueContext(
        rest_days_home=ctx.rest_days_home,
        rest_days_away=ctx.rest_days_away,
        rest_diff=ctx.rest_diff,
        congestion_home=ctx.congestion_home,
        congestion_away=ctx.congestion_away,
        is_midweek=ctx.is_midweek,
    )


class RefereeInfo(BaseModel):
    name: str
    n: int
    goals_delta: float      # goals/match above/below the rolling 2-season league avg
    league_avg: float
    multiplier: float       # applied to both teams' λ; clamped to ±10%


@router.get("/{match_id}/referee", response_model=RefereeInfo | None)
async def match_referee(match_id: int, request: Request) -> RefereeInfo | None:
    """Per-match referee tendency. Returns None when no ref assigned or
    the ref has < 30 matches in the rolling 2-season window."""
    from app.models.referee import referee_multiplier, referee_tendencies

    pool = request.app.state.pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT referee, league_code, kickoff_time FROM matches WHERE id = $1",
            match_id,
        )
        if row is None or not row["referee"] or not row["league_code"]:
            return None
        sample = await conn.fetch(
            """
            SELECT referee, home_goals, away_goals
            FROM matches
            WHERE league_code = $1
              AND status = 'final'
              AND home_goals IS NOT NULL
              AND referee IS NOT NULL
              AND kickoff_time < $2
              AND kickoff_time >= $2 - INTERVAL '730 days'
              AND id <> $3
            """,
            row["league_code"], row["kickoff_time"], match_id,
        )
    if not sample:
        return None
    tendencies = referee_tendencies(sample, min_matches=30)
    info = tendencies.get(row["referee"])
    if info is None:
        return None
    totals = [int(r["home_goals"]) + int(r["away_goals"]) for r in sample]
    league_avg = sum(totals) / len(totals) if totals else 2.8
    m = referee_multiplier(info["goals_delta"], league_avg=league_avg, cap=0.10)
    return RefereeInfo(
        name=row["referee"],
        n=info["n"],
        goals_delta=round(info["goals_delta"], 3),
        league_avg=round(league_avg, 3),
        multiplier=round(m, 4),
    )


@router.get("/{match_id}/weather", response_model=WeatherOut | None)
async def match_weather(match_id: int, request: Request) -> WeatherOut | None:
    pool = request.app.state.pool
    row = await pool.fetchrow(
        "SELECT temp_c, wind_kmh, precip_mm, condition, fetched_at "
        "FROM match_weather WHERE match_id = $1",
        match_id,
    )
    if row is None:
        return None
    return WeatherOut(
        temp_c=row["temp_c"],
        wind_kmh=row["wind_kmh"],
        precip_mm=row["precip_mm"],
        condition=row["condition"],
        fetched_at=row["fetched_at"].isoformat() if row["fetched_at"] else None,
    )


@router.get("/{match_id}/injury-impact", response_model=InjuryImpact)
async def match_injury_impact(match_id: int, request: Request) -> InjuryImpact:
    """Per-team injury-adjusted λ multiplier + top absentees by season xG.

    Mirrors the INJURY_ALPHA shrink applied in predict/service so the FE
    can explain the model's move: "λ_home = 1.5 × 0.86 = 1.29 (Salah, Saka out)".
    """
    from app.predict.service import INJURY_ALPHA, _injury_impact

    pool = request.app.state.pool
    async with pool.acquire() as conn:
        pair = await conn.fetchrow(
            """
            SELECT m.season,
                   ht.id AS home_id, ht.slug AS home_slug,
                   at.id AS away_id, at.slug AS away_slug
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.id = $1
            """,
            match_id,
        )
        if pair is None:
            raise HTTPException(404, f"match {match_id} not found")

        async def _team(team_id: int, team_slug: str) -> TeamInjuryImpact:
            share = await _injury_impact(conn, team_id, pair["season"], match_id)
            multiplier = max(0.5, 1.0 - INJURY_ALPHA * share)
            absent = await conn.fetch(
                """
                SELECT p.player_name, p.xg
                FROM player_injuries pi
                JOIN teams t ON t.id = $1 AND pi.team_slug = t.slug
                JOIN player_season_stats p
                     ON p.team_id = t.id
                    AND p.season = $2
                    AND p.player_name = pi.player_name
                WHERE pi.season = $2
                  AND pi.last_seen_at >= NOW() - INTERVAL '3 days'
                  AND pi.status_label <> 'Missing Fixture'
                ORDER BY p.xg DESC NULLS LAST
                LIMIT 5
                """,
                team_id, pair["season"],
            )
            return TeamInjuryImpact(
                team_slug=team_slug,
                injured_xg_share=round(share, 4),
                lambda_multiplier=round(multiplier, 4),
                top_absent=[r["player_name"] for r in absent],
            )

        home = await _team(pair["home_id"], pair["home_slug"])
        away = await _team(pair["away_id"], pair["away_slug"])
    return InjuryImpact(home=home, away=away)


@router.get("/{match_id}/scorers", response_model=list[ScorerOdds])
async def match_scorers(
    match_id: int,
    request: Request,
    limit: int = Query(12, ge=1, le=30),
) -> list[ScorerOdds]:
    """Per-player anytime-goalscorer probability for this match.

    Formula: each player's share of their team's season xG is scaled by the
    team's expected goals for this match (from the latest prediction).
    Assumes player participates — for pre-team-sheet matches this is still
    a useful ranking of who's most likely to score if on the pitch.
    """
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        match_row = await conn.fetchrow(
            """
            SELECT m.id, m.season,
                   ht.id AS home_team_id, ht.slug AS home_slug, ht.short_name AS home_short,
                   at.id AS away_team_id, at.slug AS away_slug, at.short_name AS away_short,
                   p.expected_home_goals, p.expected_away_goals
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            LEFT JOIN LATERAL (
                SELECT expected_home_goals, expected_away_goals
                FROM predictions
                WHERE match_id = m.id
                ORDER BY created_at DESC
                LIMIT 1
            ) p ON TRUE
            WHERE m.id = $1
            """,
            match_id,
        )
        if match_row is None:
            raise HTTPException(404, f"match {match_id} not found")
        if match_row["expected_home_goals"] is None:
            return []

        players = await conn.fetch(
            """
            SELECT p.player_name, p.position, p.xg, p.games, p.goals,
                   t.id AS team_id, t.slug AS team_slug, t.short_name AS team_short
            FROM player_season_stats p
            JOIN teams t ON t.id = p.team_id
            WHERE p.season = $1
              AND t.id = ANY($2::int[])
              AND p.xg IS NOT NULL
              AND p.games IS NOT NULL
              AND p.games > 0
            """,
            match_row["season"],
            [match_row["home_team_id"], match_row["away_team_id"]],
        )

    # Aggregate per-team total xG to compute each player's share.
    by_team: dict[int, float] = {}
    for p in players:
        by_team[p["team_id"]] = by_team.get(p["team_id"], 0.0) + float(p["xg"] or 0)

    lam_home = float(match_row["expected_home_goals"])
    lam_away = float(match_row["expected_away_goals"])

    out: list[ScorerOdds] = []
    for p in players:
        team_total = by_team.get(p["team_id"], 0.0)
        if team_total <= 0:
            continue
        team_lambda = lam_home if p["team_id"] == match_row["home_team_id"] else lam_away
        share = float(p["xg"] or 0) / team_total
        match_xg = share * team_lambda
        if match_xg <= 0:
            continue
        p_any = 1.0 - math.exp(-match_xg)
        out.append(
            ScorerOdds(
                player_name=p["player_name"],
                team_slug=p["team_slug"],
                team_short=p["team_short"],
                position=p["position"],
                season_xg=round(float(p["xg"] or 0), 2),
                season_games=int(p["games"] or 0),
                expected_goals=round(match_xg, 3),
                p_anytime=round(p_any, 4),
            )
        )

    out.sort(key=lambda s: s.p_anytime, reverse=True)
    return out[:limit]


class OddsBookRow(BaseModel):
    book: str                 # lowercase key e.g. "bet365", "pinnacle"
    odds_home: float
    odds_draw: float
    odds_away: float
    fair_home: float          # probability derived by devig
    fair_draw: float
    fair_away: float
    edge_home: float | None = None   # model_prob − fair_prob, per outcome
    edge_draw: float | None = None
    edge_away: float | None = None
    captured_at: str


class OddsComparisonOut(BaseModel):
    match_id: int
    updated_at: str | None
    books: list[OddsBookRow]
    best_home_book: str | None        # which book offers the highest home price
    best_home_odds: float | None
    best_draw_book: str | None
    best_draw_odds: float | None
    best_away_book: str | None
    best_away_odds: float | None


@router.get("/{match_id}/odds-comparison", response_model=OddsComparisonOut)
async def match_odds_comparison(match_id: int, request: Request) -> OddsComparisonOut:
    """Per-bookmaker 1X2 odds comparison. Picks the best price per outcome
    across every book in our DB for this match, and surfaces each book's
    devigged fair probs + edge vs the model."""
    from app.ingest.odds import fair_probs

    pool = request.app.state.pool
    async with pool.acquire() as conn:
        books = await conn.fetch(
            """
            SELECT source, odds_home, odds_draw, odds_away, captured_at
            FROM match_odds
            WHERE match_id = $1
              AND source LIKE 'odds-api:%'
            ORDER BY source
            """,
            match_id,
        )
        pred = await conn.fetchrow(
            """
            SELECT p_home_win, p_draw, p_away_win
            FROM predictions WHERE match_id = $1
            ORDER BY created_at DESC LIMIT 1
            """,
            match_id,
        )

    rows: list[OddsBookRow] = []
    best_home_book = best_draw_book = best_away_book = None
    best_home_odds = best_draw_odds = best_away_odds = 0.0
    latest_capture: str | None = None

    for b in books:
        fair = fair_probs(b["odds_home"], b["odds_draw"], b["odds_away"])
        if fair is None:
            continue
        fh, fd, fa = fair
        eh = (pred["p_home_win"] - fh) if pred else None
        ed = (pred["p_draw"] - fd) if pred else None
        ea = (pred["p_away_win"] - fa) if pred else None
        book_key = b["source"].removeprefix("odds-api:")
        cap = b["captured_at"].isoformat() if b["captured_at"] else ""
        if latest_capture is None or (cap and cap > latest_capture):
            latest_capture = cap

        rows.append(OddsBookRow(
            book=book_key,
            odds_home=float(b["odds_home"]), odds_draw=float(b["odds_draw"]), odds_away=float(b["odds_away"]),
            fair_home=fh, fair_draw=fd, fair_away=fa,
            edge_home=eh, edge_draw=ed, edge_away=ea,
            captured_at=cap,
        ))

        if b["odds_home"] > best_home_odds:
            best_home_odds, best_home_book = float(b["odds_home"]), book_key
        if b["odds_draw"] > best_draw_odds:
            best_draw_odds, best_draw_book = float(b["odds_draw"]), book_key
        if b["odds_away"] > best_away_odds:
            best_away_odds, best_away_book = float(b["odds_away"]), book_key

    # Sort books by descending model edge on whichever outcome the model
    # picked — highest-edge book first. If no prediction, alphabetical.
    if pred and rows:
        model_pick = max(
            [("home", pred["p_home_win"]), ("draw", pred["p_draw"]), ("away", pred["p_away_win"])],
            key=lambda t: t[1],
        )[0]
        edge_attr = {"home": "edge_home", "draw": "edge_draw", "away": "edge_away"}[model_pick]
        rows.sort(key=lambda r: getattr(r, edge_attr) or -1, reverse=True)

    return OddsComparisonOut(
        match_id=match_id,
        updated_at=latest_capture,
        books=rows,
        best_home_book=best_home_book, best_home_odds=best_home_odds or None,
        best_draw_book=best_draw_book, best_draw_odds=best_draw_odds or None,
        best_away_book=best_away_book, best_away_odds=best_away_odds or None,
    )
