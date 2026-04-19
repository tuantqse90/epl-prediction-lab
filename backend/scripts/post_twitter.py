"""Post top value bets to X (Twitter) — one tweet per pick.

Complements the Telegram channel. Tweet body is short enough to fit in 280
chars even with a long-name team pair; the link to /match/:id carries the
full context + OG image preview.

Env:
    X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET

Idempotent: `twitter_posts` table gates each (match_id, 'pick') tuple so
re-running won't spam.

Usage:
    python scripts/post_twitter.py [--horizon-days 3] [--threshold 0.07] [--max 5]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.ingest.odds import fair_probs
from app.leagues import BY_CODE


SITE = "https://predictor.nullshift.sh"


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


def _league_prefix(code: str | None) -> str:
    lg = BY_CODE.get(code or "")
    if lg is None:
        return ""
    return f"{lg.emoji} {lg.short}"


def _pick_side_label(side: str, home: str, away: str) -> str:
    if side == "H":
        return f"{home} win"
    if side == "A":
        return f"{away} win"
    return "Draw"


def _compose(match: dict, side: str, edge: float, model_p: float, odds: float) -> str:
    prefix = _league_prefix(match["league_code"])
    home = match["home_short"]
    away = match["away_short"]
    verb = _pick_side_label(side, home, away)
    edge_pp = f"{edge * 100:+.1f}%"
    link = f"{SITE}/match/{match['id']}"
    # 280-char budget — compose short enough that a worst-case league prefix
    # + long team names still fits. Link counts as 23 chars in twitter.
    lines = [
        f"{prefix} · {home} vs {away}".strip(" ·"),
        f"Model: {verb} @ {odds:.2f}",
        f"Edge {edge_pp} · {round(model_p * 100)}% model vs market",
        link,
    ]
    return "\n".join(lines)


async def _fetch_picks(pool: asyncpg.Pool, horizon_days: int, threshold: float, limit: int) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH latest AS (
                SELECT DISTINCT ON (p.match_id)
                    p.match_id, p.p_home_win, p.p_draw, p.p_away_win
                FROM predictions p
                ORDER BY p.match_id, p.created_at DESC
            )
            SELECT m.id, m.kickoff_time, m.league_code,
                   ht.short_name AS home_short, at.short_name AS away_short,
                   l.p_home_win, l.p_draw, l.p_away_win,
                   o.odds_home, o.odds_draw, o.odds_away
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            JOIN latest l ON l.match_id = m.id
            LEFT JOIN LATERAL (
                SELECT * FROM match_odds WHERE match_id = m.id ORDER BY captured_at DESC LIMIT 1
            ) o ON TRUE
            WHERE m.status = 'scheduled'
              AND m.kickoff_time BETWEEN NOW() AND NOW() + ($1 || ' days')::INTERVAL
              AND o.odds_home IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM twitter_posts tp
                  WHERE tp.match_id = m.id AND tp.post_type = 'pick'
              )
            ORDER BY m.kickoff_time ASC
            """,
            str(horizon_days),
        )

    picks: list[dict] = []
    for r in rows:
        probs = {"H": float(r["p_home_win"]), "D": float(r["p_draw"]), "A": float(r["p_away_win"])}
        fair = fair_probs(r["odds_home"], r["odds_draw"], r["odds_away"])
        if not fair:
            continue
        fair_map = {"H": fair[0], "D": fair[1], "A": fair[2]}
        odds_map = {"H": r["odds_home"], "D": r["odds_draw"], "A": r["odds_away"]}
        best_side, best_edge = max(
            (("H", probs["H"] - fair_map["H"]),
             ("D", probs["D"] - fair_map["D"]),
             ("A", probs["A"] - fair_map["A"])),
            key=lambda t: t[1],
        )
        if best_edge < threshold:
            continue
        picks.append({
            "id": r["id"],
            "league_code": r["league_code"],
            "home_short": r["home_short"],
            "away_short": r["away_short"],
            "side": best_side,
            "edge": best_edge,
            "model_p": probs[best_side],
            "odds": odds_map[best_side],
        })

    picks.sort(key=lambda p: p["edge"], reverse=True)
    return picks[:limit]


async def run(horizon_days: int, threshold: float, max_posts: int) -> None:
    client = _client()
    if client is None:
        print("[twitter] X API creds missing — skipping")
        return

    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        picks = await _fetch_picks(pool, horizon_days, threshold, max_posts)
        print(f"[twitter] {len(picks)} eligible picks to post")
        for p in picks:
            body = _compose(p, p["side"], p["edge"], p["model_p"], p["odds"])
            try:
                resp = client.create_tweet(text=body)
            except Exception as e:
                print(f"[twitter] tweet failed for {p['id']}: {type(e).__name__}: {e}")
                continue
            tweet_id = str(resp.data["id"])
            await pool.execute(
                """
                INSERT INTO twitter_posts (match_id, post_type, tweet_id, body)
                VALUES ($1, 'pick', $2, $3)
                ON CONFLICT (match_id, post_type) DO NOTHING
                """,
                p["id"], tweet_id, body,
            )
            print(f"[twitter] posted pick for match {p['id']} → tweet {tweet_id}")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    p = argparse.ArgumentParser()
    p.add_argument("--horizon-days", type=int, default=3,
                   help="Only pick matches starting within N days")
    p.add_argument("--threshold", type=float, default=0.07,
                   help="Minimum model-vs-market edge (0.07 = 7pp)")
    p.add_argument("--max", dest="max_posts", type=int, default=5,
                   help="Cap posts per run to stay under daily quota")
    args = p.parse_args()
    asyncio.run(run(args.horizon_days, args.threshold, args.max_posts))


if __name__ == "__main__":
    main()
