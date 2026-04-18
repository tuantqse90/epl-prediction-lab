#!/usr/bin/env bash
# Weekly refresh run by systemd timer (see football-predict-weekly.*).
# Idempotent: ingest upserts, backtest skips matches already predicted.
set -euo pipefail

cd /opt/football-predict

SEASON="${SEASON:-2025-26}"
HORIZON_DAYS="${HORIZON_DAYS:-14}"

echo "[weekly] season=$SEASON horizon=$HORIZON_DAYS"

run() {
  echo "[weekly] $*"
  docker compose exec -T api "$@"
}

run python scripts/ingest_season.py     --season "$SEASON"
run python scripts/ingest_players.py    --season "$SEASON"
run python scripts/ingest_odds.py       --season "$SEASON"
run python scripts/ingest_live_odds.py  --season "$SEASON" || true   # tolerate missing key / quota
run python scripts/backtest.py            --season "$SEASON"
run python scripts/post_telegram_recap.py --days 7 || true               # skip if no token
run python scripts/predict_upcoming.py    --horizon-days "$HORIZON_DAYS" --with-reasoning
run python scripts/post_telegram.py       --horizon-days "$HORIZON_DAYS" || true   # skip if no token

echo "[weekly] done"
