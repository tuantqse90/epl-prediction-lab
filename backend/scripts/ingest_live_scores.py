"""Poll API-Football for live EPL fixtures and update DB score + minute.

Quota-aware: only calls the API when the DB has at least one match inside
the "could be in progress" window (kickoff within the last 150 min and not
final). Otherwise it's a no-op — no quota burned overnight.

Env:
    API_FOOTBALL_KEY   — https://dashboard.api-football.com (free 100/day)
    API_FOOTBALL_LEAGUE_ID   (default 39 = EPL)

Usage:
    python scripts/ingest_live_scores.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import urllib.request
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings
from app.leagues import BY_CODE, DEFAULT_LEAGUE, LEAGUES


def _league_prefix(code: str | None) -> str:
    lg = BY_CODE.get(code or DEFAULT_LEAGUE) or BY_CODE[DEFAULT_LEAGUE]
    return f"{lg.emoji} {lg.short}"


# API-Football returns long names; map back to Understat canonical forms.
# Missing entries fall through via `_canon`. Extend as new clubs show up.
NAME_MAP: dict[str, str] = {
    # Premier League
    "Brighton & Hove Albion": "Brighton",
    "Newcastle": "Newcastle United",
    "Wolves": "Wolverhampton Wanderers",
    "Tottenham Hotspur": "Tottenham",
    "Leeds United": "Leeds",
    "Manchester Utd": "Manchester United",
    "Sheffield Utd": "Sheffield United",
    # La Liga
    "Athletic Club de Bilbao": "Athletic Club",
    "Atlético Madrid": "Atletico Madrid",
    "Atletico de Madrid": "Atletico Madrid",
    "Celta de Vigo": "Celta Vigo",
    "RCD Espanyol": "Espanyol",
    "Rayo Vallecano de Madrid": "Rayo Vallecano",
    "Betis": "Real Betis",
    "Alavés": "Alaves",
    # Bundesliga
    "FC Bayern München": "Bayern Munich",
    "Bayern München": "Bayern Munich",
    "Borussia Mönchengladbach": "Borussia M.Gladbach",
    "Eintracht Frankfurt": "Eintracht Frankfurt",
    "1. FC Köln": "FC Cologne",
    "FC Köln": "FC Cologne",
    "1. FC Heidenheim": "FC Heidenheim",
    "1. FSV Mainz 05": "Mainz 05",
    "FC St. Pauli": "St. Pauli",
    "1. FC Union Berlin": "Union Berlin",
    "VfL Wolfsburg": "Wolfsburg",
    "SV Werder Bremen": "Werder Bremen",
    "RB Leipzig": "RasenBallsport Leipzig",
    "FC Augsburg": "Augsburg",
    "Hamburger SV": "Hamburger SV",
    "SC Freiburg": "Freiburg",
    "TSG 1899 Hoffenheim": "Hoffenheim",
    # Serie A
    "Internazionale": "Inter",
    "Milan": "AC Milan",
    "AS Roma": "Roma",
    "Parma": "Parma Calcio 1913",
    "Hellas Verona": "Verona",
    # Ligue 1
    "Paris": "Paris Saint Germain",
    "Paris Saint-Germain": "Paris Saint Germain",
    "Olympique Lyonnais": "Lyon",
    "Olympique de Marseille": "Marseille",
    "OGC Nice": "Nice",
    "Stade Rennais": "Rennes",
    "RC Lens": "Lens",
    "AS Monaco": "Monaco",
    "AS Saint-Étienne": "Saint-Etienne",
    "LOSC Lille": "Lille",
    "Stade Brestois 29": "Brest",
    "AJ Auxerre": "Auxerre",
    "FC Nantes": "Nantes",
    "FC Metz": "Metz",
    "Angers SCO": "Angers",
    "Le Havre AC": "Le Havre",
    "Racing Strasbourg": "Strasbourg",
    "FC Lorient": "Lorient",
    "Toulouse FC": "Toulouse",
}

_LEAGUE_IDS: set[int] = {lg.api_football_id for lg in LEAGUES}


def _canon(n: str) -> str:
    return NAME_MAP.get(n, n)


def _map_status(api_short: str) -> str:
    """API-Football short → our DB status ('live' | 'final' | 'scheduled')."""
    if api_short in {"1H", "2H", "HT", "ET", "BT", "P", "LIVE"}:
        return "live"
    if api_short in {"FT", "AET", "PEN"}:
        return "final"
    return "scheduled"


async def _has_potential_live(pool: asyncpg.Pool) -> bool:
    # Either (a) a match's about to / just kicked off, or (b) a match is
    # still marked 'live' from a prior cycle — keep polling until we see
    # its FT transition, however late.
    return bool(await pool.fetchval(
        """
        SELECT EXISTS(
            SELECT 1 FROM matches
            WHERE status = 'live'
               OR (status != 'final'
                   AND kickoff_time BETWEEN NOW() - INTERVAL '150 minutes'
                                        AND NOW() + INTERVAL '5 minutes')
        )
        """,
    ))


def _fetch(key: str, league_id: int | None = None) -> list[dict]:
    """Poll API-Football for live fixtures. One request covers all top-5
    leagues by filtering client-side on the response; skip per-league calls
    to keep quota small during busy weekends."""
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    req = urllib.request.Request(url, headers={"x-apisports-key": key})
    with urllib.request.urlopen(req, timeout=20) as resp:
        remaining = resp.headers.get("x-ratelimit-requests-remaining")
        if remaining:
            print(f"[live-scores] quota remaining: {remaining}")
        body = json.loads(resp.read())
    raw = body.get("response", []) or []
    if league_id is not None:
        return [f for f in raw if (f.get("league") or {}).get("id") == league_id]
    # keep only the leagues we follow
    return [f for f in raw if (f.get("league") or {}).get("id") in _LEAGUE_IDS]


def _fetch_events(key: str, fixture_id: int) -> list[dict]:
    url = f"https://v3.football.api-sports.io/fixtures/events?fixture={fixture_id}"
    req = urllib.request.Request(url, headers={"x-apisports-key": key})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read())
        return body.get("response", []) or []
    except Exception as e:
        print(f"[live-scores] events fetch failed for {fixture_id}: {type(e).__name__}")
        return []


async def _upsert_events(
    pool: asyncpg.Pool, match_id: int, events: list[dict], home: str, away: str,
) -> list[int]:
    """Upsert events into match_events; return event IDs that were *actually* inserted
    (i.e. not silenced by the ON CONFLICT DO NOTHING idempotency guard).
    """
    if not events:
        return []
    inserted_ids: list[int] = []
    async with pool.acquire() as conn:
        async with conn.transaction():
            team_rows = await conn.fetch(
                "SELECT slug, name FROM teams WHERE name IN ($1, $2)", home, away,
            )
            by_name = {r["name"]: r["slug"] for r in team_rows}

            for e in events:
                time_info = e.get("time") or {}
                team_info = e.get("team") or {}
                player_info = e.get("player") or {}
                assist_info = e.get("assist") or {}
                team_name = _canon(team_info.get("name", "").strip())
                team_slug = by_name.get(team_name)
                new_id = await conn.fetchval(
                    """
                    INSERT INTO match_events (
                        match_id, minute, extra_minute, team_slug,
                        player_name, assist_name, event_type, event_detail
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT DO NOTHING
                    RETURNING id
                    """,
                    match_id,
                    time_info.get("elapsed"),
                    time_info.get("extra"),
                    team_slug,
                    (player_info.get("name") or "").strip() or None,
                    (assist_info.get("name") or "").strip() or None,
                    e.get("type", "").strip(),
                    (e.get("detail") or "").strip() or None,
                )
                if new_id is not None:
                    inserted_ids.append(int(new_id))
    return inserted_ids


async def _notify_goal_events(
    pool: asyncpg.Pool,
    match_id: int,
    new_event_ids: list[int],
    *,
    home_short: str,
    away_short: str,
    home_goals: int,
    away_goals: int,
    minute: int,
) -> None:
    """Post a Telegram message for each brand-new Goal event. Idempotent via
    notified_at so re-running doesn't re-spam."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        return

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, minute, extra_minute, player_name, assist_name,
                   event_type, event_detail, team_slug
            FROM match_events
            WHERE id = ANY($1::int[])
              AND event_type = 'Goal'
              AND notified_at IS NULL
            ORDER BY minute ASC NULLS LAST, extra_minute ASC NULLS LAST, id ASC
            """,
            new_event_ids,
        )
        teams = await conn.fetchrow(
            """
            SELECT ht.short_name AS home_short, ht.name AS home_name,
                   at.short_name AS away_short, at.name AS away_name,
                   ht.slug AS home_slug, at.slug AS away_slug,
                   m.league_code
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.id = $1
            """,
            match_id,
        )

    if not rows or teams is None:
        return

    # Use our existing live probability helper so the alert carries the same
    # "model thinks" number the site shows.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # idempotent
    from app.models.poisson import live_probabilities  # local import avoids boot cost

    # Pull pre-match lambdas from the latest prediction row.
    async with pool.acquire() as conn:
        pred = await conn.fetchrow(
            """
            SELECT expected_home_goals, expected_away_goals
            FROM predictions
            WHERE match_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            match_id,
        )

    for r in rows:
        scorer = r["player_name"] or "?"
        assist = r["assist_name"]
        minute_label = (
            f"{r['minute']}+{r['extra_minute']}'"
            if r["extra_minute"]
            else f"{r['minute']}'"
        )
        scoring_home = r["team_slug"] == teams["home_slug"]
        scoring_team = teams["home_name"] if scoring_home else teams["away_name"]
        detail = (r["event_detail"] or "").lower()
        icon = "🎯" if "penalty" in detail and "missed" not in detail else (
            "⚽️" if "own goal" not in detail else "⚽️ (phản lưới)"
        )

        prefix = _league_prefix(teams["league_code"])
        lines = [
            f"{icon} *{minute_label} · {prefix} · {home_short} {home_goals}-{away_goals} {away_short}*",
            f"_{scoring_team}_ — {scorer}"
            + (f"  (kiến tạo: {assist})" if assist else ""),
        ]

        if pred:
            lp = live_probabilities(
                float(pred["expected_home_goals"]),
                float(pred["expected_away_goals"]),
                home_goals, away_goals, minute=minute, rho=-0.15,
            )
            lines.append(
                f"Mô hình hiện tại: chủ {round(lp.p_home_win * 100)}% · "
                f"hòa {round(lp.p_draw * 100)}% · khách {round(lp.p_away_win * 100)}%"
            )
        lines.append(f"https://predictor.nullshift.sh/match/{match_id}")
        text = "\n".join(lines)

        try:
            _telegram_post(token, chat_id, text)
        except Exception as e:
            print(f"[live-scores] telegram goal alert failed: {type(e).__name__}: {e}")
            continue

        # Web Push to subscribers following either side. Best-effort — no
        # retry, drops 410 Gone rows. Separate from telegram so a TG outage
        # doesn't silence push and vice versa.
        try:
            from app.api.push import dispatch_goal
            await dispatch_goal(
                pool,
                [teams["home_slug"], teams["away_slug"]],
                {
                    "title": f"{icon} {minute_label} {home_short} {home_goals}-{away_goals} {away_short}",
                    "body": f"{scoring_team} — {scorer}",
                    "url": f"https://predictor.nullshift.sh/match/{match_id}",
                },
            )
        except Exception as e:
            print(f"[live-scores] push dispatch failed: {type(e).__name__}: {e}")

        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE match_events SET notified_at = NOW() WHERE id = $1", r["id"],
            )


def _telegram_post(token: str, chat_id: str, text: str) -> dict:
    import urllib.parse

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": "true",
    }).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


async def _update(pool: asyncpg.Pool, f: dict, api_key: str) -> bool:
    teams = f["teams"]
    fixture = f["fixture"]
    goals = f.get("goals", {})
    home = _canon(teams["home"]["name"].strip())
    away = _canon(teams["away"]["name"].strip())
    status_short = (fixture.get("status") or {}).get("short", "")
    elapsed = (fixture.get("status") or {}).get("elapsed")
    hg = goals.get("home")
    ag = goals.get("away")
    fixture_id = fixture.get("id")
    referee = (fixture.get("referee") or "").strip() or None

    db_status = _map_status(status_short)
    if hg is None or ag is None:
        return False

    async with pool.acquire() as conn:
        # Capture the prior score so we can decide whether to spend an events
        # call. /fixtures/events is the expensive endpoint — only worth it
        # when something actually changed on the scoreboard.
        # Window: 6h past kickoff covers extra time / ref delays. If still
        # labelled 'live' past that, match row matches by name alone.
        match_row = await conn.fetchrow(
            """
            WITH prev AS (
                SELECT m.id, m.status AS prev_status,
                       m.home_goals AS prev_hg, m.away_goals AS prev_ag
                FROM matches m
                JOIN teams ht ON ht.id = m.home_team_id
                JOIN teams at ON at.id = m.away_team_id
                WHERE ht.name = $5 AND at.name = $6
                  AND (
                    m.status = 'live'
                    OR m.kickoff_time BETWEEN NOW() - INTERVAL '6 hours'
                                          AND NOW() + INTERVAL '30 minutes'
                  )
                ORDER BY m.kickoff_time DESC
                LIMIT 1
            )
            UPDATE matches m
            SET status = $1,
                home_goals = $2,
                away_goals = $3,
                minute = $4,
                live_period = $7,
                referee = COALESCE($8, m.referee),
                live_updated_at = NOW()
            FROM prev
            WHERE m.id = prev.id
            RETURNING m.id, prev.prev_status, prev.prev_hg, prev.prev_ag
            """,
            db_status, int(hg), int(ag), elapsed, home, away, status_short, referee,
        )
    if not match_row:
        return False

    score_changed = (
        match_row["prev_hg"] != int(hg) or match_row["prev_ag"] != int(ag)
    )
    status_changed = match_row["prev_status"] != db_status

    # Only hit /fixtures/events when something interesting changed. Most
    # polling cycles (90%+) see a static scoreline — skipping events there
    # lets us poll aggressively without blowing API-Football quota.
    should_fetch_events = (
        (score_changed or status_changed)
        and db_status in ("live", "final")
        and fixture_id and api_key
    )
    if should_fetch_events:
        events = _fetch_events(api_key, int(fixture_id))
        new_ids = await _upsert_events(pool, match_row["id"], events, home, away)
        if new_ids:
            await _notify_goal_events(
                pool, match_row["id"], new_ids,
                home_short=home, away_short=away,
                home_goals=int(hg), away_goals=int(ag),
                minute=int(elapsed) if elapsed is not None else 0,
            )
    return True


async def _notify_full_time(pool: asyncpg.Pool) -> int:
    """Post a Telegram (+ push) summary for any match that just went final
    but we haven't notified about yet. Idempotent via matches.ft_notified_at.

    The message carries: final score + model pick + hit/miss + deep link.
    Only matches that kicked off in the last 6h are eligible so we don't
    spam-backfill after a DB migration or long outage.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH latest AS (
                SELECT DISTINCT ON (p.match_id)
                    p.match_id, p.p_home_win, p.p_draw, p.p_away_win
                FROM predictions p
                ORDER BY p.match_id, p.created_at DESC
            )
            SELECT m.id, m.kickoff_time, m.league_code, m.home_goals, m.away_goals,
                   m.minute,
                   ht.short_name AS home_short, ht.slug AS home_slug, ht.name AS home_name,
                   at.short_name AS away_short, at.slug AS away_slug, at.name AS away_name,
                   l.p_home_win, l.p_draw, l.p_away_win
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            LEFT JOIN latest l ON l.match_id = m.id
            WHERE m.status = 'final'
              AND m.home_goals IS NOT NULL
              AND m.away_goals IS NOT NULL
              AND m.ft_notified_at IS NULL
              AND m.kickoff_time > NOW() - INTERVAL '6 hours'
            ORDER BY m.kickoff_time ASC
            LIMIT 20
            """,
        )

    if not rows:
        return 0

    notified = 0
    for r in rows:
        match_id = r["id"]

        # Compute model pick / hit (tolerant of missing prediction rows).
        if r["p_home_win"] is None:
            pick = None
            hit = None
            conf = 0.0
        else:
            probs = {
                "H": float(r["p_home_win"]),
                "D": float(r["p_draw"]),
                "A": float(r["p_away_win"]),
            }
            pick = max(probs, key=probs.get)
            conf = probs[pick]

        hg, ag = int(r["home_goals"]), int(r["away_goals"])
        actual = "H" if hg > ag else "A" if ag > hg else "D"
        hit = pick is not None and pick == actual

        prefix = _league_prefix(r.get("league_code"))
        home_short = r["home_short"].replace("_", "\\_")
        away_short = r["away_short"].replace("_", "\\_")

        if pick is None:
            pick_line = ""
        else:
            pick_label = (
                home_short if pick == "H"
                else away_short if pick == "A"
                else "Hòa"
            )
            verdict_tag = "✓ ĐÚNG" if hit else "✗ SAI"
            pick_line = (
                f"\n⚫ Model dự đoán *{pick_label}* ({round(conf * 100)}%) — *{verdict_tag}*"
            )

        text = (
            f"🏁 *FULL TIME* · {prefix}\n"
            f"*{home_short} {hg}-{ag} {away_short}*"
            f"{pick_line}\n\n"
            f"[Xem phân tích](https://predictor.nullshift.sh/match/{match_id})"
        )

        posted_ok = True
        if token and chat_id:
            try:
                result = _telegram_post(token, chat_id, text)
                posted_ok = bool(result.get("ok"))
                if not posted_ok:
                    print(f"[live-scores] FT telegram api error for {match_id}: {result}")
            except Exception as e:
                posted_ok = False
                print(f"[live-scores] FT telegram failed for {match_id}: {type(e).__name__}: {e}")
        else:
            # No creds set — don't block the DB flag; treat as 'notified' so
            # we don't loop forever trying to post.
            pass

        # Web push (best-effort, independent of Telegram).
        try:
            from app.api.push import dispatch_goal
            if hit is True:
                body = f"Đúng kèo! {home_short} {hg}-{ag} {away_short}"
            elif hit is False:
                body = f"Miss kèo. {home_short} {hg}-{ag} {away_short}"
            else:
                body = f"{home_short} {hg}-{ag} {away_short}"
            await dispatch_goal(
                pool,
                [r["home_slug"], r["away_slug"]],
                {
                    "title": f"🏁 FT · {home_short} {hg}-{ag} {away_short}",
                    "body": body,
                    "url": f"https://predictor.nullshift.sh/match/{match_id}",
                },
            )
        except Exception as e:
            print(f"[live-scores] FT push failed for {match_id}: {type(e).__name__}: {e}")

        # Always mark notified — even if telegram failed — so we don't spam
        # retry on every 10s tick. Missed FT posts are acceptable; duplicate
        # posts are not.
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE matches SET ft_notified_at = NOW() WHERE id = $1", match_id,
            )
        if posted_ok:
            notified += 1

    return notified


async def _flip_stuck_live_to_final(pool: asyncpg.Pool) -> int:
    """Cleanup: matches stuck at status='live' after API-Football dropped them.

    API-Football removes a fixture from `/fixtures?live=all` the moment the
    referee blows full-time. If that response never carries the FT transition
    (e.g. the ingest timer skipped the one cycle it would've caught the
    change), our DB row stays at status='live' forever. Visible symptom: UI
    shows "LIVE 90'" on a match that ended hours ago.

    We flip to 'final' any row where:
      * status='live'
      * live_updated_at is older than 90s (9 missed 10s ingest cycles)
      * kickoff_time was more than 105 min ago (90 play + 15 HT; safe
        against half-time network blips)
    Score + minute are preserved — only status flips.
    """
    async with pool.acquire() as conn:
        n = await conn.fetchval(
            """
            WITH flipped AS (
                UPDATE matches
                SET status = 'final', live_updated_at = NOW()
                WHERE status = 'live'
                  AND (live_updated_at IS NULL
                       OR live_updated_at < NOW() - INTERVAL '90 seconds')
                  AND kickoff_time < NOW() - INTERVAL '105 minutes'
                  AND home_goals IS NOT NULL
                  AND away_goals IS NOT NULL
                RETURNING 1
            )
            SELECT COUNT(*) FROM flipped
            """,
        )
    return int(n or 0)


async def run() -> None:
    key = os.environ.get("API_FOOTBALL_KEY")
    if not key:
        print("[live-scores] no API_FOOTBALL_KEY; skipping")
        return

    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        if not await _has_potential_live(pool):
            print("[live-scores] no match within live window; skipping API call")
            return
        fixtures = _fetch(key)  # all top-5 leagues in one call
        print(f"[live-scores] {len(fixtures)} live top-5 league fixtures")
        touched = 0
        for f in fixtures:
            try:
                if await _update(pool, f, key):
                    touched += 1
            except Exception as e:
                print(f"[live-scores] skip fixture: {type(e).__name__}: {e}")
        print(f"[live-scores] updated {touched} rows")

        flipped = await _flip_stuck_live_to_final(pool)
        if flipped:
            print(f"[live-scores] flipped {flipped} stale live rows → final")

        ft_posts = await _notify_full_time(pool)
        if ft_posts:
            print(f"[live-scores] posted {ft_posts} full-time notifications")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    asyncio.run(run())


if __name__ == "__main__":
    main()
