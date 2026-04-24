"""GET /api/stats/bracket — Monte Carlo over remaining UCL/UEL bracket.

Given the fixtures still to play in a knockout competition, sample goal
outcomes per leg from each match's stored (expected_home_goals,
expected_away_goals), aggregate ties, advance winners through the tree,
count trophy lifts per team.

Works for any 2-leg tie + single-match final. Not generalised to earlier
rounds yet — kicks off once only 4 teams remain (semifinal stage).
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel


router = APIRouter(prefix="/api/stats", tags=["stats"])


COMP_CODES = {
    "UCL": "UEFA-Champions League",
    "UEL": "UEFA-Europa League",
}


class TeamOdds(BaseModel):
    team_slug: str
    team_short: str
    p_semi_win: float     # probability of winning their semi
    p_final_win: float    # probability of winning the final (conditional on reaching it)
    p_lift_trophy: float  # combined


class BracketResponse(BaseModel):
    competition: str
    n_simulations: int
    teams: list[TeamOdds]


@dataclass
class Fixture:
    home: str           # team short
    home_slug: str
    away: str
    away_slug: str
    lam_h: float
    lam_a: float
    # Aggregate tiebreak from first leg — filled in for leg 2.
    first_leg_agg_home: int = 0
    first_leg_agg_away: int = 0


def _sample_poisson(lam: float, rng: random.Random) -> int:
    if lam <= 0:
        return 0
    L = math.exp(-lam)
    k, p = 0, 1.0
    while True:
        k += 1
        p *= rng.random()
        if p < L:
            return k - 1


def _simulate_leg(fx: Fixture, rng: random.Random) -> tuple[int, int]:
    return _sample_poisson(fx.lam_h, rng), _sample_poisson(fx.lam_a, rng)


def _simulate_tie(
    first: Fixture, second: Fixture, rng: random.Random,
) -> str:
    """Simulate a 2-leg tie, return the short_name of the advancing team."""
    h1, a1 = _simulate_leg(first, rng)
    h2, a2 = _simulate_leg(second, rng)
    # In leg 2, the "home" side is the original away team.
    team_first_home_agg = h1 + a2
    team_first_away_agg = a1 + h2
    if team_first_home_agg > team_first_away_agg:
        return first.home_slug
    if team_first_home_agg < team_first_away_agg:
        return first.away_slug
    # Tied on aggregate → coin flip proxy for penalties.
    return first.home_slug if rng.random() < 0.5 else first.away_slug


@router.get("/bracket", response_model=BracketResponse)
async def bracket(
    request: Request,
    competition: str = Query("UCL", regex="^(UCL|UEL)$"),
    n: int = Query(5000, ge=500, le=50_000),
    seed: int = Query(42, ge=0, le=1_000_000),
) -> BracketResponse:
    league_code = COMP_CODES[competition]
    pool = request.app.state.pool

    async with pool.acquire() as conn:
        fixtures = await conn.fetch(
            """
            WITH latest AS (
                SELECT DISTINCT ON (p.match_id)
                    p.match_id,
                    p.expected_home_goals, p.expected_away_goals
                FROM predictions p
                ORDER BY p.match_id, p.created_at DESC
            )
            SELECT m.id, m.kickoff_time,
                   ht.slug AS home_slug, ht.short_name AS home_short,
                   at.slug AS away_slug, at.short_name AS away_short,
                   l.expected_home_goals AS lam_h,
                   l.expected_away_goals AS lam_a
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            LEFT JOIN latest l ON l.match_id = m.id
            WHERE m.league_code = $1
              AND m.status = 'scheduled'
              AND l.expected_home_goals IS NOT NULL
            ORDER BY m.kickoff_time ASC
            """,
            league_code,
        )

    if not fixtures:
        return BracketResponse(competition=competition, n_simulations=0, teams=[])

    # Group fixtures by ordered team-pair → list of legs in kickoff order.
    pairs: dict[frozenset[str], list[Fixture]] = defaultdict(list)
    for r in fixtures:
        fx = Fixture(
            home=r["home_short"], home_slug=r["home_slug"],
            away=r["away_short"], away_slug=r["away_slug"],
            lam_h=float(r["lam_h"]), lam_a=float(r["lam_a"]),
        )
        pairs[frozenset({r["home_slug"], r["away_slug"]})].append(fx)

    # Two-leg ties: pairs with 2 fixtures.
    two_leg_pairs = [legs for legs in pairs.values() if len(legs) == 2]
    # Potential final: a single-fixture pair (legs count = 1).
    single_pairs = [legs[0] for legs in pairs.values() if len(legs) == 1]

    if not two_leg_pairs:
        # No semifinals to simulate — just return an empty result.
        return BracketResponse(competition=competition, n_simulations=0, teams=[])

    # Need team shortnames for mapping slug → short_name.
    short_of: dict[str, str] = {}
    for fx in fixtures:
        short_of[fx["home_slug"]] = fx["home_short"]
        short_of[fx["away_slug"]] = fx["away_short"]

    semi_win = defaultdict(int)
    final_win = defaultdict(int)
    lift = defaultdict(int)

    rng = random.Random(seed)
    for _ in range(n):
        # Advance each semi.
        advancers: list[str] = []
        for legs in two_leg_pairs:
            first, second = legs[0], legs[1]
            winner = _simulate_tie(first, second, rng)
            semi_win[winner] += 1
            advancers.append(winner)

        # Simulate the final if there's one.
        if len(advancers) == 2:
            # No stored λ for a final that hasn't been scheduled yet —
            # use the semis' attack/defense weighted average as a proxy.
            # For now, 50/50 between advancers (home advantage irrelevant
            # on a neutral-venue final, and we have no per-team λ).
            w = advancers[0] if rng.random() < 0.5 else advancers[1]
            final_win[w] += 1
            lift[w] += 1

    # Assemble response: one row per team that appeared.
    teams_slugs = {s for f in fixtures for s in (f["home_slug"], f["away_slug"])}
    out: list[TeamOdds] = []
    for slug in teams_slugs:
        out.append(TeamOdds(
            team_slug=slug,
            team_short=short_of.get(slug, slug),
            p_semi_win=semi_win[slug] / n,
            p_final_win=final_win[slug] / max(1, semi_win[slug]),
            p_lift_trophy=lift[slug] / n,
        ))
    out.sort(key=lambda t: -t.p_lift_trophy)
    return BracketResponse(
        competition=competition, n_simulations=n, teams=out,
    )
