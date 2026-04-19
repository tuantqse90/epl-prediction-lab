# Deploy — Shared Hostinger VPS (API + DB + Web)

End-to-end path to `predictor.nullshift.sh` live. No Cloudflare Pages, no Railway, no Fly — one VPS runs everything and a shared Caddy fronts TLS.

## Topology

- **VPS**: Hostinger `srv1589451.hstgr.cloud` (`76.13.183.138`), shared with other Nullshift/Shinhan stacks (ai-hub, bi, fin, docflow, tasco-drive, nullvote). Convention: each app lives under `/opt/<name>/` with its own `docker-compose.yml` + `.env` (mode 600, not committed) and `COMPOSE_PROJECT_NAME=<name>` to namespace containers.
- **App root**: `/opt/football-predict/`
- **Containers**:
  - `api` — FastAPI, internal port 8000 → host port **8500** (`127.0.0.1`-bound)
  - `web` — Next.js 15 standalone, internal port 3000 → host port **3500** (`127.0.0.1`-bound)
  - `football-predict-db-1` — `pgvector/pgvector:pg16`, **no host port** (internal-only, reached via compose network)
- **Volume**: `football-predict_pgdata`
- **Caddy** (owned by host, shared across projects) — single hostname, path-routed:
  ```
  predictor.nullshift.sh {
      handle /api/* { reverse_proxy 127.0.0.1:8500 }
      handle /docs* { reverse_proxy 127.0.0.1:8500 }
      handle /openapi.json { reverse_proxy 127.0.0.1:8500 }
      handle { reverse_proxy 127.0.0.1:3500 }
  }
  ```
- **DNS**: Cloudflare A record `predictor.nullshift.sh → 76.13.183.138`, **unproxied** (orange-cloud off — same as sibling Shinhan subdomains).

## Deploy flow (bare-repo push)

The VPS hosts a **bare git repo** at `/srv/git/football-predict.git`. A `post-receive` hook (mirrored in `infra/deploy/`) runs on every push to `main`:

1. Fetch the new ref into the working tree at `/opt/football-predict/`
2. `docker compose build api web`
3. `docker compose up -d --remove-orphans`
4. Wait for `/health` on `api` and a 200 on `web`'s root
5. Log `[deploy] done <timestamp>`

From dev:

```bash
git remote add vps football-predict-vps:/srv/git/football-predict.git   # one-time
git push vps main
```

`football-predict-vps` is an SSH alias defined in `~/.ssh/config`. Secrets live in `/opt/football-predict/.env` on the VPS (mode 600, never copied locally, never committed). `POSTGRES_PASSWORD` was generated on-box via `openssl rand -hex 20`.

## First-time VPS setup

```bash
# on the VPS
sudo mkdir -p /srv/git/football-predict.git
cd /srv/git/football-predict.git
sudo git init --bare
sudo cp /path/to/infra/deploy/post-receive hooks/post-receive
sudo chmod +x hooks/post-receive

sudo mkdir -p /opt/football-predict
# drop .env in /opt/football-predict/.env (mode 600)

# first push from dev triggers the hook which does the rest
```

## Initial data seed (one-time)

```bash
ssh football-predict-vps
cd /opt/football-predict
docker compose exec api python scripts/ingest_season.py --season 2025-26 --league eng.1
docker compose exec api python scripts/ingest_season.py --season 2025-26 --league esp.1
# … repeat for ger.1, ita.1, fra.1
docker compose exec api python scripts/predict_upcoming.py
```

## Ongoing ingestion

Systemd timers on the VPS (defined under `ops/systemd/`):

- `ingest-live-scores.timer` — every 10s during match windows, skip-unchanged-optimised
- `ingest-lineups.timer` — every 15m, 3h pre-KO
- `ingest-injuries.timer` — daily 04:00 local
- `ingest-bookmaker-odds.timer` — daily 02:00
- `ingest-live-odds.timer` — every 2h during fixture week
- `ingest-weather.timer` — T-2h per scheduled match
- `weekly.timer` — Monday 08:00 → `ops/weekly.sh` (recap post + backtest + predict_upcoming)

GitHub Actions mirrors a weekly nightly `pg_dump` to off-box storage.

## Backups

```bash
# nightly on VPS
docker compose exec -T db pg_dump -U epl -d epl --clean | gzip \
  > /srv/backups/football-predict/epl_$(date +%Y-%m-%d).sql.gz

# restore
gunzip < epl_YYYY-MM-DD.sql.gz | docker compose exec -T db psql -U epl -d epl
```

## Notes / gotchas

- **DashScope (Qwen) intl endpoint**: must use `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`, **not** the `.cn` one. LiteLLM config hardcodes this in `app/core/llm.py`.
- **The Odds API** free tier is 500 calls/mo. `ingest_live_odds.py` respects a per-match dedup window and a daily cap; the live cron will skip if over quota.
- **Hostinger shared VPS**: other stacks share the network namespace, so always pick host ports in the 3500–3999 / 8500–8999 range for this project to avoid collisions with nullvote (8600), tasco-drive (3600), etc.
- **Port exposure**: `db` has no host binding on purpose — only `api` reaches it via the compose network. Never expose Postgres directly.
