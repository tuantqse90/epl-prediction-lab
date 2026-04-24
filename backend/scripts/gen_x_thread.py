"""Generate an X/Twitter thread for today's top edges.

Output goes to stdout — no posting (Twitter API requires setup). User
copy-pastes. Each tweet is ≤ 280 chars; thread is 3-4 tweets.

Usage:
    python scripts/gen_x_thread.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings


async def run() -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        today_utc = datetime.now(timezone.utc).date().isoformat()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                WITH latest AS (
                    SELECT DISTINCT ON (p.match_id)
                      p.match_id, p.p_home_win, p.p_draw, p.p_away_win
                    FROM predictions p
                    ORDER BY p.match_id, p.created_at DESC
                ),
                best AS (
                    SELECT o.match_id,
                           MAX(o.odds_home) AS bh,
                           MAX(o.odds_draw) AS bd,
                           MAX(o.odds_away) AS ba
                    FROM match_odds o GROUP BY o.match_id
                )
                SELECT m.id, m.league_code, m.kickoff_time,
                       ht.short_name AS home_short, at.short_name AS away_short,
                       l.p_home_win, l.p_draw, l.p_away_win,
                       b.bh, b.bd, b.ba
                FROM matches m
                JOIN teams ht ON ht.id = m.home_team_id
                JOIN teams at ON at.id = m.away_team_id
                JOIN latest l ON l.match_id = m.id
                LEFT JOIN best b ON b.match_id = m.id
                WHERE m.status = 'scheduled'
                  AND m.kickoff_time BETWEEN NOW() AND NOW() + INTERVAL '36 hours'
                """,
            )

        picks: list[dict] = []
        for r in rows:
            probs = {"H": r["p_home_win"], "D": r["p_draw"], "A": r["p_away_win"]}
            side = max(probs, key=probs.get)
            conf = float(probs[side])
            odds = {"H": r["bh"], "D": r["bd"], "A": r["ba"]}[side]
            if not odds:
                continue
            edge_pp = (conf * float(odds) - 1) * 100
            if not (5.0 <= edge_pp <= 30.0):
                continue
            pick = (
                r["home_short"] if side == "H"
                else r["away_short"] if side == "A"
                else "Draw"
            )
            picks.append({
                "match_id": r["id"],
                "league_code": r["league_code"],
                "ko": r["kickoff_time"],
                "home": r["home_short"], "away": r["away_short"],
                "pick": pick, "conf": conf,
                "odds": float(odds), "edge_pp": edge_pp,
            })

        picks.sort(key=lambda e: -e["edge_pp"])
        top = picks[:3]
        if not top:
            print("# No tweet — no eligible edges today.")
            return

        # Tweet 1 — hook
        print("--- Tweet 1 / 4 ---")
        print(
            f"☀️ Today's 3 model edges "
            f"({datetime.now(timezone.utc).strftime('%a %d %b')})\n\n"
            f"xG-driven ensemble — Poisson + Elo + XGB on 5 top leagues + UCL.\n"
            f"Every pick has +{top[0]['edge_pp']:.0f}%+ expected value vs the market.\n\n"
            f"Thread ↓"
        )
        print()

        # Tweet 2-4 — one per pick
        for i, e in enumerate(top, start=2):
            ko = str(e["ko"])[11:16]
            print(f"--- Tweet {i} / 4 ---")
            print(
                f"{i-1}. {e['home']} vs {e['away']} · {ko} UTC\n\n"
                f"Model pick: {e['pick']} ({int(e['conf']*100)}%)\n"
                f"Best odds: {e['odds']:.2f}\n"
                f"Edge: +{e['edge_pp']:.1f}%\n\n"
                f"predictor.nullshift.sh/match/{e['match_id']}"
            )
            print()

        # Final tweet — link
        print("--- Tweet 4 / 4 ---")
        print(
            "Full methodology + calibration curve + 7-season equity curve "
            "open source at:\n\n"
            "predictor.nullshift.sh/methodology\n\n"
            "(xG doesn't lie. But the bookies do.)"
        )

    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    asyncio.run(run())


if __name__ == "__main__":
    main()
