"""Thread a hit/miss reply onto every pick tweet whose match has settled.

Accountability matters — publicly replying under your own bet with the
actual result builds trust faster than any marketing copy. Idempotent via
the 'recap' post_type row.

Env:
    X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET

Usage:
    python scripts/post_twitter_recap.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings


def _client():
    import tweepy
    keys = {
        "consumer_key":    os.environ.get("X_API_KEY"),
        "consumer_secret": os.environ.get("X_API_SECRET"),
        "access_token":    os.environ.get("X_ACCESS_TOKEN"),
        "access_token_secret": os.environ.get("X_ACCESS_TOKEN_SECRET"),
    }
    if not all(keys.values()):
        return None
    return tweepy.Client(**keys)


def _pick_side_from_body(body: str) -> str | None:
    # body looks like "Model: {home} win @ 1.85" / "Model: {away} win" / "Model: Draw"
    for line in body.splitlines():
        if line.startswith("Model:"):
            if "Draw" in line:
                return "D"
            # Use home/away ordering: first word after 'Model:'
            tail = line.split("Model:", 1)[1].strip()
            if tail.lower().startswith("draw"):
                return "D"
            return "__team__"  # caller disambiguates via DB
    return None


def _outcome(hg: int, ag: int) -> str:
    return "H" if hg > ag else ("A" if hg < ag else "D")


async def run() -> None:
    client = _client()
    if client is None:
        print("[twitter-recap] X API creds missing — skipping")
        return

    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        rows = await pool.fetch(
            """
            SELECT tp.match_id, tp.tweet_id AS pick_tweet_id, tp.body AS pick_body,
                   m.home_goals, m.away_goals,
                   ht.short_name AS home_short, at.short_name AS away_short,
                   p.p_home_win, p.p_draw, p.p_away_win
            FROM twitter_posts tp
            JOIN matches m ON m.id = tp.match_id
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            LEFT JOIN LATERAL (
                SELECT p_home_win, p_draw, p_away_win
                FROM predictions
                WHERE match_id = m.id
                ORDER BY created_at DESC LIMIT 1
            ) p ON TRUE
            WHERE tp.post_type = 'pick'
              AND m.status = 'final'
              AND m.home_goals IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM twitter_posts tp2
                  WHERE tp2.match_id = tp.match_id AND tp2.post_type = 'recap'
              )
            ORDER BY m.kickoff_time DESC
            LIMIT 20
            """,
        )
        print(f"[twitter-recap] {len(rows)} matches to recap")

        for r in rows:
            hg = int(r["home_goals"])
            ag = int(r["away_goals"])
            actual = _outcome(hg, ag)
            probs = {"H": float(r["p_home_win"] or 0), "D": float(r["p_draw"] or 0), "A": float(r["p_away_win"] or 0)}
            picked = max(probs, key=probs.get)
            hit = picked == actual
            icon = "✅" if hit else "❌"
            picked_label = (
                "Draw" if picked == "D"
                else f"{r['home_short'] if picked == 'H' else r['away_short']} win"
            )
            body = (
                f"{icon} {r['home_short']} {hg}-{ag} {r['away_short']}\n"
                f"Called: {picked_label} ({round(probs[picked] * 100)}%)"
            )
            try:
                resp = client.create_tweet(
                    text=body,
                    in_reply_to_tweet_id=str(r["pick_tweet_id"]),
                )
            except Exception as e:
                print(f"[twitter-recap] reply failed for match {r['match_id']}: {type(e).__name__}: {e}")
                continue
            tweet_id = str(resp.data["id"])
            await pool.execute(
                """
                INSERT INTO twitter_posts (match_id, post_type, tweet_id, body)
                VALUES ($1, 'recap', $2, $3)
                ON CONFLICT (match_id, post_type) DO NOTHING
                """,
                r["match_id"], tweet_id, body,
            )
            print(f"[twitter-recap] replied to {r['pick_tweet_id']} → {tweet_id}")
    finally:
        await pool.close()


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    asyncio.run(run())
