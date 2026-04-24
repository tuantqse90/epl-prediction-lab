"""Dynamic Dixon-Coles ρ lookup.

Reads calibrated ρ per (league, season, quarter) from the database;
falls back to a safe default when a calibration hasn't been run yet.

Quarter is derived from the match's matchweek or kickoff timestamp.
We pick a simple week-bucketing approach: Q1 = weeks 1-10, Q2 = 11-20,
Q3 = 21-30, Q4 = 31+. A league with a non-standard weekcount still gets
a reasonable quarter mapping.
"""

from __future__ import annotations


DEFAULT_RHO = -0.15


def quarter_for_matchweek(matchweek: int | None) -> int:
    if matchweek is None or matchweek < 1:
        return 1
    if matchweek <= 10: return 1
    if matchweek <= 20: return 2
    if matchweek <= 30: return 3
    return 4


async def lookup_rho(
    pool, *, league_code: str | None, season: str | None, matchweek: int | None,
) -> float:
    if not league_code or not season:
        return DEFAULT_RHO
    q = quarter_for_matchweek(matchweek)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT rho FROM rho_calibration
            WHERE league_code = $1 AND season = $2 AND quarter = $3
            """,
            league_code, season, q,
        )
    if row is None:
        return DEFAULT_RHO
    return float(row["rho"])
