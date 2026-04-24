"""O/U middle finder.

A middle pair is:
  * OVER at line_low @ book_A
  * UNDER at line_high @ book_B
  * line_low < line_high

If the actual total lands STRICTLY between the two lines, both bets win.
Outside the middle band, exactly one wins.

Returns per candidate pair:
  middle_low, middle_high, source_over, source_under, odds_over, odds_under,
  middle_pnl   — payout when middle hits (stake 1 + 1)
  miss_pnl_low, miss_pnl_high — payout when total falls outside the middle
"""

from __future__ import annotations

from typing import Iterable


def find_ou_middles(rows: Iterable) -> list[dict]:
    """Scan O/U rows (each has source, line, outcome_code, odds) and
    return all positive-middle pairs.
    """
    overs = [r for r in rows if getattr(r, "outcome_code", "") == "OVER"]
    unders = [r for r in rows if getattr(r, "outcome_code", "") == "UNDER"]

    out: list[dict] = []
    for o in overs:
        for u in unders:
            if o.line >= u.line:
                continue          # no gap, not a middle
            if o.source == u.source:
                continue          # same book; they have both sides covered
            out.append({
                "middle_low": o.line,
                "middle_high": u.line,
                "source_over": o.source,
                "source_under": u.source,
                "odds_over": o.odds,
                "odds_under": u.odds,
                # Stake 1 on each side.
                "middle_pnl": o.odds + u.odds - 2.0,
                "miss_pnl_low": u.odds - 2.0,
                "miss_pnl_high": o.odds - 2.0,
            })
    out.sort(key=lambda m: -m["middle_pnl"])
    return out
