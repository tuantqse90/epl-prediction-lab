#!/usr/bin/env bash
# Freshness-critical refresh — runs every 4h (00, 04, 08, 12, 16, 20 UTC).
# Catches:
#   - new fixtures showing up in API-Football mid-day (TV reschedules)
#   - matches stuck in 'scheduled' past kickoff (live cron quota miss)
#   - Understat xG that lands 24-72h after a match
#   - injuries reported close to kickoff
#   - new finals needing predictions / recaps / stories
#
# What we DON'T run here (lives in daily.sh): photo sweeps, weather,
# news (own 30-min timer), social broadcasts, restore drill, IndexNow
# bulk. Those are heavier and don't gain by running 6× / day.
set -euo pipefail

cd /opt/football-predict

SEASON="${SEASON:-2025-26}"
HORIZON_DAYS="${HORIZON_DAYS:-7}"

echo "[hourly] season=$SEASON horizon=$HORIZON_DAYS"

wait_for_api() {
  local tries=0
  while [ $tries -lt 24 ]; do
    if docker compose exec -T api python -c "import sys; sys.exit(0)" 2>/dev/null; then
      echo "[hourly] api ready"
      return 0
    fi
    echo "[hourly] waiting for api container… (try $tries/24)"
    sleep 5
    tries=$((tries + 1))
  done
  echo "[hourly] api container did not come up in 120s; continuing anyway"
  return 0
}
wait_for_api

run() {
  echo "[hourly] $*"
  docker compose exec -T api "$@"
}

# Fixture-list drift sync (TV reschedules, missing af_ids).
run python scripts/backfill_fixture_ids.py --days 14 || true

# Resolve any match stuck in 'scheduled' past kickoff.
run python scripts/finalise_missed_matches.py --max 20 || true

# Injuries — cheap, 5 calls/run, kickoff-relevant.
run python scripts/ingest_injuries.py --season "$SEASON" || true

# Understat xG for top-5 finals. Each call is idempotent UPSERT;
# Understat refreshes its match-xG ~24-72h after kickoff so a 4-h
# cadence catches it the same day instead of waiting 6 days for
# the Monday weekly cycle.
for LG in epl laliga seriea bundesliga ligue1; do
  run python scripts/ingest_season.py --season "$SEASON" --league "$LG" || true
done

# Predictions for any new fixture that just appeared.
run python scripts/predict_upcoming.py --horizon-days "$HORIZON_DAYS" --with-reasoning || true

# Post-match recaps + long-form stories. Both idempotent on existing
# rows; ingest_live_scores.py also fires these on FT, this is the
# catch-up for any failure.
run python scripts/generate_recaps.py --days 7 --limit 60 || true
run python scripts/generate_stories.py --days 7 --limit 12 || true

# Translate fresh stories to other langs (~$0.005/lang/story).
run python scripts/translate_stories.py --days 7 --limit 8 \
    --langs en,th,zh,ko || true

echo "[hourly] done"
