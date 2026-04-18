# Deploy — VPS (API + DB) and Cloudflare Pages (frontend)

End-to-end path from an empty VPS to `predictor.nullshift.sh` live.

## Backend (VPS)

Requires Docker + docker compose. Any x86 or ARM VPS with a public IP and at least 1 GB RAM works.

```bash
git clone <repo> epl-lab && cd epl-lab
cp .env.example .env
# fill POSTGRES_PASSWORD, DASHSCOPE_API_KEY (and optionally ANTHROPIC_API_KEY)

docker compose up -d db
# wait ~5s for the pg_isready healthcheck to pass
docker compose up -d --build api

docker compose exec api python scripts/ingest_season.py --season 2024-25
docker compose exec api python -c "
import asyncio
from app.predict.service import predict_all_upcoming
from app.core.config import get_settings
from app.core.db import lifespan  # noqa
import asyncpg
async def run():
    s = get_settings()
    pool = await asyncpg.create_pool(s.database_url)
    ids = await predict_all_upcoming(pool, rho=s.default_rho, model_version=s.model_version)
    print(f'wrote {len(ids)} predictions')
    await pool.close()
asyncio.run(run())
"
```

Put Caddy (or Nginx) in front of `127.0.0.1:8000` for TLS. Minimal `Caddyfile`:

```
api.predictor.nullshift.sh {
    reverse_proxy 127.0.0.1:8000
}
```

## Frontend (Cloudflare Pages)

From the Cloudflare dashboard → Pages → Connect to Git:

- **Root directory**: `frontend`
- **Build command**: `npm run build`
- **Build output**: `.next` (Cloudflare Pages with Next.js adapter auto-detects)
- **Env var**: `NEXT_PUBLIC_API_URL=https://api.predictor.nullshift.sh`

First deploy will build server components and deploy to `predictor.nullshift.sh` once the custom domain is attached.

## Recurring ingestion

A weekly GitHub Actions cron hitting the ingest endpoint is the plan (see roadmap Phase 3). For now, run the ingest + prediction commands via `docker compose exec api` weekly by hand — a two-minute job.

## Backups

```bash
docker compose exec -T db pg_dump -U epl -d epl --clean | gzip > epl_$(date +%Y-%m-%d).sql.gz
```

Store off-box (rsync, rclone). Restore:

```bash
gunzip < epl_YYYY-MM-DD.sql.gz | docker compose exec -T db psql -U epl -d epl
```
