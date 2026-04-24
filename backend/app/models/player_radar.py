"""Player-radar normalized coefficients.

Given a player's raw per-season totals, normalise each axis against the
league-position baseline so a forward and a midfielder produce comparable
radar silhouettes. Positions treated:
    FW — attacking forward
    MF — midfielder
    DF — defender
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RadarAxes:
    # All scaled to [0, 1] against 90th-percentile baseline per position.
    goals_p90: float
    xg_p90: float
    assists_p90: float
    xa_p90: float
    key_passes_p90: float
    g_minus_xg: float          # finishing: positive = outperforms xG


# Per-position 90th-percentile caps. Anything above caps at 1.0.
_CAPS: dict[str, dict[str, float]] = {
    "FW": {"goals": 0.60, "xg": 0.55, "assists": 0.30, "xa": 0.30, "key_passes": 2.4},
    "MF": {"goals": 0.30, "xg": 0.25, "assists": 0.40, "xa": 0.35, "key_passes": 2.8},
    "DF": {"goals": 0.15, "xg": 0.12, "assists": 0.20, "xa": 0.15, "key_passes": 1.8},
}


def _per_90(total: float, games: float) -> float:
    if games <= 0:
        return 0.0
    return total / games   # `games` ≈ 90-min units from Understat


def build_radar(
    *, position: str, goals: int, xg: float, assists: int, xa: float,
    key_passes: int, games: int,
) -> RadarAxes:
    pos = position.upper()[:2] if position else "MF"
    if pos.startswith("F"):
        pos = "FW"
    elif pos.startswith("D"):
        pos = "DF"
    else:
        pos = "MF"
    caps = _CAPS[pos]

    goals_p90 = _per_90(goals, games)
    xg_p90 = _per_90(xg, games)
    assists_p90 = _per_90(assists, games)
    xa_p90 = _per_90(xa, games)
    kp_p90 = _per_90(key_passes, games)

    def scale(v: float, cap: float) -> float:
        return max(0.0, min(1.0, v / cap)) if cap > 0 else 0.0

    # Finishing: goals − xG per 90, centered on 0. Map [-0.3, +0.3] → [0, 1].
    g_minus = _per_90(goals - xg, games)
    g_minus_scaled = max(0.0, min(1.0, (g_minus + 0.3) / 0.6))

    return RadarAxes(
        goals_p90=scale(goals_p90, caps["goals"]),
        xg_p90=scale(xg_p90, caps["xg"]),
        assists_p90=scale(assists_p90, caps["assists"]),
        xa_p90=scale(xa_p90, caps["xa"]),
        key_passes_p90=scale(kp_p90, caps["key_passes"]),
        g_minus_xg=g_minus_scaled,
    )
