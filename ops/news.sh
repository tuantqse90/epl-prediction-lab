#!/usr/bin/env bash
# Systemd-triggered news refresh. RSS feeds only, no paid API cost.
set -euo pipefail
cd /opt/football-predict
docker compose exec -T api python scripts/ingest_news.py 2>&1
