#!/usr/bin/env bash
# Daily pg_dump to /var/backups/football-predict with rotation.
#
# Retention policy:
#   - last 14 daily dumps
#   - last 8 weekly dumps (Sunday-stamped)
#   Rotation runs at the end; any older file is deleted.
#
# Dumps are compressed (gzip -9) — typical size ~20 MB for the current
# schema (13k matches, 15k predictions, 45k events). pg_dump is run via
# `docker compose exec db` so it uses the container's Postgres binaries
# matching the server version — avoids the "server/client version
# mismatch" errors you get from host pg_dump against a containerised db.
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/football-predict}"
TIMESTAMP=$(date -u +%Y%m%d-%H%M%S)
DOW=$(date -u +%u)  # 1=Monday, 7=Sunday

mkdir -p "$BACKUP_DIR"

cd /opt/football-predict

# Dump via the db container (uses Postgres 16 client matching the server).
TMP_FILE="$BACKUP_DIR/epl-$TIMESTAMP.sql.gz.tmp"
FINAL_FILE="$BACKUP_DIR/epl-daily-$TIMESTAMP.sql.gz"

echo "[backup] dumping → $TMP_FILE"
docker compose exec -T db bash -c \
  'pg_dump --clean --no-owner --no-privileges -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip -9' \
  > "$TMP_FILE"

SIZE=$(stat -c%s "$TMP_FILE" 2>/dev/null || stat -f%z "$TMP_FILE")
if [ "$SIZE" -lt 1048576 ]; then
  echo "[backup] FAIL — dump only $SIZE bytes, aborting" >&2
  rm -f "$TMP_FILE"
  exit 1
fi

mv "$TMP_FILE" "$FINAL_FILE"
echo "[backup] ok → $FINAL_FILE ($(numfmt --to=iec "$SIZE" 2>/dev/null || echo "$SIZE bytes"))"

# Sunday → also promote this dump to a weekly snapshot.
if [ "$DOW" = "7" ]; then
  WEEKLY_FILE="$BACKUP_DIR/epl-weekly-$TIMESTAMP.sql.gz"
  cp "$FINAL_FILE" "$WEEKLY_FILE"
  echo "[backup] also promoted to weekly: $WEEKLY_FILE"
fi

# Rotation — keep last 14 dailies, last 8 weeklies.
echo "[backup] rotating …"
ls -1t "$BACKUP_DIR"/epl-daily-*.sql.gz 2>/dev/null | awk 'NR>14' | xargs -r rm -v
ls -1t "$BACKUP_DIR"/epl-weekly-*.sql.gz 2>/dev/null | awk 'NR>8' | xargs -r rm -v

echo "[backup] done"
