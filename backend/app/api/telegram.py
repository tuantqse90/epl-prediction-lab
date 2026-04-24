"""POST /api/telegram/webhook — Telegram bot update receiver.

Flow:
    1. Telegram POSTs an Update JSON here.
    2. parse_update() extracts (chat_id, command, args).
    3. Dispatcher maps command → async handler that queries DB.
    4. Handler returns markdown; send_message() POSTs it back.

The webhook is publicly reachable; Telegram sends a `X-Telegram-Bot-Api-Secret-Token`
header that matches TELEGRAM_WEBHOOK_SECRET if set via `setWebhook`. We verify that
so a random poster can't spam us.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from app.telegram.bot import (
    format_clv,
    format_edge,
    format_error,
    format_help,
    format_pick,
    format_roi,
    format_subscribe_ok,
    format_unknown_team,
    format_unsubscribe_ok,
    parse_update,
    send_message,
)


router = APIRouter(prefix="/api/telegram", tags=["telegram"])


class WebhookAck(BaseModel):
    ok: bool


@router.post("/webhook", response_model=WebhookAck)
async def webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> WebhookAck:
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
    if secret and x_telegram_bot_api_secret_token != secret:
        raise HTTPException(status_code=403, detail="bad secret")
    update = await request.json()
    cmd = parse_update(update)
    if cmd is None:
        return WebhookAck(ok=True)
    pool = request.app.state.pool
    text = await _dispatch(pool, cmd.command, cmd.args, chat_id=cmd.chat_id)
    send_message(cmd.chat_id, text)
    return WebhookAck(ok=True)


# ---------------------------------------------------------------------------
# Dispatcher + async DB fetchers
# ---------------------------------------------------------------------------


async def _dispatch(pool, command: str, args: list[str], *, chat_id: int | None = None) -> str:
    try:
        if command in ("help", "start"):
            return format_help()
        if command == "pick":
            return await _handle_pick(pool, args)
        if command == "edge":
            return await _handle_edge(pool)
        if command == "roi":
            return await _handle_roi(pool, args)
        if command == "clv":
            return await _handle_clv(pool)
        if command == "subscribe":
            return await _handle_subscribe(pool, args, chat_id=chat_id, subscribe=True)
        if command == "unsubscribe":
            return await _handle_subscribe(pool, args, chat_id=chat_id, subscribe=False)
        if command in ("subscriptions", "subs"):
            return await _handle_subscriptions_list(pool, chat_id=chat_id)
        return format_help()
    except Exception as e:
        print(f"[telegram] handler {command} crashed: {type(e).__name__}: {e}")
        return format_error("Bot had a hiccup — try again in a moment.")


async def _handle_pick(pool, args: list[str]) -> str:
    # Today window default; a team name arg overrides and returns next match
    # for that team.
    if args and args[0].lower() not in ("today", "tomorrow"):
        team_query = " ".join(args)
        return await _pick_for_team(pool, team_query)

    window = args[0].lower() if args else "today"
    if window == "tomorrow":
        bounds = "kickoff_time >= NOW() + INTERVAL '24 hours' AND kickoff_time < NOW() + INTERVAL '48 hours'"
    else:
        bounds = "kickoff_time >= NOW() AND kickoff_time < NOW() + INTERVAL '24 hours'"

    rows = await _fetch_picks(pool, bounds)
    return format_pick(rows, window_label=window)


async def _pick_for_team(pool, query: str) -> str:
    async with pool.acquire() as conn:
        team = await conn.fetchrow(
            """
            SELECT id, name, short_name, slug FROM teams
            WHERE lower(short_name) = lower($1)
               OR lower(slug) = lower($1)
               OR lower(name) LIKE lower($1) || '%'
            LIMIT 1
            """,
            query,
        )
    if not team:
        return format_unknown_team(query)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            _PICKS_QUERY_WITH_TEAM,
            team["id"],
        )
    return format_pick(rows, window_label=f"next · {team['short_name']}")


_PICKS_QUERY_BASE = """
WITH latest AS (
    SELECT DISTINCT ON (p.match_id)
        p.match_id, p.p_home_win, p.p_draw, p.p_away_win
    FROM predictions p
    ORDER BY p.match_id, p.created_at DESC
),
best AS (
    SELECT o.match_id,
           MAX(o.odds_home) AS best_home,
           MAX(o.odds_draw) AS best_draw,
           MAX(o.odds_away) AS best_away
    FROM match_odds o
    GROUP BY o.match_id
)
SELECT m.id,
       ht.short_name AS home_short, at.short_name AS away_short,
       m.league_code, m.kickoff_time,
       l.p_home_win, l.p_draw, l.p_away_win,
       b.best_home, b.best_draw, b.best_away
FROM matches m
JOIN teams ht ON ht.id = m.home_team_id
JOIN teams at ON at.id = m.away_team_id
LEFT JOIN latest l ON l.match_id = m.id
LEFT JOIN best b ON b.match_id = m.id
WHERE m.status = 'scheduled'
  AND l.p_home_win IS NOT NULL
"""

_PICKS_QUERY_WITH_TEAM = _PICKS_QUERY_BASE + """
  AND (m.home_team_id = $1 OR m.away_team_id = $1)
ORDER BY m.kickoff_time ASC
LIMIT 1
"""


async def _fetch_picks(pool, bounds_sql: str):
    q = _PICKS_QUERY_BASE + f"  AND {bounds_sql} ORDER BY m.kickoff_time ASC LIMIT 20"
    async with pool.acquire() as conn:
        raw = await conn.fetch(q)
    return [_row_to_pick(r) for r in raw if r["p_home_win"] is not None]


def _row_to_pick(r):
    probs = {"H": r["p_home_win"], "D": r["p_draw"], "A": r["p_away_win"]}
    side = max(probs, key=probs.get)
    conf = probs[side]
    best_odds = {
        "H": r["best_home"], "D": r["best_draw"], "A": r["best_away"],
    }[side]
    edge_pp = None
    if best_odds:
        edge_pp = (conf * best_odds - 1) * 100
    from types import SimpleNamespace
    return SimpleNamespace(
        match_id=r["id"],
        home_short=r["home_short"],
        away_short=r["away_short"],
        league_code=r["league_code"],
        kickoff_time=r["kickoff_time"],
        pick_side=side,
        pick_conf=conf,
        best_odds=best_odds,
        edge_pp=edge_pp,
    )


async def _handle_edge(pool) -> str:
    async with pool.acquire() as conn:
        raw = await conn.fetch(
            _PICKS_QUERY_BASE + """
              AND m.kickoff_time >= NOW()
              AND m.kickoff_time < NOW() + INTERVAL '7 days'
            ORDER BY m.kickoff_time ASC
            """
        )
    picks = [_row_to_pick(r) for r in raw if r["p_home_win"] is not None]
    # 5 ≤ edge ≤ 30 — anything above 30% is almost always an odds-data
    # bug (wrong home/away side, stale line), not real signal.
    picks = [p for p in picks if p.edge_pp is not None and 5.0 <= p.edge_pp <= 30.0]
    picks.sort(key=lambda p: -p.edge_pp)
    return format_edge(picks)


async def _handle_roi(pool, args: list[str]) -> str:
    window = "30d"
    days = 30
    if args:
        candidate = args[0].lower()
        if candidate in ("7d", "30d", "90d"):
            window = candidate
            days = {"7d": 7, "30d": 30, "90d": 90}[candidate]
    # Reuse the same math as /api/stats/roi — raw aggregate over graded
    # value bets in the window.
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
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
                FROM match_odds o
                GROUP BY o.match_id
            ),
            graded AS (
                SELECT m.id,
                  l.p_home_win, l.p_draw, l.p_away_win,
                  b.bh, b.bd, b.ba,
                  m.home_goals, m.away_goals
                FROM matches m
                JOIN latest l ON l.match_id = m.id
                LEFT JOIN best b ON b.match_id = m.id
                WHERE m.status = 'final'
                  AND m.kickoff_time > NOW() - ($1 || ' days')::INTERVAL
                  AND m.home_goals IS NOT NULL
            ),
            picks AS (
                SELECT
                  CASE
                    WHEN p_home_win >= p_draw AND p_home_win >= p_away_win
                         AND bh IS NOT NULL AND p_home_win * bh - 1 >= 0.05
                      THEN 'H'
                    WHEN p_draw >= p_home_win AND p_draw >= p_away_win
                         AND bd IS NOT NULL AND p_draw * bd - 1 >= 0.05
                      THEN 'D'
                    WHEN p_away_win >= p_home_win AND p_away_win >= p_draw
                         AND ba IS NOT NULL AND p_away_win * ba - 1 >= 0.05
                      THEN 'A'
                  END AS side,
                  bh, bd, ba, home_goals, away_goals
                FROM graded
            )
            SELECT
              COUNT(*) FILTER (WHERE side IS NOT NULL) AS bets,
              COALESCE(SUM(
                CASE side
                  WHEN 'H' THEN CASE WHEN home_goals > away_goals THEN bh - 1 ELSE -1 END
                  WHEN 'D' THEN CASE WHEN home_goals = away_goals THEN bd - 1 ELSE -1 END
                  WHEN 'A' THEN CASE WHEN home_goals < away_goals THEN ba - 1 ELSE -1 END
                END
              ), 0)::float AS pnl
            FROM picks
            """,
            str(days),
        )
    bets = int(row["bets"] or 0)
    pnl = float(row["pnl"] or 0.0)
    roi_pct = (pnl / bets * 100) if bets > 0 else 0.0
    return format_roi(total_bets=bets, roi_pct=roi_pct, pnl=pnl, window=window)


async def _handle_clv(pool) -> str:
    # Model pick vs devigged closing line. Positive mean CLV = model is
    # picking outcomes the market later agrees with → healthy signal.
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            WITH latest AS (
                SELECT DISTINCT ON (match_id)
                  match_id, p_home_win, p_draw, p_away_win
                FROM predictions ORDER BY match_id, created_at DESC
            )
            SELECT COUNT(*) AS n, AVG(clv_pct) AS mean_clv
            FROM (
                SELECT
                  CASE
                    WHEN l.p_home_win >= l.p_draw AND l.p_home_win >= l.p_away_win
                      THEN (l.p_home_win * co.odds_home - 1) * 100.0
                    WHEN l.p_away_win >= l.p_home_win AND l.p_away_win >= l.p_draw
                      THEN (l.p_away_win * co.odds_away - 1) * 100.0
                    ELSE (l.p_draw * co.odds_draw - 1) * 100.0
                  END AS clv_pct
                FROM closing_odds co
                JOIN latest l ON l.match_id = co.match_id
            ) x
            WHERE clv_pct IS NOT NULL
            """,
        )
    n = int(row["n"] or 0)
    mean = float(row["mean_clv"] or 0.0)
    return format_clv(total=n, mean_clv=mean)


async def _handle_subscribe(
    pool, args: list[str], *, chat_id: int | None, subscribe: bool,
) -> str:
    if chat_id is None:
        return format_error("Couldn't identify this chat.")
    if not args:
        return format_unknown_team("(no team given)")
    query = " ".join(args)
    async with pool.acquire() as conn:
        team = await conn.fetchrow(
            """
            SELECT id, name, short_name, slug FROM teams
            WHERE lower(short_name) = lower($1)
               OR lower(slug) = lower($1)
               OR lower(name) LIKE lower($1) || '%'
            LIMIT 1
            """,
            query,
        )
    if not team:
        return format_unknown_team(query)
    async with pool.acquire() as conn:
        if subscribe:
            await conn.execute(
                """
                INSERT INTO telegram_subscriptions (chat_id, team_slug)
                VALUES ($1, $2)
                ON CONFLICT (chat_id, team_slug) DO NOTHING
                """,
                chat_id, team["slug"],
            )
            return format_subscribe_ok(team["short_name"])
        await conn.execute(
            "DELETE FROM telegram_subscriptions WHERE chat_id = $1 AND team_slug = $2",
            chat_id, team["slug"],
        )
        return format_unsubscribe_ok(team["short_name"])


async def _handle_subscriptions_list(pool, *, chat_id: int | None) -> str:
    if chat_id is None:
        return format_error("Couldn't identify this chat.")
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT t.short_name, t.name, s.team_slug
            FROM telegram_subscriptions s
            JOIN teams t ON t.slug = s.team_slug
            WHERE s.chat_id = $1
            ORDER BY t.short_name
            """,
            chat_id,
        )
    if not rows:
        return "You're not subscribed to any team. Try `/subscribe ARS`."
    lines = ["*Your subscriptions*"]
    for r in rows:
        lines.append(f"• *{r['short_name']}* — {r['name']}")
    return "\n".join(lines)


async def fan_out_to_team_subscribers(
    pool, *, team_slugs: list[str], text: str,
) -> int:
    """Post `text` to every chat_id subscribed to any of `team_slugs`.

    Reused by live-scores for goal/HT/FT events. Returns count posted.
    """
    if not team_slugs:
        return 0
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT chat_id
            FROM telegram_subscriptions
            WHERE team_slug = ANY($1::text[])
            """,
            team_slugs,
        )
    posted = 0
    for r in rows:
        if send_message(int(r["chat_id"]), text):
            posted += 1
    return posted
