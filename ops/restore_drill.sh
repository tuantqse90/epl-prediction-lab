#!/usr/bin/env bash
# Weekly proof-of-restore drill: pick the newest daily dump, gunzip it
# into a throwaway scratch postgres container, run a handful of count
# queries that must return > 0. If anything's wrong (dump corrupted,
# restore fails, schema empty) exit non-zero so the ops-alert cron
# surfaces it.
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/football-predict}"

LATEST=$(ls -1t "$BACKUP_DIR"/epl-daily-*.sql.gz 2>/dev/null | head -1 || true)
if [ -z "$LATEST" ]; then
  echo "[drill] no daily backups in $BACKUP_DIR" >&2
  exit 2
fi
echo "[drill] using $LATEST"

CONTAINER="fb-pg-drill-$$"
trap 'docker rm -f "$CONTAINER" >/dev/null 2>&1 || true' EXIT

docker run -d --rm --name "$CONTAINER" \
  -e POSTGRES_PASSWORD=drill \
  -e POSTGRES_DB=drilldb \
  postgres:16-alpine >/dev/null

# Wait up to 30s for Postgres to accept connections.
for _ in $(seq 1 30); do
  if docker exec "$CONTAINER" pg_isready -U postgres -q; then
    break
  fi
  sleep 1
done

echo "[drill] restoring …"
gunzip -c "$LATEST" | docker exec -i "$CONTAINER" \
  psql -U postgres -d drilldb -q >/dev/null

# Sanity queries — each must return > 0 rows.
for q in \
  "SELECT count(*) FROM matches" \
  "SELECT count(*) FROM predictions" \
  "SELECT count(*) FROM teams" \
  "SELECT count(*) FROM match_odds";
do
  n=$(docker exec "$CONTAINER" psql -U postgres -d drilldb -tA -c "$q")
  echo "[drill] $q → $n"
  if [ -z "$n" ] || [ "$n" -le 0 ]; then
    echo "[drill] FAIL — zero rows on \`$q\`" >&2
    exit 3
  fi
done

echo "[drill] PASS"
