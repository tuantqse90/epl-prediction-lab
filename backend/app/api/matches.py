"""GET /api/matches — upcoming fixtures with latest prediction joined."""

from __future__ import annotations

import math

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app import queries
from app.schemas import MatchOut

router = APIRouter(prefix="/api/matches", tags=["matches"])


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
    league: str | None = Query(None, description="league slug or code (e.g. epl, laliga)"),
) -> list[MatchOut]:
    from app.leagues import get_league
    league_code = get_league(league).code if league else None
    rows = await queries.list_matches(
        request.app.state.pool,
        upcoming_only=upcoming_only,
        limit=limit,
        league_code=league_code,
    )
    return [MatchOut.model_validate(queries.record_to_match_dict(r)) for r in rows]


@router.get("/{match_id}", response_model=MatchOut)
async def get_match(match_id: int, request: Request) -> MatchOut:
    pool = request.app.state.pool
    row = await queries.get_match(pool, match_id)
    if row is None:
        raise HTTPException(404, f"match {match_id} not found")
    data = queries.record_to_match_dict(row)
    data["events"] = await queries.get_match_events(pool, match_id)
    return MatchOut.model_validate(data)


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


@router.get("/{match_id}/markets", response_model=MarketsOut | None)
async def match_markets(match_id: int, request: Request) -> MarketsOut | None:
    """Derived O/U + BTTS + clean-sheet probabilities from the latest prediction.

    Reuses the pre-computed λ stored in predictions to rebuild the scoreline
    matrix — no DB re-ingest, ~0.5ms per call.
    """
    from app.models.markets import markets_from_matrix
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
