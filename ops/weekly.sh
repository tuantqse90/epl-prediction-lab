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

LEAGUES="${LEAGUES:-epl laliga seriea bundesliga ligue1}"

for lg in $LEAGUES; do
  echo "[weekly] === league=$lg ==="
  run python scripts/ingest_season.py  --season "$SEASON" --league "$lg"
  run python scripts/ingest_players.py --season "$SEASON" --league "$lg" || true
  run python scripts/ingest_odds.py    --season "$SEASON" --league "$lg" || true
done

# live odds + backtest + predict + telegram are league-agnostic: they iterate
# internally over LEAGUES / match.league_code, so a single pass covers all 5.
run python scripts/ingest_live_odds.py   --season "$SEASON" || true
run python scripts/backtest.py            --season "$SEASON"
run python scripts/post_telegram_recap.py --days 7 || true
run python scripts/predict_upcoming.py    --horizon-days "$HORIZON_DAYS" --with-reasoning
run python scripts/post_telegram.py       --horizon-days "$HORIZON_DAYS" || true

echo "[weekly] done"
