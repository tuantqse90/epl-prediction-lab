#!/usr/bin/env bash
# One-shot deploy from local workspace → Hostinger VPS. Bypasses GitHub.
#
# Reads VPS creds from ~/.config/football-predict/deploy.env:
#   VPS_HOST=76.13.183.138
#   VPS_USER=root
#   VPS_SSHPASS=...
#   VPS_PORT=22   # optional
#
# Usage:
#   ./ops/deploy.sh            # rsync + rebuild api + web + smoke test
#   ./ops/deploy.sh --fast     # skip rebuild, just rsync + restart
set -euo pipefail

cd "$(dirname "$0")/.."

CREDS="${FOOTBALL_PREDICT_DEPLOY_ENV:-$HOME/.config/football-predict/deploy.env}"
if [ ! -f "$CREDS" ]; then
  echo "Missing $CREDS — create it with VPS_HOST, VPS_USER, VPS_SSHPASS." >&2
  exit 1
fi
# shellcheck disable=SC1090
set -a; . "$CREDS"; set +a

: "${VPS_HOST:?}"; : "${VPS_USER:?}"; : "${VPS_SSHPASS:?}"
VPS_PORT="${VPS_PORT:-22}"
REMOTE_DIR="${REMOTE_DIR:-/opt/football-predict}"
FAST="${1:-}"

if ! command -v sshpass >/dev/null; then
  echo "sshpass not found — brew install sshpass" >&2
  exit 1
fi

SSHPASS="$VPS_SSHPASS"; export SSHPASS
SSH="sshpass -e ssh -p $VPS_PORT -o StrictHostKeyChecking=accept-new"
RSH="sshpass -e ssh -p $VPS_PORT -o StrictHostKeyChecking=accept-new"

echo "--- rsync → $VPS_USER@$VPS_HOST:$REMOTE_DIR ---"
COMMON_EXCLUDES=(
  --exclude ".git/"
  --exclude ".env" --exclude ".env.*"
  --exclude "node_modules/" --exclude ".next/" --exclude "out/"
  --exclude ".venv/" --exclude "__pycache__/" --exclude "*.pyc"
)

for dir in backend frontend ops db; do
  rsync -az --delete -e "$RSH" "${COMMON_EXCLUDES[@]}" \
    "$dir/" "$VPS_USER@$VPS_HOST:$REMOTE_DIR/$dir/"
done
rsync -az -e "$RSH" docker-compose.yml "$VPS_USER@$VPS_HOST:$REMOTE_DIR/"

$SSH "$VPS_USER@$VPS_HOST" "cd $REMOTE_DIR && chmod +x ops/*.sh 2>/dev/null || true"

if [ "$FAST" = "--fast" ]; then
  echo "--- fast mode: restart only ---"
  $SSH "$VPS_USER@$VPS_HOST" "cd $REMOTE_DIR && docker compose restart api web"
else
  echo "--- docker compose build api web ---"
  $SSH "$VPS_USER@$VPS_HOST" "cd $REMOTE_DIR && docker compose build api web"

  echo "--- docker compose up -d ---"
  $SSH "$VPS_USER@$VPS_HOST" "cd $REMOTE_DIR && docker compose up -d --remove-orphans && docker image prune -f | tail -1"
fi

echo "--- smoke test ---"
$SSH "$VPS_USER@$VPS_HOST" "
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS --max-time 3 http://127.0.0.1:8500/health >/dev/null 2>&1; then
    echo 'api: ok'; break
  fi
  [ \$i = 10 ] && echo 'api: timeout'
  sleep 2
done
curl -fsS --max-time 5 http://127.0.0.1:3500 >/dev/null 2>&1 && echo 'web: ok' || echo 'web: failed'
"

echo "--- done $(date -u +%FT%TZ) ---"
