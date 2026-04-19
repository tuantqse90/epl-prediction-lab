#!/usr/bin/env bash
# systemd-triggered lineups refresh. Quota-self-limiting via the script's
# 3-hour window filter.
set -euo pipefail
cd /opt/football-predict
docker compose exec -T api python scripts/ingest_lineups.py --window-minutes 180 2>&1
