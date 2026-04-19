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

# Injuries refresh (cheap, 5 calls/day)
run python scripts/ingest_injuries.py --season "$SEASON" || true

# Weather forecast for matches in the next 48h (open-meteo, no key)
run python scripts/ingest_weather.py --window-minutes 2880 || true

# Ensure every scheduled match in window has a prediction + reasoning.
# predict_all_upcoming iterates league-agnostic by match.league_code.
run python scripts/predict_upcoming.py --horizon-days "$HORIZON_DAYS" --with-reasoning

echo "[daily] done"
