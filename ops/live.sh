#!/usr/bin/env bash
# Polls API-Football for live EPL scores. Invoked every 2 min by systemd timer.
# The Python script self-gates against quota: if no match is inside the
# 150-min-before-now → now+5 window, it exits without calling the API.
set -euo pipefail

cd /opt/football-predict
docker compose exec -T api python scripts/ingest_live_scores.py
