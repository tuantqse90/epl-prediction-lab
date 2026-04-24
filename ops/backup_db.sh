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

# Rotation — keep last 14 dailies, last 8 weeklies locally.
echo "[backup] rotating local …"
ls -1t "$BACKUP_DIR"/epl-daily-*.sql.gz 2>/dev/null | awk 'NR>14' | xargs -r rm -v
ls -1t "$BACKUP_DIR"/epl-weekly-*.sql.gz 2>/dev/null | awk 'NR>8' | xargs -r rm -v

# Off-site mirror — Cloudflare R2 if rclone + the [r2] remote are
# configured. The remote is set up separately (one-shot) via:
#   /root/.config/rclone/rclone.conf containing account_id + keys.
# If rclone isn't installed or the [r2] remote is missing we skip
# silently; the local dump still succeeded.
#
# Remote retention is more generous than local: 60 dailies + 26 weeklies
# (6 months of Sunday snapshots) — R2 storage is $0.015/GB/mo, cheap.
R2_BUCKET="${R2_BUCKET:-football-predict-backups}"
if command -v rclone >/dev/null 2>&1 \
   && rclone listremotes 2>/dev/null | grep -q '^r2:$'; then
  echo "[backup] uploading to r2:$R2_BUCKET …"
  if rclone copyto "$FINAL_FILE" "r2:$R2_BUCKET/$(basename "$FINAL_FILE")" \
       --s3-no-check-bucket --quiet; then
    echo "[backup] r2 ok"
    if [ "$DOW" = "7" ]; then
      rclone copyto "$WEEKLY_FILE" "r2:$R2_BUCKET/$(basename "$WEEKLY_FILE")" \
        --s3-no-check-bucket --quiet || true
    fi
    # Remote rotation.
    echo "[backup] rotating remote …"
    rclone ls "r2:$R2_BUCKET" --include "epl-daily-*.sql.gz" 2>/dev/null \
      | awk '{print $2}' | sort | head -n -60 \
      | while read -r f; do rclone delete "r2:$R2_BUCKET/$f" || true; done
    rclone ls "r2:$R2_BUCKET" --include "epl-weekly-*.sql.gz" 2>/dev/null \
      | awk '{print $2}' | sort | head -n -26 \
      | while read -r f; do rclone delete "r2:$R2_BUCKET/$f" || true; done
  else
    echo "[backup] r2 upload FAILED — local copy still intact"
  fi
else
  echo "[backup] r2 not configured; skipping off-site mirror"
fi

echo "[backup] done"
