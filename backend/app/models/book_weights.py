"""Book weights — Pinnacle-heavy consensus.

Sharp sportsbooks (Pinnacle, Betfair Exchange) produce tighter lines
than retail books. When building a "market consensus" probability, give
those books more weight.

Default weights reflect common sharp-trading folklore:
  * Pinnacle, Betfair Exchange   → 1.0
  * 1xBet, SBOBet, BetVictor     → 0.7
  * Bet365, Unibet, William Hill → 0.5
  * everyone else                 → 0.3
"""

from __future__ import annotations

from typing import Iterable


_SHARP = {"pinnacle", "betfair", "betfair_ex", "matchbook", "betfair_sb_uk"}
_LEAN_SHARP = {"1xbet", "sbobet", "betvictor", "pinnacle_sb"}
_RETAIL_BIG = {
    "bet365", "unibet", "williamhill", "william_hill",
    "bet365_uk", "unibet_se", "unibet_nl",
}


def _normalise(source: str) -> str:
    s = source.lower()
    # Strip a provider prefix like "odds-api:" or "af:"
    if ":" in s:
        s = s.split(":", 1)[1]
    return s


def weight_for(source: str) -> float:
    s = _normalise(source)
    if any(k in s for k in _SHARP):
        return 1.0
    if any(k in s for k in _LEAN_SHARP):
        return 0.7
    if any(k in s for k in _RETAIL_BIG):
        return 0.5
    return 0.3


def _devig(home: float, draw: float, away: float) -> tuple[float, float, float]:
    ih, id_, ia = 1 / home, 1 / draw, 1 / away
    total = ih + id_ + ia
    return (ih / total, id_ / total, ia / total)


def weighted_consensus(rows: Iterable) -> dict | None:
    """Take rows with (source, odds_home, odds_draw, odds_away) and return
    weighted-consensus devigged probabilities.

    Weights per book via `weight_for()`. If weights sum to 0, returns None.
    """
    rows = list(rows)
    wsum = 0.0
    h = d = a = 0.0
    for r in rows:
        src = getattr(r, "source", None)
        oh = float(getattr(r, "odds_home", 0) or 0)
        od = float(getattr(r, "odds_draw", 0) or 0)
        oa = float(getattr(r, "odds_away", 0) or 0)
        if not src or oh <= 1 or od <= 1 or oa <= 1:
            continue
        w = weight_for(src)
        if w <= 0:
            continue
        ph, pd, pa = _devig(oh, od, oa)
        h += ph * w; d += pd * w; a += pa * w
        wsum += w
    if wsum == 0:
        return None
    return {
        "p_home_win": h / wsum,
        "p_draw": d / wsum,
        "p_away_win": a / wsum,
        "weight_sum": wsum,
    }
