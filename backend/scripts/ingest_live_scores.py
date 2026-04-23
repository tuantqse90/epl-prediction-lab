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
    "Oviedo": "Real Oviedo",
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
    "FSV Mainz 05": "Mainz 05",
    "1899 Hoffenheim": "Hoffenheim",
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
    """Return True when polling is warranted.

    Ultra plan = 150k req/day; cadence budget is a non-issue. We still
    gate off completely-idle periods so logs stay clean, but the window
    is generous — any match kicked off in the last 150 min or starting
    within 10 min is worth polling. Even if API-Football already marked
    it final, the call is cheap and picks up the FT transition.
    """
    return bool(await pool.fetchval(
        """
        SELECT EXISTS(
            SELECT 1 FROM matches
            WHERE status = 'live'
               OR (status != 'final'
                   AND kickoff_time BETWEEN NOW() - INTERVAL '150 minutes'
                                        AND NOW() + INTERVAL '10 minutes')
        )
        """,
    ))


# Stop polling only when we're truly about to hit the wall. Ultra plan =
# 150,000 req/day; a 500 floor still leaves ~3 hours of headroom at peak
# weekend burn (~200 req/min) while catching runaway misconfigs early.
_QUOTA_FLOOR = 500


def _fetch(key: str, league_id: int | None = None) -> list[dict] | None:
    """Poll API-Football for live fixtures. Returns None if the daily quota
    is nearly exhausted (fewer than _QUOTA_FLOOR left) so the caller can
    back off for the rest of the UTC day."""
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    req = urllib.request.Request(url, headers={"x-apisports-key": key})
    with urllib.request.urlopen(req, timeout=20) as resp:
        remaining = resp.headers.get("x-ratelimit-requests-remaining")
        if remaining:
            try:
                left = int(remaining)
                if left < _QUOTA_FLOOR:
                    print(f"[live-scores] quota critical: {left} remaining — backing off")
                    return None
                print(f"[live-scores] quota remaining: {left}")
            except ValueError:
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


def _fetch_stats(key: str, fixture_id: int) -> list[dict]:
    """Per-team live stats (possession, shots, corners, fouls, offsides,
    passes, passes-accuracy, saves). One API request per match — quota
    cost means we throttle which matches get stats, not every tick."""
    url = f"https://v3.football.api-sports.io/fixtures/statistics?fixture={fixture_id}"
    req = urllib.request.Request(url, headers={"x-apisports-key": key})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read())
        return body.get("response", []) or []
    except Exception as e:
        print(f"[live-scores] stats fetch failed for {fixture_id}: {type(e).__name__}")
        return []


# Cache per-process so we don't re-pull stats for the same match every tick.
# Tuple of (fixture_id, epoch_seconds) — when True, it's time to pull again.
_STATS_COOLDOWN_SEC = 30
_stats_last_pull: dict[int, float] = {}


def _should_pull_stats(fixture_id: int) -> bool:
    import time
    now = time.time()
    last = _stats_last_pull.get(fixture_id, 0.0)
    if now - last >= _STATS_COOLDOWN_SEC:
        _stats_last_pull[fixture_id] = now
        return True
    return False


async def _upsert_stats(
    pool: asyncpg.Pool, match_id: int, fixture_response: list[dict],
    home_api_name: str, away_api_name: str,
) -> None:
    """Collapse API-Football's per-team stats array into a compact JSON
    blob on matches.live_stats. Normalized names: possession_pct,
    shots_total, shots_on, corners, fouls, offsides, passes_pct, saves."""
    def _row_for(team_name: str) -> dict:
        for t in fixture_response:
            if (t.get("team") or {}).get("name", "") == team_name:
                return _pack_stats(t.get("statistics") or [])
        return {}

    def _pack_stats(arr: list[dict]) -> dict:
        m: dict = {}
        for s in arr:
            typ = (s.get("type") or "").lower()
            val = s.get("value")
            if val is None:
                continue
            if "ball possession" in typ:
                m["possession_pct"] = str(val).rstrip("%")
            elif typ == "total shots":
                m["shots_total"] = val
            elif typ == "shots on goal":
                m["shots_on"] = val
            elif typ == "corner kicks":
                m["corners"] = val
            elif typ == "fouls":
                m["fouls"] = val
            elif typ == "offsides":
                m["offsides"] = val
            elif typ == "passes %":
                m["passes_pct"] = str(val).rstrip("%")
            elif typ == "goalkeeper saves":
                m["saves"] = val
            elif typ == "expected_goals":
                m["xg"] = val
        return m

    packed = {
        "home": _row_for(home_api_name),
        "away": _row_for(away_api_name),
    }
    # Skip the DB write when we got nothing useful — saves noise in logs.
    if not packed["home"] and not packed["away"]:
        return
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE matches
            SET live_stats = $2::jsonb, live_stats_updated_at = NOW()
            WHERE id = $1
            """,
            match_id, json.dumps(packed),
        )


async def _upsert_events(
    pool: asyncpg.Pool, match_id: int, events: list[dict], home: str, away: str,
) -> list[int]:
    """Upsert events into match_events; return event IDs that were *actually* inserted
    (i.e. not silenced by the ON CONFLICT DO NOTHING idempotency guard).

    Dedup tolerance: API-Football occasionally revises an event's minute by ±1
    between polls (e.g. 38' → 37' for the same goal). The DB's unique index
    keys off exact minute, so a revised row would sneak in as a new event and
    re-trigger Telegram notification. We SELECT for a near-duplicate first
    (same match / type / player / detail / within ±EVENT_MINUTE_TOLERANCE
    minutes) and skip insert when found — optionally patching the minute on
    the existing row so the UI shows the latest value.
    """
    if not events:
        return []
    EVENT_MINUTE_TOLERANCE = 3
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
                minute = time_info.get("elapsed")
                extra = time_info.get("extra")
                player = (player_info.get("name") or "").strip() or None
                assist = (assist_info.get("name") or "").strip() or None
                event_type = e.get("type", "").strip()
                event_detail = (e.get("detail") or "").strip() or None

                # Tolerance dedup: match_id + event_type + player + detail
                # within ±N minutes collapses two polls' worth of the same
                # event into one row. Non-matching players are still inserted
                # as new events (so two unrelated yellow cards at 35' vs 37'
                # both land).
                existing_id = None
                if minute is not None:
                    # asyncpg serialises bare ints as "unknown" type and
                    # postgres refuses to pick an operator for unknown-unknown
                    # arithmetic. Pre-compute the tolerance window in Python
                    # so the SQL sees two concrete ints.
                    low = int(minute) - EVENT_MINUTE_TOLERANCE
                    high = int(minute) + EVENT_MINUTE_TOLERANCE
                    existing_id = await conn.fetchval(
                        """
                        SELECT id FROM match_events
                        WHERE match_id = $1
                          AND event_type = $2
                          AND COALESCE(player_name, '') = COALESCE($3, '')
                          AND COALESCE(event_detail, '') = COALESCE($4, '')
                          AND COALESCE(team_slug, '') = COALESCE($5, '')
                          AND minute BETWEEN $6 AND $7
                        ORDER BY id ASC
                        LIMIT 1
                        """,
                        match_id, event_type, player, event_detail, team_slug,
                        low, high,
                    )
                if existing_id is not None:
                    # Keep the canonical (earliest) row; don't re-notify.
                    continue

                new_id = await conn.fetchval(
                    """
                    INSERT INTO match_events (
                        match_id, minute, extra_minute, team_slug,
                        player_name, assist_name, event_type, event_detail
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT DO NOTHING
                    RETURNING id
                    """,
                    match_id, minute, extra, team_slug,
                    player, assist, event_type, event_detail,
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


def _telegram_edit(token: str, chat_id: str, message_id: int, text: str) -> dict:
    """Edit an already-posted message. Used to enrich an instant goal post
    with the scorer's name once /fixtures/events resolves (~1s later)."""
    import urllib.parse

    url = f"https://api.telegram.org/bot{token}/editMessageText"
    body = urllib.parse.urlencode({
        "chat_id": chat_id,
        "message_id": message_id,
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

    # Instant goal notification — fires the moment we see the score change,
    # BEFORE the /fixtures/events roundtrip (which adds ~1s and only
    # contributes player/assist names). Player-level detail still populates
    # the frontend via the subsequent events upsert; the Telegram side just
    # gets "X scored, it's now 2-1 at 67'" in real time.
    #
    # Guards:
    #   * prev_hg/prev_ag == NULL → first-time seeing this match, establish
    #     a baseline without posting. Prevents "Có bàn thắng!" on match boot.
    #   * score went *down* (VAR cancels a goal) → don't celebrate; skip.
    #   * Idempotent via the prev score check: once posted, the score is
    #     identical next tick so score_changed is False.
    prev_hg_raw = match_row["prev_hg"]
    prev_ag_raw = match_row["prev_ag"]
    is_first_reading = prev_hg_raw is None or prev_ag_raw is None
    prev_hg = int(prev_hg_raw) if prev_hg_raw is not None else 0
    prev_ag = int(prev_ag_raw) if prev_ag_raw is not None else 0
    scored_home = int(hg) > prev_hg
    scored_away = int(ag) > prev_ag
    should_notify_goal = (
        score_changed
        and not is_first_reading
        and (scored_home or scored_away)
    )
    # `meta` becomes non-None only when dedupe accepted the score for a
    # *new* Telegram post; the subsequent block uses that to send the
    # message. But we MUST continue to the /fixtures/events fetch below
    # regardless — otherwise skipped duplicate-notifications would also
    # skip updating match_events, leaving the events panel missing goals.
    meta = None
    if should_notify_goal:
        # Atomic dedupe: append the current score to notified_scores and
        # return non-NULL ONLY if it wasn't already there. Guards against
        # (a) two ingest ticks racing, (b) API-Football momentarily
        # returning stale/flap data (0→1→0→1), and (c) a restart where
        # in-memory score_changed state is lost. One row per unique score
        # per match, ever.
        score_key = f"{int(hg)}-{int(ag)}"
        async with pool.acquire() as conn:
            meta = await conn.fetchrow(
                """
                UPDATE matches m
                SET notified_scores = array_append(m.notified_scores, $2)
                FROM teams ht, teams at
                WHERE m.id = $1
                  AND ht.id = m.home_team_id
                  AND at.id = m.away_team_id
                  AND NOT ($2 = ANY(m.notified_scores))
                RETURNING m.league_code,
                          ht.short_name AS home_short, ht.slug AS home_slug,
                          at.short_name AS away_short, at.slug AS away_slug
                """,
                match_row["id"], score_key,
            )

    if meta is not None:

        minute_label = f"{elapsed}'" if elapsed is not None else "—"
        prefix = _league_prefix(meta["league_code"])
        home_short = meta["home_short"].replace("_", "\\_")
        away_short = meta["away_short"].replace("_", "\\_")

        if scored_home and scored_away:
            # Extremely rare edge case (2-goal jump from missed update).
            lead = "⚽ *Có bàn thắng!*"
        elif scored_home:
            lead = f"⚽ *{home_short}* ghi bàn!"
        else:
            lead = f"⚽ *{away_short}* ghi bàn!"

        text = (
            f"{lead}  _{minute_label}_\n"
            f"{prefix} · *{home_short} {int(hg)}-{int(ag)} {away_short}*\n"
            f"[Xem live](https://predictor.nullshift.sh/match/{match_row['id']})"
        )
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        posted_message_id: int | None = None
        if token and chat_id:
            try:
                result = _telegram_post(token, chat_id, text)
                if result.get("ok"):
                    posted_message_id = int(result["result"]["message_id"])
                else:
                    print(f"[live-scores] instant goal tg api error for {match_row['id']}: {result}")
            except Exception as e:
                print(f"[live-scores] instant goal tg failed for {match_row['id']}: {type(e).__name__}: {e}")

        # Stash so the subsequent /fixtures/events enrichment can edit the
        # same message with the scorer's name — no second Telegram message
        # needed, we just update the first one in place.
        if posted_message_id is not None:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE matches
                    SET last_goal_message_id = $2, last_goal_score = $3
                    WHERE id = $1
                    """,
                    match_row["id"], posted_message_id, score_key,
                )
        try:
            from app.api.push import dispatch_goal
            await dispatch_goal(
                pool,
                [meta["home_slug"], meta["away_slug"]],
                {
                    "title": f"⚽ {home_short} {int(hg)}-{int(ag)} {away_short}",
                    "body": f"{minute_label}",
                    "url": f"https://predictor.nullshift.sh/match/{match_row['id']}",
                },
            )
        except Exception as e:
            print(f"[live-scores] instant goal push failed: {type(e).__name__}: {e}")

        try:
            from app.api.telegram import fan_out_to_team_subscribers
            fan_text = (
                f"⚽ *{home_short} {int(hg)}-{int(ag)} {away_short}* "
                f"_{minute_label}_\n"
                f"https://predictor.nullshift.sh/match/{match_row['id']}"
            )
            await fan_out_to_team_subscribers(
                pool,
                team_slugs=[meta["home_slug"], meta["away_slug"]],
                text=fan_text,
            )
        except Exception as e:
            print(f"[live-scores] team-sub fanout failed: {type(e).__name__}: {e}")

        try:
            from app.api.discord import fan_out_to_discord
            discord_text = (
                f"⚽ **{home_short.replace('\\_','_')} {int(hg)}-{int(ag)} "
                f"{away_short.replace('\\_','_')}** · {minute_label}\n"
                f"<https://predictor.nullshift.sh/match/{match_row['id']}>"
            )
            await fan_out_to_discord(
                pool,
                team_slugs=[meta["home_slug"], meta["away_slug"]],
                content=discord_text,
                kind="goal",
            )
        except Exception as e:
            print(f"[live-scores] discord fanout failed: {type(e).__name__}: {e}")

    # Only hit /fixtures/events when something interesting changed. Most
    # polling cycles (90%+) see a static scoreline — skipping events there
    # lets us poll aggressively without blowing API-Football quota.
    should_fetch_events = (
        (score_changed or status_changed)
        and db_status in ("live", "final")
        and fixture_id and api_key
    )
    # Live stats pull — throttled to once every _STATS_COOLDOWN_SEC per
    # match so six concurrent live fixtures cost ≤12 req/min total.
    if db_status == "live" and fixture_id and api_key and _should_pull_stats(int(fixture_id)):
        stats_resp = _fetch_stats(api_key, int(fixture_id))
        if stats_resp:
            try:
                await _upsert_stats(
                    pool, match_row["id"], stats_resp,
                    teams["home"]["name"], teams["away"]["name"],
                )
            except Exception as e:
                print(f"[live-scores] stats upsert failed for {match_row['id']}: {type(e).__name__}: {e}")

    if should_fetch_events:
        events = _fetch_events(api_key, int(fixture_id))
        new_ids = await _upsert_events(pool, match_row["id"], events, home, away)
        if new_ids:
            # Mark newly-upserted Goal events as notified — the instant
            # notify above already posted the message, so the legacy
            # _notify_goal_events path should never fire for these.
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE match_events
                    SET notified_at = NOW()
                    WHERE id = ANY($1::int[])
                      AND event_type = 'Goal'
                      AND notified_at IS NULL
                    """,
                    new_ids,
                )

            # Enrichment: if we have a pending instant-goal message on this
            # match, edit it to include the scorer. Picks the newest Goal
            # event we just inserted as the scorer (events come back ordered
            # by time, so the last one is the most recent goal).
            await _enrich_goal_message_with_scorer(
                pool, match_row["id"], new_ids, home, away, int(hg), int(ag),
            )
    return True


async def _enrich_goal_message_with_scorer(
    pool: asyncpg.Pool,
    match_id: int,
    new_event_ids: list[int],
    home_name: str,
    away_name: str,
    hg: int,
    ag: int,
) -> None:
    """Edit the instant-goal Telegram message to include the scorer's name.

    Called right after /fixtures/events resolves. Finds the pending message
    id stashed on matches.last_goal_message_id, pulls the newest Goal event
    among the just-inserted rows, and rewrites the Telegram post with
    '⚽ Scorer  67'  Home 2-1 Away' formatting.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        return

    score_key = f"{hg}-{ag}"
    async with pool.acquire() as conn:
        # Find the newest Goal event among the ones we just inserted.
        scorer_row = await conn.fetchrow(
            """
            SELECT e.player_name, e.assist_name, e.minute, e.extra_minute,
                   e.team_slug, e.event_detail
            FROM match_events e
            WHERE e.id = ANY($1::int[])
              AND e.event_type = 'Goal'
            ORDER BY COALESCE(e.minute, 0) DESC,
                     COALESCE(e.extra_minute, 0) DESC,
                     e.id DESC
            LIMIT 1
            """,
            new_event_ids,
        )
        # Pull the pending message id + team display data in one shot.
        meta = await conn.fetchrow(
            """
            SELECT m.last_goal_message_id, m.last_goal_score, m.league_code,
                   ht.short_name AS home_short, ht.slug AS home_slug,
                   at.short_name AS away_short, at.slug AS away_slug
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.id = $1
            """,
            match_id,
        )

    if meta is None or not meta["last_goal_message_id"]:
        return
    if meta["last_goal_score"] != score_key:
        # Message on file is for a different score — another goal already
        # arrived before enrichment. Skip this edit; the newer instant post
        # will have its own enrichment cycle.
        return
    if scorer_row is None or not scorer_row["player_name"]:
        return

    player = scorer_row["player_name"].replace("_", "\\_")
    own_goal = (scorer_row["event_detail"] or "").lower() == "own goal"
    penalty = (scorer_row["event_detail"] or "").lower() == "penalty"
    min_raw = scorer_row["minute"]
    extra = scorer_row["extra_minute"]
    if min_raw is not None and extra:
        minute_label = f"{min_raw}+{extra}'"
    elif min_raw is not None:
        minute_label = f"{min_raw}'"
    else:
        minute_label = "—"

    badge = ""
    if own_goal:
        badge = " (phản lưới)"
    elif penalty:
        badge = " (phạt đền)"

    assist_raw = scorer_row["assist_name"] if not own_goal else None
    assist_line = ""
    if assist_raw:
        assist_line = f"\n🅰️ Kiến tạo: {assist_raw.replace('_', chr(92)+'_')}"

    prefix = _league_prefix(meta["league_code"])
    home_short = meta["home_short"].replace("_", "\\_")
    away_short = meta["away_short"].replace("_", "\\_")

    # Figure out which team scored from the event's team_slug.
    if scorer_row["team_slug"] == meta["home_slug"]:
        scoring = home_short
    elif scorer_row["team_slug"] == meta["away_slug"]:
        scoring = away_short
    else:
        scoring = "⚽"

    # Qwen-powered 1-sentence commentary. Sync call adds ~500-900ms to this
    # enrichment cycle; acceptable because the instant post already fired.
    # Returns None on LLM outage — we just skip the line.
    from app.llm.goal_commentary import goal_commentary as _commentary
    commentary = _commentary(
        home_team=home_name, away_team=away_name,
        home_goals=hg, away_goals=ag,
        scorer=scorer_row["player_name"], assist=assist_raw,
        minute=min_raw if min_raw is not None else 0,
        league=meta["league_code"],
        is_own_goal=own_goal, is_penalty=penalty,
    )
    commentary_line = f"\n💬 _{commentary}_" if commentary else ""

    new_text = (
        f"⚽ *{scoring}* — {player}{badge}  _{minute_label}_\n"
        f"{prefix} · *{home_short} {hg}-{ag} {away_short}*"
        f"{assist_line}"
        f"{commentary_line}\n"
        f"[Xem live](https://predictor.nullshift.sh/match/{match_id})"
    )

    try:
        result = _telegram_edit(
            token, chat_id, int(meta["last_goal_message_id"]), new_text,
        )
        if not result.get("ok"):
            # Telegram refuses edits with identical body; also a 48h window.
            # Both acceptable no-ops — log and move on.
            desc = result.get("description", "?")
            if "not modified" not in desc.lower():
                print(f"[live-scores] enrich edit tg error for {match_id}: {desc}")
    except Exception as e:
        print(f"[live-scores] enrich edit failed for {match_id}: {type(e).__name__}: {e}")

    # Clear the pending message id so a later non-goal event (card, sub) on
    # the same match doesn't accidentally try to edit this post again.
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE matches SET last_goal_message_id = NULL, last_goal_score = NULL WHERE id = $1",
            match_id,
        )


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
                   m.minute, m.live_stats,
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

        # Scorers: pull Goal events for this match, ordered by minute.
        async with pool.acquire() as conn:
            goal_events = await conn.fetch(
                """
                SELECT minute, extra_minute, player_name, event_detail, team_slug
                FROM match_events
                WHERE match_id = $1 AND event_type = 'Goal'
                  AND player_name IS NOT NULL
                ORDER BY COALESCE(minute, 0), COALESCE(extra_minute, 0), id
                """,
                match_id,
            )
        scorer_lines: list[str] = []
        for g in goal_events:
            mn = g["minute"]
            ex = g["extra_minute"]
            minute_label = f"{mn}+{ex}'" if (mn is not None and ex) else f"{mn}'" if mn is not None else "—"
            badge = ""
            det = (g["event_detail"] or "").lower()
            if det == "own goal":
                badge = " (PL)"  # phản lưới
            elif det == "penalty":
                badge = " (PEN)"
            # Mark with team short-name so "MU scored at 67'" is unambiguous
            # in a mixed-column layout.
            side = (
                home_short if g["team_slug"] and g["team_slug"].startswith(r["home_slug"])
                else away_short if g["team_slug"] and g["team_slug"].startswith(r["away_slug"])
                else ""
            )
            # Fallback: rematch via explicit equality since slugs might not
            # start-match perfectly (e.g. man-utd vs manchester-united).
            if not side and g["team_slug"]:
                if g["team_slug"] == r["home_slug"]:
                    side = home_short
                elif g["team_slug"] == r["away_slug"]:
                    side = away_short
            player = (g["player_name"] or "—").replace("_", "\\_")
            scorer_lines.append(f"┃ _{minute_label:>5}_  *{side or '—'}*  {player}{badge}")
        scorers_block = ""
        if scorer_lines:
            scorers_block = "\n\n⚽ *Bàn thắng*\n" + "\n".join(scorer_lines)

        # Stats block — render only keys present in live_stats JSONB.
        stats_block = ""
        raw_stats = r["live_stats"]
        if raw_stats:
            if isinstance(raw_stats, str):
                try:
                    stats = json.loads(raw_stats)
                except Exception:
                    stats = None
            else:
                stats = raw_stats
            if stats and (stats.get("home") or stats.get("away")):
                h = stats.get("home") or {}
                a = stats.get("away") or {}

                def _row(label: str, key: str, pct: bool = False) -> str | None:
                    hv = h.get(key)
                    av = a.get(key)
                    if hv is None and av is None:
                        return None
                    hv_fmt = f"{hv}%" if pct and hv is not None else str(hv if hv is not None else "—")
                    av_fmt = f"{av}%" if pct and av is not None else str(av if av is not None else "—")
                    return f"{label:<14} {hv_fmt:>5} · {av_fmt:>5}"

                rows_list = [
                    _row("Kiểm soát", "possession_pct", pct=True),
                    _row("Cú sút", "shots_total"),
                    _row("Trúng đích", "shots_on"),
                    _row("Phạt góc", "corners"),
                    _row("Phạm lỗi", "fouls"),
                    _row("Việt vị", "offsides"),
                    _row("Chuyền", "passes_pct", pct=True),
                    _row("Cứu thua", "saves"),
                ]
                rows_list = [x for x in rows_list if x is not None]
                if rows_list:
                    stats_block = (
                        f"\n\n📊 *Thế trận* — {home_short} vs {away_short}\n```\n"
                        + "\n".join(rows_list)
                        + "\n```"
                    )

        # Pre-match probability breakdown (shows model's prior conviction).
        prob_block = ""
        if r["p_home_win"] is not None:
            ph = round(float(r["p_home_win"]) * 100)
            pd_ = round(float(r["p_draw"]) * 100)
            pa = round(float(r["p_away_win"]) * 100)
            prob_block = (
                f"\n🔮 *Dự đoán trước trận:* "
                f"{home_short} {ph}% · Hòa {pd_}% · {away_short} {pa}%"
            )

        # Model verdict + streak counter for the same league.
        streak_block = ""
        pick_line = ""
        if pick is not None:
            pick_label = (
                home_short if pick == "H"
                else away_short if pick == "A"
                else "Hòa"
            )
            verdict_tag = "✅ ĐÚNG" if hit else "❌ SAI"
            pick_line = (
                f"\n⚫ *Chốt của model:* {pick_label} ({round(conf * 100)}%) — *{verdict_tag}*"
            )
            # Streak: wins/total in same league over last 10 scored matches.
            if r.get("league_code"):
                async with pool.acquire() as conn:
                    last10 = await conn.fetch(
                        """
                        WITH latest AS (
                            SELECT DISTINCT ON (p.match_id)
                                p.match_id, p.p_home_win, p.p_draw, p.p_away_win
                            FROM predictions p
                            ORDER BY p.match_id, p.created_at DESC
                        )
                        SELECT m.home_goals, m.away_goals,
                               l.p_home_win, l.p_draw, l.p_away_win
                        FROM matches m
                        JOIN latest l ON l.match_id = m.id
                        WHERE m.league_code = $1
                          AND m.status = 'final'
                          AND m.home_goals IS NOT NULL
                          AND m.kickoff_time > NOW() - INTERVAL '60 days'
                        ORDER BY m.kickoff_time DESC
                        LIMIT 10
                        """,
                        r["league_code"],
                    )
                hits = 0
                total = 0
                for row in last10:
                    probs_i = {"H": float(row["p_home_win"]), "D": float(row["p_draw"]), "A": float(row["p_away_win"])}
                    pick_i = max(probs_i, key=probs_i.get)
                    actual_i = (
                        "H" if row["home_goals"] > row["away_goals"]
                        else "A" if row["home_goals"] < row["away_goals"]
                        else "D"
                    )
                    if pick_i == actual_i:
                        hits += 1
                    total += 1
                if total > 0:
                    streak_block = f"\n🔥 *Streak {prefix}*: {hits}/{total} gần nhất"

        # AI match recap line. Uses Qwen; tolerant of LLM outages (just
        # drops the line quietly).
        recap_block = ""
        try:
            from app.llm.match_recap_line import match_recap_line
            top_h = [g["player_name"] for g in goal_events if g["team_slug"] == r["home_slug"]][:3]
            top_a = [g["player_name"] for g in goal_events if g["team_slug"] == r["away_slug"]][:3]
            line = match_recap_line(
                home_team=r["home_name"], away_team=r["away_name"],
                home_goals=hg, away_goals=ag,
                pre_pick_side=pick, pre_pick_conf=conf if pick else None,
                hit=hit,
                top_scorers_home=top_h, top_scorers_away=top_a,
            )
            if line:
                # Light escaping so the LLM doesn't accidentally break
                # Telegram's legacy Markdown parser.
                safe = line.replace("*", "").replace("_", "").replace("[", "").replace("]", "")
                recap_block = f"\n\n💬 _{safe}_"
        except Exception as e:
            print(f"[live-scores] FT recap line failed for {match_id}: {type(e).__name__}: {e}")

        text = (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏁 *KẾT THÚC* · {prefix}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"\n*{home_short}  {hg}  ━  {ag}  {away_short}*"
            f"{prob_block}"
            f"{scorers_block}"
            f"{stats_block}"
            f"\n{pick_line}"
            f"{streak_block}"
            f"{recap_block}"
            f"\n\n[📊 Xem phân tích đầy đủ](https://predictor.nullshift.sh/match/{match_id})"
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

        try:
            from app.api.telegram import fan_out_to_team_subscribers
            ft_text = (
                f"🏁 *FT · {home_short} {hg}-{ag} {away_short}*\n"
                f"https://predictor.nullshift.sh/match/{match_id}"
            )
            await fan_out_to_team_subscribers(
                pool,
                team_slugs=[r["home_slug"], r["away_slug"]],
                text=ft_text,
            )
        except Exception as e:
            print(f"[live-scores] FT team-sub fanout failed for {match_id}: {type(e).__name__}: {e}")

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


async def _select_finals_needing_recap(pool: asyncpg.Pool) -> list[int]:
    """Recent finals that have an FT notification but no recap yet.

    Window kept tight (6h) so a backlog from an outage doesn't fire a
    burst of LLM calls from the live loop — the daily cron still runs
    `generate_recaps.py --days 7` for longer-range cleanup.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT m.id
            FROM matches m
            WHERE m.status = 'final'
              AND m.home_goals IS NOT NULL
              AND m.recap IS NULL
              AND m.ft_notified_at IS NOT NULL
              AND m.kickoff_time > NOW() - INTERVAL '6 hours'
              AND EXISTS (SELECT 1 FROM predictions p WHERE p.match_id = m.id)
            ORDER BY m.kickoff_time DESC
            """,
        )
    return [int(r["id"]) for r in rows]


async def _generate_recaps_on_ft(
    pool: asyncpg.Pool,
    *,
    selector=_select_finals_needing_recap,
    generator=None,
    limit: int = 5,
) -> int:
    """Generate post-match recaps for any just-finalised match on this tick.

    Bounded by `limit` per tick — a typical matchday has <5 simultaneous
    finishes, but enforcing a ceiling protects the 10s live-scores cadence
    from a worst-case backlog.

    Returns count of successfully-written recaps.
    """
    if generator is None:
        from app.llm.recap import generate_recap
        generator = generate_recap

    match_ids = await selector(pool)
    if not match_ids:
        return 0

    generated = 0
    for mid in match_ids[:limit]:
        try:
            result = await generator(pool, mid)
        except Exception as e:
            print(f"[live-scores] recap failed for {mid}: {type(e).__name__}: {e}")
            continue
        if result:
            generated += 1
    return generated


async def _flip_stuck_live_to_final(pool: asyncpg.Pool) -> int:
    """Cleanup: matches stuck at status='live' after API-Football dropped them.

    Two triggers for flipping to 'final':
      (a) minute ≥ 90 AND live_period ∈ {2H, ET, P} AND stale > 60s — the
          ref blew FT and API-Football dropped the fixture from the live
          feed. Catches almost every match within ~1 minute of the whistle.
      (b) stale > 90s AND kickoff > 95 min ago — fallback for matches whose
          minute field never made it to 90 (feed glitch, early abandonment).
    Score and minute are preserved; only status flips.
    """
    async with pool.acquire() as conn:
        n = await conn.fetchval(
            """
            WITH flipped AS (
                UPDATE matches
                SET status = 'final', live_updated_at = NOW()
                WHERE status = 'live'
                  AND home_goals IS NOT NULL
                  AND away_goals IS NOT NULL
                  AND (
                    -- (a) minute hit 90 during a second-half / ET / pens period
                    (
                      minute IS NOT NULL AND minute >= 90
                      AND live_period IN ('2H', 'ET', 'P')
                      AND (live_updated_at IS NULL
                           OR live_updated_at < NOW() - INTERVAL '60 seconds')
                    )
                    OR
                    -- (b) kickoff long enough ago that it must have ended
                    (
                      kickoff_time < NOW() - INTERVAL '95 minutes'
                      AND (live_updated_at IS NULL
                           OR live_updated_at < NOW() - INTERVAL '90 seconds')
                    )
                  )
                RETURNING 1
            )
            SELECT COUNT(*) FROM flipped
            """,
        )
    return int(n or 0)


async def _notify_halftime(pool: asyncpg.Pool) -> int:
    """Post a Telegram HT message for live matches with live_period='HT'.

    Runs on every ingest tick; idempotent via matches.ht_notified_at.
    Score + current model probs shown (live-mode probs carried through
    the standard live-update path).
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
            SELECT m.id, m.league_code, m.home_goals, m.away_goals,
                   ht.short_name AS home_short, ht.slug AS home_slug,
                   at.short_name AS away_short, at.slug AS away_slug,
                   l.p_home_win, l.p_draw, l.p_away_win
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            LEFT JOIN latest l ON l.match_id = m.id
            WHERE m.status = 'live'
              AND m.live_period = 'HT'
              AND m.ht_notified_at IS NULL
              AND m.home_goals IS NOT NULL
              AND m.kickoff_time > NOW() - INTERVAL '3 hours'
            LIMIT 20
            """,
        )

    if not rows:
        return 0

    notified = 0
    for r in rows:
        match_id = r["id"]
        hg, ag = int(r["home_goals"]), int(r["away_goals"])
        home_short = r["home_short"].replace("_", "\\_")
        away_short = r["away_short"].replace("_", "\\_")
        prefix = _league_prefix(r.get("league_code"))

        # Stored prob row is the pre-match prediction (live probs are
        # computed on-demand from remaining Poisson, not persisted). Label
        # it as such so users don't think we're showing real-time model
        # update at HT.
        probs_line = ""
        if r["p_home_win"] is not None:
            ph = round(float(r["p_home_win"]) * 100)
            pd_ = round(float(r["p_draw"]) * 100)
            pa = round(float(r["p_away_win"]) * 100)
            probs_line = f"\n⚫ Model (pre-match): {home_short} {ph}% · Hòa {pd_}% · {away_short} {pa}%"

        text = (
            f"⏸️ *HẾT HIỆP 1* · {prefix}\n"
            f"*{home_short} {hg}-{ag} {away_short}*"
            f"{probs_line}\n\n"
            f"[Xem chi tiết](https://predictor.nullshift.sh/match/{match_id})"
        )

        posted_ok = True
        if token and chat_id:
            try:
                result = _telegram_post(token, chat_id, text)
                posted_ok = bool(result.get("ok"))
                if not posted_ok:
                    print(f"[live-scores] HT telegram api error for {match_id}: {result}")
            except Exception as e:
                posted_ok = False
                print(f"[live-scores] HT telegram failed for {match_id}: {type(e).__name__}: {e}")

        try:
            from app.api.push import dispatch_goal
            await dispatch_goal(
                pool,
                [r["home_slug"], r["away_slug"]],
                {
                    "title": f"⏸️ HT · {home_short} {hg}-{ag} {away_short}",
                    "body": "Hết hiệp 1",
                    "url": f"https://predictor.nullshift.sh/match/{match_id}",
                },
            )
        except Exception as e:
            print(f"[live-scores] HT push failed for {match_id}: {type(e).__name__}: {e}")

        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE matches SET ht_notified_at = NOW() WHERE id = $1", match_id,
            )
        if posted_ok:
            notified += 1

    return notified


async def run() -> None:
    key = os.environ.get("API_FOOTBALL_KEY")
    if not key:
        print("[live-scores] no API_FOOTBALL_KEY; skipping")
        return

    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        # DB-only cleanups run unconditionally — they don't call API-Football,
        # so they must keep working even when the daily quota is exhausted.
        # Without this, a quota exhaustion would leave matches stuck "LIVE 90'"
        # in the UI until the UTC reset.
        flipped = await _flip_stuck_live_to_final(pool)
        if flipped:
            print(f"[live-scores] flipped {flipped} stale live rows → final")
        ht_posts = await _notify_halftime(pool)
        if ht_posts:
            print(f"[live-scores] posted {ht_posts} half-time notifications")
        ft_posts = await _notify_full_time(pool)
        if ft_posts:
            print(f"[live-scores] posted {ft_posts} full-time notifications")

        # Same tick as FT → recap prose. Without this, recaps waited until
        # the 06:00 UTC daily cron (up to 9h lag for an evening fixture).
        try:
            recaps_written = await _generate_recaps_on_ft(pool)
            if recaps_written:
                print(f"[live-scores] wrote {recaps_written} post-match recaps")
        except Exception as e:
            print(f"[live-scores] recap pass failed: {type(e).__name__}: {e}")

        if not await _has_potential_live(pool):
            print("[live-scores] no match within live window; skipping API call")
            return
        fixtures = _fetch(key)  # all top-5 leagues in one call
        if fixtures is None:
            return
        print(f"[live-scores] {len(fixtures)} live top-5 league fixtures")
        touched = 0
        for f in fixtures:
            try:
                if await _update(pool, f, key):
                    touched += 1
            except Exception as e:
                print(f"[live-scores] skip fixture: {type(e).__name__}: {e}")
        print(f"[live-scores] updated {touched} rows")
    finally:
        await pool.close()


def main() -> None:
    logging.disable(logging.CRITICAL)
    asyncio.run(run())


if __name__ == "__main__":
    main()
