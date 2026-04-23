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

# live odds + injuries + backtest + predict + telegram are league-agnostic:
# each iterates internally over LEAGUES / match.league_code.
run python scripts/ingest_live_odds.py   --season "$SEASON" || true
run python scripts/ingest_injuries.py    --season "$SEASON" || true

# Retrain XGBoost on all prior seasons so the booster stays fresh as new
# matches accumulate. Holdout is the current season → honest out-of-sample
# metrics on every retrain. Saved to the persistent /data volume, picked
# up automatically by the api service (lazy-loaded via XGB_MODEL_PATH).
run python scripts/train_xgboost.py      --holdout-season "$SEASON"

run python scripts/backtest.py            --season "$SEASON"
run python scripts/post_telegram_recap.py --days 7 || true
run python scripts/predict_upcoming.py    --horizon-days "$HORIZON_DAYS" --with-reasoning
run python scripts/post_telegram.py       --horizon-days "$HORIZON_DAYS" || true

# Per-team SEO narratives — Qwen-Plus writes 500-700-word stories per
# team once a week. Keyed on (team_slug, season); skips teams refreshed
# in the last 6 days so a mid-week re-run of weekly.sh costs nothing.
run python scripts/generate_team_narratives.py --limit 200 || true

echo "[weekly] done"
