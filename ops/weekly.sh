#!/usr/bin/env bash
# Weekly refresh run by systemd timer (see football-predict-weekly.*).
# Idempotent: ingest upserts, backtest skips matches already predicted.
set -euo pipefail

cd /opt/football-predict

SEASON="${SEASON:-2025-26}"
HORIZON_DAYS="${HORIZON_DAYS:-14}"

echo "[weekly] season=$SEASON horizon=$HORIZON_DAYS"

# Wait for api container to be exec-able before starting. Prevents
# cascade abort when the weekly cron fires during a deploy window.
wait_for_api() {
  local tries=0
  while [ $tries -lt 24 ]; do
    if docker compose exec -T api python -c "import sys; sys.exit(0)" 2>/dev/null; then
      echo "[weekly] api ready"
      return 0
    fi
    echo "[weekly] waiting for api container… (try $tries/24)"
    sleep 5
    tries=$((tries + 1))
  done
  echo "[weekly] api container did not come up in 120s; continuing anyway"
  return 0
}
wait_for_api

run() {
  echo "[weekly] $*"
  docker compose exec -T api "$@"
}

LEAGUES="${LEAGUES:-epl laliga seriea bundesliga ligue1}"

# `|| true` on every line so one failing league doesn't abort the
# whole weekly run via set -e.
for lg in $LEAGUES; do
  echo "[weekly] === league=$lg ==="
  run python scripts/ingest_season.py  --season "$SEASON" --league "$lg" || true
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
run python scripts/train_xgboost.py      --holdout-season "$SEASON" || true

run python scripts/backtest.py            --season "$SEASON" || true
run python scripts/post_telegram_recap.py --days 7 || true
run python scripts/predict_upcoming.py    --horizon-days "$HORIZON_DAYS" --with-reasoning || true
run python scripts/post_telegram.py       --horizon-days "$HORIZON_DAYS" || true

# Per-team SEO narratives — Qwen-Plus writes 500-700-word stories per
# team once a week. Keyed on (team_slug, season); skips teams refreshed
# in the last 6 days so a mid-week re-run of weekly.sh costs nothing.
run python scripts/generate_team_narratives.py --limit 200 || true

# Weekly auto-blog: "Week N: what the model learned". Idempotent via
# slug (week-N-YYYY); a mid-week re-run does nothing unless --force.
run python scripts/generate_weekly_blog.py || true

# Reddit cross-post — only fires when the 5 REDDIT_* env vars are set.
# Conservative: 1 thread per subreddit per week. See growth-playbook.md
# for subreddit selection guidance before adding heavy hitters.
run python scripts/post_reddit_weekly.py || true

echo "[weekly] done"
