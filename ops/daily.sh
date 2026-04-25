#!/usr/bin/env bash
# Daily refresh — run by systemd timer at 06:00 UTC.
# Purpose: catch midweek fixtures that the Monday weekly cron missed, so
# every league has fresh predictions + reasoning without waiting 7 days.
set -euo pipefail

cd /opt/football-predict

SEASON="${SEASON:-2025-26}"
HORIZON_DAYS="${HORIZON_DAYS:-7}"

echo "[daily] season=$SEASON horizon=$HORIZON_DAYS"

# The daily cron runs at 06:00 UTC — a common deploy window. If the api
# container is mid-restart the first 'docker compose exec' will fail with
# 'service api is not running' and, under set -e, abort the whole script.
# Wait up to 120s for the container to be up + responding before starting.
wait_for_api() {
  local tries=0
  while [ $tries -lt 24 ]; do
    if docker compose exec -T api python -c "import sys; sys.exit(0)" 2>/dev/null; then
      echo "[daily] api ready"
      return 0
    fi
    echo "[daily] waiting for api container… (try $tries/24)"
    sleep 5
    tries=$((tries + 1))
  done
  echo "[daily] api container did not come up in 120s; continuing anyway"
  return 0
}
wait_for_api

run() {
  echo "[daily] $*"
  docker compose exec -T api "$@"
}

# Sync fixture IDs + kickoff times against API-Football's canonical
# schedule. TV-broadcast reschedules (e.g. Man City shifted a day) and
# missing af_ids otherwise silently break live tracking. ~5 API calls.
run python scripts/backfill_fixture_ids.py --days 30 || true

# Referee names propagate via live-scores + lineups ingest, but any
# fixture that slipped past both cron windows is left with referee NULL.
# Cheap — one /fixtures page per active (league, season) ≈ 5 API calls.
run python scripts/backfill_referees.py --season "$SEASON" || true

# Resolve any match stuck in 'scheduled' past kickoff. Catches matches
# the live ingest never saw (quota, outage) so the ops watchdog doesn't
# flag them forever. ~1 API call per stuck match, bounded to 20/tick.
run python scripts/finalise_missed_matches.py --max 20 || true

# UCL + UEL daily refresh — high-audience Tue/Wed matchdays. Cheap call
# count: ~2 league-season pulls + ~N odds pages. Script is idempotent
# (upsert by af fixture id).
EUROPE_SEASON_YEAR="${EUROPE_SEASON_YEAR:-2025}"
run python scripts/ingest_european_cups.py --season "$EUROPE_SEASON_YEAR" --league ALL || true

# News headlines (RSS, no API cost)
run python scripts/ingest_news.py || true

# Injuries refresh (cheap, 5 calls/day)
run python scripts/ingest_injuries.py --season "$SEASON" || true

# Player photos via API-Football topscorers endpoint — 10 calls/day,
# keeps the homepage Star Players strip fresh with new transfers /
# new top-scorer rosters.
run python scripts/ingest_player_photos.py --season "$SEASON" || true

# Full-squad photo sweep (once daily). ~100 API calls total: 5 for
# team-id resolution (only runs once per team), then ~95 team-squad
# pulls. Covers every player on team pages, not just top-20 scorers.
run python scripts/ingest_full_squad_photos.py --season "$SEASON" || true

# Weather forecast for matches in the next 48h (open-meteo, no key)
run python scripts/ingest_weather.py --window-minutes 2880 || true

# Player season stats (xG, goals, assists) refresh — weekly was leaving
# /scorers and /players 4-7 days stale after a gameweek. Understat is
# free + rate-limited so 5 league calls daily is cheap.
for LG in epl laliga seriea bundesliga ligue1; do
  run python scripts/ingest_players.py --season "$SEASON" --league "$LG" || true
done

# Ensure every scheduled match in window has a prediction + reasoning.
# predict_all_upcoming iterates league-agnostic by match.league_code.
run python scripts/predict_upcoming.py --horizon-days "$HORIZON_DAYS" --with-reasoning || true

# Post-match LLM recaps for finals in the last 7d (cheap, idempotent).
run python scripts/generate_recaps.py --days 7 --limit 120 || true

# Phase 42.1 — long-form match stories (Qwen-Plus, ~$0.02/call).
# Scoped to last 14 days + cap 30/day so a catch-up batch doesn't blow
# the budget. Idempotent via `story IS NULL` guard.
run python scripts/generate_stories.py --days 14 --limit 30 || true

# IndexNow bulk re-submission — bumps every NewsArticle (story) URL
# to Bing/Yandex once a day. The on-write hook in app/llm/story.py
# already pings them as new stories land; this is the catch-up sweep.
run python scripts/submit_indexnow.py || true

# Social distribution — tolerated failure (missing creds, rate limit, etc.)
run python scripts/post_twitter.py --horizon-days 3 --threshold 0.07 --max 5 || true
run python scripts/post_twitter_recap.py || true
run python scripts/post_telegram_digest.py --horizon-hours 24 --threshold 0.05 --max 3 || true

echo "[daily] done"
