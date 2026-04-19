# Ops recovery runbook

> What to do if the VPS dies, the deploy key is lost, or the `.env` goes up
> in smoke. Read this once; keep a copy of `~/.config/football-predict/`
> outside this repo.

---

## 1. Credentials inventory

All secrets live outside git. Back these up to a password manager (1Password /
Bitwarden / local keychain):

| Secret | Where on local | Where on VPS | Notes |
|---|---|---|---|
| Hostinger VPS root password | `~/.config/football-predict/deploy.env` | n/a | Reset via hpanel.hostinger.com if lost |
| Hostinger VPS IP/hostname | same file | n/a | |
| VPS SSH key (deploy) | `~/.ssh/football-predict-local` + `.pub` | `~/.ssh/football-predict-deploy` (GitHub deploy key) | Regenerate + re-register if lost |
| GitHub deploy key title | n/a | `hostinger-vps-srv1589451` (read-only) | Rotate via `gh repo deploy-key` |
| `POSTGRES_PASSWORD` | `.env.example` has placeholder | `/opt/football-predict/.env` | Changing requires DB re-dump |
| `DASHSCOPE_API_KEY` | in VPS .env only | `/opt/football-predict/.env` | Qwen chat + reasoning |
| `API_FOOTBALL_KEY` | VPS only | `/opt/football-predict/.env` | 7500 req/day Ultra |
| `THE_ODDS_API_KEY` | VPS only | `/opt/football-predict/.env` | Live match odds |
| `TELEGRAM_BOT_TOKEN` / `CHAT_ID` | VPS only | `/opt/football-predict/.env` | Channel + goal alerts |
| `VAPID_PUBLIC_KEY` / `PRIVATE_KEY` | VPS only | `/opt/football-predict/.env` | Web push; regeneration invalidates all existing subs |
| `X_API_*` (4 keys) | VPS only | `/opt/football-predict/.env` | Empty until the X bot launches |
| `NEXT_PUBLIC_PLAUSIBLE_*` | VPS only | `/opt/football-predict/.env` | Empty until analytics onboarded |

### Back up VPS `.env` once a week

From local, with password in the local deploy.env:

```sh
set -a; source ~/.config/football-predict/deploy.env; set +a
SSHPASS=$VPS_SSHPASS sshpass -e ssh -o PreferredAuthentications=password \
  -o PubkeyAuthentication=no root@$VPS_HOST \
  'cat /opt/football-predict/.env' \
  > ~/.config/football-predict/vps-env.backup.$(date +%Y%m%d)
```

---

## 2. If the VPS is gone (new host)

1. Spin up a fresh Ubuntu 22+ with Docker + docker-compose installed.
2. Copy `.env` backup into `/opt/football-predict/.env`.
3. Add **new deploy key** to GitHub via `gh repo deploy-key add`, store the
   matching private key in `~/.ssh/football-predict-deploy` on the new VPS.
4. `git clone ssh://github.com/tuantqse90/epl-prediction-lab.git /opt/football-predict`.
5. Initialize the bare repo for push-to-deploy:
   ```sh
   git init --bare /srv/git/football-predict.git
   # copy ops/football-predict-*.timer/service to /etc/systemd/system/
   systemctl daemon-reload
   for t in live lineups news daily weekly ops-alert; do
     systemctl enable --now football-predict-$t.timer
   done
   ```
6. Apply all migrations in order:
   ```sh
   for f in db/migrations/*.sql; do
     docker compose exec -T db psql -U epl -d epl < "$f"
   done
   ```
7. Re-seed data:
   ```sh
   docker compose exec -T api python scripts/ingest_season.py   --season 2025-26 --league epl
   docker compose exec -T api python scripts/ingest_players.py  --season 2025-26 --league epl
   docker compose exec -T api python scripts/ingest_odds.py     --season 2025-26 --league epl
   # ... repeat for laliga / seriea / bundesliga / ligue1
   docker compose exec -T api python scripts/ingest_news.py
   docker compose exec -T api python scripts/ingest_injuries.py --season 2025-26
   docker compose exec -T api python scripts/ingest_weather.py
   docker compose exec -T api python scripts/predict_upcoming.py --horizon-days 14 --with-reasoning
   ```
8. Update Cloudflare / Caddy / DNS → new VPS IP.
9. Restore the local SSH alias in `~/.ssh/config`:
   ```
   Host football-predict-vps
     HostName <new-ip>
     User root
     Port 22
     IdentityFile ~/.ssh/football-predict-local
   ```
10. `git remote set-url vps football-predict-vps:/srv/git/football-predict.git`.

---

## 3. If the deploy key is revoked

GitHub → repo → Settings → Deploy keys → delete old key → regenerate:

```sh
ssh-keygen -t ed25519 -f ~/.ssh/football-predict-deploy -N "" -C "football-predict-deploy-$(hostname)"
gh repo deploy-key add ~/.ssh/football-predict-deploy.pub \
  --repo tuantqse90/epl-prediction-lab --title "vps-$(date +%Y%m%d)"
```

Copy the private key onto the VPS and update `~/.ssh/config` there:

```
Host github-footballpredict
  HostName github.com
  User git
  IdentityFile ~/.ssh/football-predict-deploy
  IdentitiesOnly yes
```

Test: `ssh -T github-footballpredict` should say "Hi tuantqse90/..., authenticated".

---

## 4. If /health is down

1. Telegram ops-alert should fire within 15 min — check `@worldcup_predictor`.
2. SSH in, check:
   ```sh
   docker compose ps
   docker compose logs api --tail 200
   docker compose logs web --tail 200
   systemctl status football-predict-live.timer
   ```
3. Common fixes:
   - `docker compose restart api` — hangs usually clear.
   - `docker compose up -d --force-recreate api` — if env changed.
   - Check `/api/admin/status` for quota + ingest freshness.

---

## 5. Routine backups (should happen automatically; verify once a month)

- **DB dump**: `docker compose exec -T db pg_dump -U epl -d epl | gzip > /opt/backups/epl-$(date +%Y%m%d).sql.gz`
- **XGBoost model**: `/tmp/football-predict-xgb.json` — regenerable via `python scripts/train_xgboost.py`.
- **Deploy keys + `.env`** — external password manager only.
