#!/usr/bin/env bash
# One-shot setup for Cloudflare R2 off-site backup. Run once on the VPS
# after you've created an R2 API token with Admin Read+Write scope.
#
# Required env (export before running):
#   R2_ACCOUNT_ID           32-char hex, from CF dashboard → R2 (top right)
#   R2_ACCESS_KEY_ID        issued by R2 → Manage R2 API Tokens → Create
#   R2_SECRET_ACCESS_KEY    displayed once, same screen as the key
#   R2_BUCKET (optional)    defaults to football-predict-backups
#
# The script:
#   1. Installs rclone if missing
#   2. Writes /root/.config/rclone/rclone.conf with the [r2] remote
#   3. Creates the bucket if it doesn't exist
#   4. Smoke-tests by uploading + deleting a 1-byte probe file
#
# After this, ops/backup_db.sh auto-uploads each daily dump.
set -euo pipefail

: "${R2_ACCOUNT_ID:?set R2_ACCOUNT_ID first}"
: "${R2_ACCESS_KEY_ID:?set R2_ACCESS_KEY_ID first}"
: "${R2_SECRET_ACCESS_KEY:?set R2_SECRET_ACCESS_KEY first}"
R2_BUCKET="${R2_BUCKET:-football-predict-backups}"

if ! command -v rclone >/dev/null 2>&1; then
  echo "[r2] installing rclone …"
  curl -fsSL https://rclone.org/install.sh | bash
fi

mkdir -p /root/.config/rclone
cat > /root/.config/rclone/rclone.conf <<CFG
[r2]
type = s3
provider = Cloudflare
access_key_id = $R2_ACCESS_KEY_ID
secret_access_key = $R2_SECRET_ACCESS_KEY
endpoint = https://$R2_ACCOUNT_ID.r2.cloudflarestorage.com
acl = private
CFG
chmod 600 /root/.config/rclone/rclone.conf
echo "[r2] rclone.conf written"

# Bucket create (idempotent — ignore 'already exists').
if rclone lsjson "r2:$R2_BUCKET" --max-depth 1 >/dev/null 2>&1; then
  echo "[r2] bucket $R2_BUCKET already exists"
else
  echo "[r2] creating $R2_BUCKET …"
  rclone mkdir "r2:$R2_BUCKET"
fi

# Smoke test.
PROBE=/tmp/r2-probe-$$
echo ok > "$PROBE"
rclone copyto "$PROBE" "r2:$R2_BUCKET/probe-$(date +%s)" --s3-no-check-bucket
rclone delete "r2:$R2_BUCKET/probe-*" --include 'probe-*' || true
rm -f "$PROBE"

echo "[r2] smoke test passed"
echo "[r2] append R2_BUCKET=$R2_BUCKET to /opt/football-predict/.env if you want backup_db.sh to pick it up (default matches)."
