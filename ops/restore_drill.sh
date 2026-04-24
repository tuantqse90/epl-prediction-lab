#!/usr/bin/env bash
# Weekly proof-of-restore drill. Restores the newest daily dump into a
# throwaway scratch postgres and asserts row counts > 0. Two modes:
#
#   DRILL_SOURCE=r2      → pull the latest dump from Cloudflare R2 (real
#                          disaster-recovery path: VPS burns, we'd restore
#                          from object storage)
#   DRILL_SOURCE=local   → use the newest dump in /var/backups (faster,
#                          catches pg_dump corruption without the R2 hop)
#   DRILL_SOURCE=auto    → default; R2 if configured, else local
#
# Exit codes:
#   0  PASS
#   2  no backup available (neither source has a dump)
#   3  restore completed but a sanity query returned 0 rows
#   4  R2 download failed
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/football-predict}"
R2_BUCKET="${R2_BUCKET:-football-predict-backups}"
SOURCE="${DRILL_SOURCE:-auto}"

r2_available() {
  command -v rclone >/dev/null 2>&1 \
    && rclone listremotes 2>/dev/null | grep -q '^r2:$' \
    && rclone lsjson "r2:$R2_BUCKET" --max-depth 1 >/dev/null 2>&1
}

if [ "$SOURCE" = "auto" ]; then
  if r2_available; then SOURCE=r2; else SOURCE=local; fi
fi

case "$SOURCE" in
  r2)
    echo "[drill] source=r2 (disaster-recovery path)"
    if ! r2_available; then
      echo "[drill] r2 not configured; run r2_bootstrap.sh first" >&2
      exit 4
    fi
    # Pick the lexicographically-last daily (timestamps sort alphanumerically).
    REMOTE_KEY=$(rclone ls "r2:$R2_BUCKET" --include "epl-daily-*.sql.gz" \
                   | awk '{print $2}' | sort | tail -1)
    if [ -z "$REMOTE_KEY" ]; then
      echo "[drill] no daily backups in r2:$R2_BUCKET" >&2
      exit 2
    fi
    WORK=$(mktemp -d)
    trap 'rm -rf "$WORK"; docker rm -f "$CONTAINER" >/dev/null 2>&1 || true' EXIT
    echo "[drill] downloading r2:$R2_BUCKET/$REMOTE_KEY → $WORK/"
    if ! rclone copyto "r2:$R2_BUCKET/$REMOTE_KEY" "$WORK/$REMOTE_KEY"; then
      echo "[drill] r2 download failed" >&2
      exit 4
    fi
    LATEST="$WORK/$REMOTE_KEY"
    ;;
  local)
    echo "[drill] source=local (fast path)"
    LATEST=$(ls -1t "$BACKUP_DIR"/epl-daily-*.sql.gz 2>/dev/null | head -1 || true)
    if [ -z "$LATEST" ]; then
      echo "[drill] no daily backups in $BACKUP_DIR" >&2
      exit 2
    fi
    trap 'docker rm -f "$CONTAINER" >/dev/null 2>&1 || true' EXIT
    ;;
  *)
    echo "[drill] unknown DRILL_SOURCE=$SOURCE (expected: auto, r2, local)" >&2
    exit 1
    ;;
esac

echo "[drill] using $(basename "$LATEST") ($(stat -c%s "$LATEST" 2>/dev/null | numfmt --to=iec 2>/dev/null || echo "?") )"

CONTAINER="fb-pg-drill-$$"

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

echo "[drill] PASS (source=$SOURCE)"
