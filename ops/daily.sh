#!/usr/bin/env bash
# Daily refresh — run by systemd timer at 06:00 UTC.
# Purpose: catch midweek fixtures that the Monday weekly cron missed, so
# every league has fresh predictions + reasoning without waiting 7 days.
set -euo pipefail

cd /opt/football-predict

SEASON="${SEASON:-2025-26}"
HORIZON_DAYS="${HORIZON_DAYS:-7}"

echo "[daily] season=$SEASON horizon=$HORIZON_DAYS"

run() {
  echo "[daily] $*"
  docker compose exec -T api "$@"
}

# Sync fixture IDs + kickoff times against API-Football's canonical
# schedule. TV-broadcast reschedules (e.g. Man City shifted a day) and
# missing af_ids otherwise silently break live tracking. ~5 API calls.
run python scripts/backfill_fixture_ids.py --days 30 || true

# Resolve any match stuck in 'scheduled' past kickoff. Catches matches
# the live ingest never saw (quota, outage) so the ops watchdog doesn't
# flag them forever. ~1 API call per stuck match, bounded to 20/tick.
run python scripts/finalise_missed_matches.py --max 20 || true

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
run python scripts/predict_upcoming.py --horizon-days "$HORIZON_DAYS" --with-reasoning

# Post-match LLM recaps for finals in the last 7d (cheap, idempotent).
run python scripts/generate_recaps.py --days 7 --limit 120 || true

# Social distribution — tolerated failure (missing creds, rate limit, etc.)
run python scripts/post_twitter.py --horizon-days 3 --threshold 0.07 --max 5 || true
run python scripts/post_twitter_recap.py || true
run python scripts/post_telegram_digest.py --horizon-hours 24 --threshold 0.05 --max 3 || true

echo "[daily] done"
