"""Per-referee scoring-environment tendency.

Referees have durable habits. Some allow more open, end-to-end matches;
others kill the tempo with frequent whistles. Over a 30+ match sample the
effect on total goals is real and measurable. We capture it as a
multiplicative shrink on both teams' λ — symmetric because refs don't
favour home or away, just the overall goal count.

Usage:
    rows = await conn.fetch(
        "SELECT referee, home_goals, away_goals FROM matches "
        "WHERE status = 'final' AND league_code = $1 AND season IN (...)",
        league_code,
    )
    tendencies = referee_tendencies(rows, min_matches=30)
    m = referee_multiplier(
        tendencies.get(match_ref, {}).get("goals_delta"),
        league_avg=2.8,
    )
    lambda_home *= m
    lambda_away *= m
"""
from __future__ import annotations


def _get(r, key):
    # asyncpg.Record: subscript; SimpleNamespace / dict: attr or .get
    if isinstance(r, dict):
        return r.get(key)
    try:
        return r[key]
    except (KeyError, TypeError):
        return getattr(r, key, None)


def referee_tendencies(rows, *, min_matches: int = 30) -> dict[str, dict]:
    """Compute per-ref goals-per-match delta vs the sample's league average.

    Returns a mapping `{referee_name: {goals_delta, n}}` for every ref with
    at least `min_matches` matches in the sample. Sparse refs are dropped
    entirely so callers fall through to the no-op multiplier.
    """
    per_ref: dict[str, list[int]] = {}
    all_totals: list[int] = []
    for r in rows:
        ref = _get(r, "referee")
        hg = _get(r, "home_goals")
        ag = _get(r, "away_goals")
        if hg is None or ag is None:
            continue
        total = int(hg) + int(ag)
        all_totals.append(total)
        if ref:
            per_ref.setdefault(ref, []).append(total)

    if not all_totals:
        return {}
    league_avg = sum(all_totals) / len(all_totals)

    out: dict[str, dict] = {}
    for ref, totals in per_ref.items():
        n = len(totals)
        if n < min_matches:
            continue
        ref_avg = sum(totals) / n
        out[ref] = {"goals_delta": ref_avg - league_avg, "n": n}
    return out


def referee_multiplier(delta, league_avg: float = 2.8, cap: float = 0.10) -> float:
    """Multiplicative shrink on goal-scoring rates based on ref tendency.

    `delta` is goals-per-match above/below the league baseline. A +0.3 delta
    on a 2.8 avg is +10.7% total goals, clamped at the cap. Returns 1.0 on
    missing data so the prediction pipeline stays valid.

    Applied symmetrically to both teams' λ — the ref affects the whole game's
    goal environment, not one side.
    """
    if delta is None:
        return 1.0
    if league_avg <= 0:
        return 1.0
    raw = float(delta) / float(league_avg)
    return 1.0 + max(-cap, min(cap, raw))
