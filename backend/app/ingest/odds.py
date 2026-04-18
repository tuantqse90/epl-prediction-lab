"""football-data.co.uk odds CSV → DB rows + devig helpers.

Pure translator is tested. Upsert side talks to `match_odds`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import asyncpg
import pandas as pd

# football-data uses short team labels; map them back to the Understat
# canonical names we already have in `teams.name`.
NAME_MAP: dict[str, str] = {
    "Man United": "Manchester United",
    "Man City": "Manchester City",
    "Wolves": "Wolverhampton Wanderers",
    "Newcastle": "Newcastle United",
    "Nott'm Forest": "Nottingham Forest",
    "West Ham": "West Ham",
    "Leeds": "Leeds",
    "Tottenham": "Tottenham",
    "Ipswich": "Ipswich",
    "Leicester": "Leicester",
    "Southampton": "Southampton",
    # identity-mapped names can be added lazily via _canon
}


def _canon(name: str) -> str:
    return NAME_MAP.get(name, name)


@dataclass(frozen=True)
class OddsRow:
    season: str
    date: pd.Timestamp
    home_name: str
    away_name: str
    odds_home: float
    odds_draw: float
    odds_away: float
    source: str  # e.g. "football-data:avg" or "football-data:pinnacle"


def _pick_odds(row, cols: tuple[str, str, str]) -> tuple[float, float, float] | None:
    h, d, a = cols
    try:
        oh, od, oa = float(row[h]), float(row[d]), float(row[a])
    except (KeyError, TypeError, ValueError):
        return None
    if not all(v and v > 1.0 for v in (oh, od, oa)):
        return None
    if pd.isna(oh) or pd.isna(od) or pd.isna(oa):
        return None
    return oh, od, oa


def odds_csv_to_rows(df: pd.DataFrame, season: str) -> list[OddsRow]:
    out: list[OddsRow] = []
    for r in df.itertuples(index=False):
        row = r._asdict() if hasattr(r, "_asdict") else dict(zip(df.columns, r))

        avg = _pick_odds(row, ("AvgH", "AvgD", "AvgA"))
        src = "football-data:avg"
        if avg is None:
            avg = _pick_odds(row, ("PSH", "PSD", "PSA"))
            src = "football-data:pinnacle"
        if avg is None:
            avg = _pick_odds(row, ("B365H", "B365D", "B365A"))
            src = "football-data:bet365"
        if avg is None:
            continue

        date = pd.to_datetime(row["Date"], dayfirst=True, errors="coerce")
        if pd.isna(date):
            continue

        out.append(
            OddsRow(
                season=season,
                date=date,
                home_name=_canon(str(row["HomeTeam"]).strip()),
                away_name=_canon(str(row["AwayTeam"]).strip()),
                odds_home=avg[0],
                odds_draw=avg[1],
                odds_away=avg[2],
                source=src,
            )
        )
    return out


def fair_probs(odds_home: float, odds_draw: float, odds_away: float) -> tuple[float, float, float] | None:
    """Devig bookmaker odds → fair probabilities that sum to 1."""
    if any(o <= 0 for o in (odds_home, odds_draw, odds_away)):
        return None
    raw = [1.0 / odds_home, 1.0 / odds_draw, 1.0 / odds_away]
    s = sum(raw)
    if s <= 0:
        return None
    return raw[0] / s, raw[1] / s, raw[2] / s


def edge(model_prob: float, fair_prob: float) -> float:
    """Absolute percentage-point delta (model − fair). Positive = value for model side."""
    return model_prob - fair_prob


async def upsert_odds(pool: asyncpg.Pool, rows: Iterable[OddsRow]) -> int:
    rows = list(rows)
    async with pool.acquire() as conn:
        async with conn.transaction():
            n = 0
            for r in rows:
                match_id = await conn.fetchval(
                    """
                    SELECT m.id FROM matches m
                    JOIN teams ht ON ht.id = m.home_team_id
                    JOIN teams at ON at.id = m.away_team_id
                    WHERE m.season = $1
                      AND ht.name = $2 AND at.name = $3
                      AND DATE(m.kickoff_time) = $4
                    """,
                    r.season, r.home_name, r.away_name, r.date.date(),
                )
                if match_id is None:
                    continue
                await conn.execute(
                    """
                    INSERT INTO match_odds (
                        match_id, source, odds_home, odds_draw, odds_away
                    ) VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (match_id, source) DO UPDATE SET
                        odds_home = EXCLUDED.odds_home,
                        odds_draw = EXCLUDED.odds_draw,
                        odds_away = EXCLUDED.odds_away,
                        captured_at = NOW()
                    """,
                    match_id, r.source, r.odds_home, r.odds_draw, r.odds_away,
                )
                n += 1
    return n
