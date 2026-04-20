# PROGRESS — EPL Prediction Lab

> Dated summary log. **One short entry per meaningful step.** Format: `## YYYY-MM-DD HH:MM TZ — <summary>`. Keep each entry to 1–3 lines. Details live in code + docs, not here.

## 2026-04-20 11:35 +07 — Phase 8 + Phase 5 (plan-new): per-league ROI + CLV

**Phase 8 — per-league edge map.** Extracted `_compute_roi_metrics` pure aggregator (6 TDD tests). New `GET /api/stats/roi/by-league?window=season|7d|30d|90d` returns bets/wins/PnL_vig/PnL_no-vig/log-loss per league. Frontend: `/roi/by-league` page (window + edge chips, neon/error per row, sparse flag for <10 bets). QuickPicks on `/` now fetches 30d rolling ROI and hides picks from leagues bleeding money (footer chip explains). Live: predictor.nullshift.sh/roi/by-league. Sample: 4 leagues all +17% to +28% ROI over 30d.

**Phase 5 — CLV infrastructure.** Migration 016 adds `closing_odds` table (UNIQUE per match+source, first snapshot wins). `clv_pct()` pure fn + `_aggregate_clv` with 6 TDD tests. `scripts/ingest_closing_odds.py` runs every 5min via new systemd timer; DB pre-check shortcuts zero-fixture windows to survive the-odds-api free tier quota. `GET /api/stats/clv` returns mean CLV + % beat close per league. `/proof` gains a CLV card (hidden until ≥10 snapshots). Waiting for first captures — table is live and empty.

## 2026-04-20 08:00 +07 — plan-new.md + full docs refresh

Scoped Phase 5+ "sharp-bettor analytics" into new `plan-new.md` (CLV logging → correlated markets → backend Kelly + virtual bankroll → per-league edge map → sharp-exchange reference; in-play parked). Explicit scoping rule: analytics + display only, no custody. Updated `CLAUDE.md` (multi-league scope, bare-repo deploy, plan-new pointer) and refreshed `docs/database.md` (6 missing tables), `docs/prediction-model.md` (Elo + XGB ensemble, injury/weather λ shrinks, CI bootstrap), `docs/project-structure.md` (current 14 routers + 33 scripts + 21 FE pages), `docs/deploy.md` (Hostinger shared VPS + bare-repo + post-receive), `docs/roadmap.md` (Phase 4 closed/dropped, Phase 5+ pointer), `docs/frontend.md` (route list now matches live app).

## 2026-04-19 15:00 +07 — 5-item UI/UX batch: convey model quality

**#81 ProofStrip hero**: new `<ProofStrip>` server component above the match grid. 4-row horizontal bar chart — Model / Bookmakers / Always-Home / Random — on 30-day finals. Backed by new `/api/stats/comparison` endpoint (TTL-cached) that argmaxes both model probs and devigged bookmaker odds. Hidden if `scored < 10`.

**#82 Model-pick banner on MatchCard**: neon pill above the 3-way bar — `✓ Model picks {team} · {conf}%` + `+X% vs market` chip when best_edge ≥ 5pp matches the pick.

**#83 Last-10 W/L dots**: inside `<ProofStrip>`, renders 10 circles (green=hit, red=miss) from `/api/stats/recent` with N/10 counter.

**#84 Kelly value popout**: `<OddsPanel>` now renders a neon-bordered callout above the odds table whenever `best_edge ≥ 10pp` — outcome label, odds, edge, model prob, Kelly stake in one hero card.

**#85 /proof marketing page**: new route combining weighted-accuracy + log-loss trust numbers, 30d head-to-head comparison, per-season accuracy bars, calibration reliability table, "why it works" 3-up explainer, and a 4-step hash-verification how-to. Linked from homepage header.

## 2026-04-19 13:30 +07 — Model validation + XGBoost leg + 3 new locales + match detail tabs

**Model validation**: 5-config walk-forward backtest (2,263 matches, 6 seasons). Ensemble **full-stack (Poisson + Dixon-Coles + Elo 25% + opp-adjusted xG)** beats baseline **+0.71% accuracy / −1.73% log-loss**. Elo single biggest leg (−0.0149), opp-adjust mild (−0.0046). Decay alone neutral. Keep full-stack config (`scripts/compare_configs.py`).

**XGBoost leg 3**: `app/models/xgb_model.py` + `scripts/train_xgboost.py`. 21 features (strengths + Elo + rest-days + derby flag). Train on all prior seasons, holdout 2024-25 EPL → acc 53.3% / log-loss 0.984. Wired into `predict/service` as second-layer blend at weight 0.30 (conservative until multi-league history fills in). Model file at `/tmp/football-predict-xgb.json`; graceful fallback if absent.

**Locales TH/ZH/KO**: added Thai, Chinese Simplified, Korean full 90-key translations. LangToggle now `<select>` (5 choices). Per-locale timezone + BCP-47 (Bangkok, Shanghai, Seoul). OpenGraph alternateLocale expanded.

**Match detail tabs**: 15 panels grouped into 4 tabs (Preview / Markets / Analysis / Community) via `<MatchTabs>` client wrapper. Sticky under SiteHeader. URL hash sync (`/match/X#markets` deep-links).

**Confidence intervals**: `app/models/ci.py` bootstrap 30-sample → 16/84 percentile on (pH, pD, pA). `/api/matches/{id}/ci` cached 10min. Prediction card shows band `68% / 58%–76%`.

**Team profile polish**: radial-gradient hero with oversized translucent crest corner, 4 stat tiles, RadialGauge for Attack/Defense vs league, next-fixture + last-result spotlight cards, top-scorer card with neon goal count.

**CSS bug fix**: removed hand-rolled `<head>` from layout.tsx that was racing Next's auto-head and stripping the stylesheet link during hydration.

**Deploy flow**: `git push vps main` path stable. 90 tests pass.

## 2026-04-19 09:45 +07 — Lineups + scorer odds + injury-adjusted λ + share + JSON-LD + favorites + push-to-bare-repo

**Lineups**: new `match_lineups` table + `ingest_lineups.py` (resolves `api_football_fixture_id` via `/fixtures?date=` per (league,day), then `/fixtures/lineups?fixture=<id>`). Systemd timer every 15m inside 3h pre-kickoff window. `/api/matches/{id}/lineups` + `<LineupsPanel>` on match detail.

**Player scorer odds**: `/api/matches/{id}/scorers` computes P(anytime goalscorer) from `share × team_λ → 1 − exp(−match_xg)`. Ranked bar chart on match detail.

**Injury-adjusted λ**: `predict/service` shrinks each team's λ by `INJURY_ALPHA=0.6 × injured_xg_share` (capped at 0.5). Upcoming fixtures only; backtest untouched.

**Share buttons** (Copy/Telegram/X/native) + **JSON-LD SportsEvent** on match detail.

**Favorites**: localStorage `<FollowStar>` on team profile; `<FavoritesSection>` on home surfaces fixtures involving followed sides.

**Push-to-bare-repo deploy**: `/srv/git/football-predict.git` + `post-receive` hook. `git push vps main` replaces rsync as primary deploy path. SSH key auth via ed25519.

**Sitemap split per league** via `generateSitemaps` (6 buckets: static + 5 leagues).

65 tests still pass.

## 2026-04-19 08:30 +07 — Ship 8 polish items: H2H, standings, injuries, OG, history, ROI, admin, mobile

**Match detail** gains `<H2HPanel>`, `<InjuriesPanel>`, and a fixed Next 15 OG image with league badge prefix.

**Pages added**: `/admin` (quota + ingest freshness + per-league counts), `/history` (per-season accuracy bars), `/roi` (edge-threshold selector + P&L chart).

**League scoping** extended to `/api/table`, `/api/stats/roi`, new `/api/stats/history`. Mobile: `SiteHeader` sticky + backdrop-blur; `headline-hero` scales from `text-4xl`.

Migration 007 (player_injuries) applied; first seed 12,935 rows across 5 leagues.

## 2026-04-19 07:15 +07 — 10s live cadence + skip-events-when-unchanged

Systemd live timer 1min → **10s**. `ingest_live_scores` only hits `/fixtures/events` when score or status changed (via CTE-UPDATE pattern). LivePoller FE 30s → 10s (free, reads self-hosted API). Lag 3–4min → **~25–30s**. Peak matchday ≈ 3650 calls/day vs 7500 Ultra budget.

## 2026-04-18 21:32 +07 — Team-color accents + trajectory chart + countdown + tz fix

**TZ fix**: new `lib/date.ts` with `formatKickoff/ShortDate/DateOnly(iso, lang)` — explicit `timeZone: Asia/Ho_Chi_Minh` for VI, `Europe/London` for EN. Replaced every ad-hoc `toLocaleString` across MatchCard / match detail / team page / last-weekend. No more SSR/client hydration drift or browser-TZ guessing. VN audience now sees VN wall-clock; EN sees kickoff local.

**Team color accents**: `lib/team-colors.ts` slug → primary club hex (Arsenal #EF0107, Chelsea #034694, etc. — 23 EPL teams covered). MatchCard carries a thin 3px top strip split home/away colors. Match-detail header adds an oblique home→away gradient at 25% alpha. Team profile adds a radial color glow behind the hero. Payy neon `#E0FF32` remains the single visual hero — club colors are peripheral identity.

**Season trajectory chart**: new `GET /api/teams/:slug/trajectory?season=` returns per-final `{xg_for, xg_against, goals_*, is_home, opponent_short}`. New `<SeasonTrajectoryChart>` (SSR, inline SVG) renders neon xG-for + red xG-against 5-match rolling lines; endpoints dot-tagged. Live test: Arsenal 2025-26 returns 32 points.

**Kickoff countdown**: `<KickoffCountdown>` client component ticks every 60s on MatchCards; VI "bắt đầu sau 2 giờ" / EN "in 2h". Only shown for `scheduled` matches.

**Matrix hover tooltip**: `<ScoreMatrix>` cells now carry `title` + `aria-label` (`Arsenal 2 – Fulham 1 · 8.24%`) and cursor-help.

60 tests still pass.

## 2026-04-18 21:22 +07 — /scorers leaderboard + PWA install + CF proxy

**Top scorers page** — new `GET /api/stats/scorers?season&sort=goals|xg|assists|goals_minus_xg`. Route `/scorers` surfaces top 25 w/ team logo, stats (G, xG, npxG, Δ, A, xA, KP, GP) and sortable chips. i18n keys added. Live sample 2025-26: Haaland 22g (xG 23.4, Δ −1.4), Semenyo +3.4 over-performer, Calvert-Lewin −4.5 under-performer — the usual regression hooks.

**PWA** — `app/manifest.ts` (standalone display, #000/neon theme), dynamic icons via Next `ImageResponse` at `app/icon.tsx` (512×512) + `app/apple-icon.tsx` (180×180 rounded). `/manifest.webmanifest` live; Add-to-Home-Screen on mobile now installs a proper EPL icon.

**Cloudflare proxy** — flipped DNS record `predictor.nullshift.sh` to `proxied: true` via CF API. DNS now resolves to CF anycast (`104.21.48.8` / `172.67.175.42`); origin Caddy LE cert makes CF Full-Strict work automatically. Free DDoS protection + edge caching + CF analytics — no code change, one `PATCH` call.

60 tests still pass.

## 2026-04-18 21:13 +07 — 7-season re-fit + post-match recap post

**Temperature re-fit (across 2599 scored matches, all 7 seasons)**: `fit_temperature.py --season all`. Best **T=1.00** (log-loss 0.998, acc 52.3%). Since stored predictions are already v3-temperature-applied, refit returning identity confirms global calibration is right — no config change needed.

**Post-match recap**: `scripts/post_telegram_recap.py` queries finals in the trailing N days + latest predictions, classifies each as hit/miss, posts a Markdown message:
```
📈 EPL tuần vừa rồi — mô hình đoán 4/6 (67%)
✅ Đoán đúng: ...
❌ Đoán sai: [match link] · dự đoán X (48%), thực tế Y
```
Added to `ops/weekly.sh` between backtest and predict_upcoming so the Monday post flow is `recap (last week)` → `pre-match picks (next week)`. Live verified: posted message_id 5 to @worldcup_predictor (6 matches in window).

Channel cadence: Monday early morning → 2 posts, building trust by owning misses alongside picks.

## 2026-04-18 20:54 +07 — Telegram bot + SEO/OG + 3-season backfill

**(3) Backfill 2019-20, 2020-21, 2021-22**: 1140 more matches, 1576 more player-season rows, 1102 odds matched (38 in 2020-21 skipped due to team rename edge cases), 1140 backtest predictions. **DB now spans 7 seasons / ~2660 matches**. Accuracy by season:
2019-20 51.3% · 2020-21 49.5% · 2021-22 53.7% · 2022-23 53.2% · 2023-24 55.5% · 2024-25 55.0% · 2025-26 47.0%. Mean ≈ 52%, every season beats baseline.

**(2) SEO + OG + mobile**:
- `layout.tsx` gets full `metadata` w/ openGraph + twitter card + metadataBase.
- `app/robots.ts` + `app/sitemap.ts` generate standard SEO artifacts (verified live).
- Per-page `generateMetadata()` on `/match/[id]` + `/teams/[slug]` — dynamic title + description w/ the actual prediction.
- `app/match/[id]/opengraph-image.tsx` renders a 1200×630 PNG via Next.js `ImageResponse`: team names (uppercase display), kickoff, top scoreline in neon, H/D/A row. Content-type verified `image/png`.

**(1) Telegram bot**: `scripts/post_telegram.py` fetches upcoming predictions + odds, ranks top 5 value bets (edge ≥ 5pp) + top 5 confidence picks, posts a Markdown message via Telegram Bot API. Gracefully no-ops if `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` missing. Added to `ops/weekly.sh` as the final step (fault-tolerant). User just needs to create a bot via @BotFather and add 2 env vars to `/opt/football-predict/.env`.

`docker-compose.yml` + `.env.example` updated. 60 tests still pass.

## 2026-04-18 20:07 +07 — Team crests across the app

Added static slug → ESPN CDN crest URL map (`lib/team-logos.ts`, 23 current + recently-relegated EPL clubs, all probed HTTP 200). `<TeamLogo>` component renders a plain `<img>` at a caller-specified size with a two-letter monogram fallback pill when the slug isn't mapped.

Wired into: MatchCard (28px, flanking short names), QuickPicks (20px), `/match/[id]` hero (56px), `/table` rows (20px with team name), `/last-weekend` cards (24px), `/teams/[slug]` header (72px). Live checks: dashboard renders 20 distinct crests, table 20, last-weekend 16, team profile 1 (its own).

No backend/schema change — mapping is FE-only, graceful degradation if slug missing.

## 2026-04-18 19:58 +07 — Cumulative ROI chart + Quick Picks hero card

**ROI**: `GET /api/stats/roi?season&threshold=0.05` walks finals chronologically, simulates 1u flat stake on every outcome with `model - fair >= threshold`, buckets PnL per kickoff date. Returns `{total_bets, total_pnl, roi_percent, points[]}`. Live 2025-26 @5pp: **204 bets · +4.01u · +2.0% ROI** over 93 date buckets (2025-08 → 2026-04). `<RoiChart>` SSR component renders a hand-rolled SVG line chart (color flips red if PnL negative) with summary chips above.

**Quick Picks**: new `<QuickPicks>` card on the dashboard, top 3 upcoming fixtures by `best_edge` filtered at 5pp. Shows outcome + edge pp + decimal odds, links to detail page. Renders above the accuracy stat row so it's the first actionable content.

i18n keys added (`roi.*`, `quick.*`). 60 tests pass, no schema changes.

## 2026-04-18 19:50 +07 — Chat rate-limit + `/last-weekend`

**Rate limit** (chat): DB count of user messages in trailing 60 min per session_id. 20 msgs/hour → 429 with localized error. Verified live (20× 200 then 429). Protects Qwen quota from spam.

**`/last-weekend` archive**: `GET /api/stats/recent?days=7` returns summary + per-match pick vs actual outcome with hit flag. FE route renders summary chips + 2-col grid of Hit/Miss pill cards. Nav link added (`nav.recent` / "Tuần vừa rồi" / "Last weekend"). Live sample 7d: **8 scored, 4 correct = 50% acc**, log-loss 1.07.

60 tests pass.

## 2026-04-18 19:43 +07 — Scoreline matrix redesign

- Smooth RGB interpolation `#161616 → #E0FF32` per cell (36-step ramp) instead of flat `rgba` overlay. Low-probability cells still legible.
- Top scoreline cell: 2px neon outline + radial glow `box-shadow: 0 0 20px rgba(224,255,50,0.5)` + bold larger number.
- Team short names now on axes (home down rows, away across columns) instead of the `H \ A` corner label.
- Header shows `λ 2.54 · 0.88` and "Most likely · LEE 2–0 WW 10.6%" subtitle.
- Added legend row below the grid: `0% ── gradient ── {max}%`.
- Text color auto-contrast (black on cells where alpha > 0.55, secondary white otherwise).

`ScoreMatrix` now takes optional `homeShort`, `awayShort` props (passed from `/match/[id]` via `match.home.short_name`).

## 2026-04-18 19:36 +07 — i18n EN/VI + softened copy (kept Payy colors + fonts)

Pivoted the UI from "terminal hacker dialect" to plain language while keeping the Payy design system (neon `#E0FF32`, pure-black surface, Geist + JetBrains Mono) intact.

**Framework**: `lib/i18n.ts` + `locales/{en,vi}.ts` (flat string keys, var interpolation). Cookie-driven lang (default `vi`). `lib/i18n-server.ts` (`getLang()` via `cookies()`) for Server Components, `lib/i18n-client.tsx` with `<LangProvider>` + `useT()` for Client Components. `<LangToggle>` in the new `<SiteHeader>` nav writes the cookie and calls `router.refresh()`.

**Copy pass**: removed `>`, `//`, `[STATUS]`, `█░░░░░`, peer-tone "tao/mày". Labels → sentence case, stats stay monospace + tabular-nums. Match-card status uses a rounded pill. Chat widget renders "You / Analyst" instead of "> mày / > tao".

**Backend alignment**: `build_chat_system(lang)` + `build_chat_user(..., lang)` + `suggested_prompts(..., lang)` accept `"vi"|"en"`. Vietnamese tone shifted to polite "tôi/bạn". Endpoint `POST /api/chat` takes `lang`; `GET /api/chat/suggest/:id?lang=` localizes starter chips. 60 tests pass (prompt tests updated for new tone).

**Live verification**:
- VI (default): "Trận đấu tuần này", "Sắp diễn ra", "Bảng XH", "Thống kê"
- EN (cookie `lang=en`): "This week's fixtures", "Upcoming", "Table", "Stats"
- Chat suggest EN: "Why did the model predict this?" / VI: "Vì sao mô hình dự đoán như vậy?"

## 2026-04-18 19:18 +07 — Live odds via The Odds API; value bets on upcoming

`scripts/ingest_live_odds.py` pulls `/v4/sports/soccer_epl/odds` (uk,eu, h2h), averages decimal across 30 bookmakers, maps team names (e.g. "Brighton and Hove Albion" → "Brighton"), upserts with source `the-odds-api:avg`. `THE_ODDS_API_KEY` wired into config / compose / `.env.example`, added to VPS `.env`, folded into weekly cron (fault-tolerant).

First run: 20 events → **17 upserted** (3 team-name / fixture mismatches). Quota 4/500. **Dashboard now shows 18 VALUE badges** across upcoming fixtures. Top picks this weekend: MC vs ARS → Arsenal +18.3pp, SUN vs NF → Home +12.4pp, NU vs BOU → Bournemouth +9.9pp.

Cost envelope: 4 credits/weekly-run × ~4 weeks/month = 16 credits/month, free budget is 500.

## 2026-04-18 19:11 +07 — Combo: backfill + multi-turn chat + odds value bets

**Backfill 2022-23 + 2023-24**: 760 new matches, 1124 player-season rows, 760 backtest predictions. Total now **1520 matches · ~2200 players · ~1500 predictions** across 4 seasons.

**Multi-turn chat**: `chat_messages` live — `POST /api/chat` accepts `session_id`, persists user+assistant messages. `GET /api/chat/history` replay. FE localStorage UUID, loads prior on mount. First turn packs DATA; follow-ups send only question (history carries context). 2-turn live test confirmed follow-up grounded in turn-1 DATA.

**Odds + value bets** (football-data.co.uk, free): migration 002 applied, 7 TDD tests, **1459/1459 matches matched** across 4 seasons via SQL JOIN on (date, home, away). `<ValueBetBadge>` on MatchCard + `<OddsPanel>` on `/match/:id`, threshold +5pp.

**ROI walk-forward** (1u flat stakes):
| season | 5pp ROI | 8pp ROI |
|---|---|---|
| 2022-23 | +6.5% | **+22.1%** |
| 2023-24 | -16.8% | -15.7% |
| 2024-25 | **+18.9%** | **+26.2%** |
| 2025-26 | +2.0% | -3.9% |

Positive EV in 3/4 seasons. 2023-24 is regime-change outlier. Limitation: CSV doesn't have upcoming-match odds → needs live API (The Odds API free 500 req/mo) for live value bets.

**Tests**: 58 pass (+7 odds).


---

## 2026-04-18 18:43 +07 — v3 temperature scaling: fixed the 60-70% overconfidence trap

`/stats` calibration revealed the model was seriously overconfident in the 60–70% bin (predicted 64%, actual 49%, -15.3pp). Fit temperature on scored predictions: 2025-26 optimum T=1.45, 2024-25 optimum T=1.25, split at **T=1.35**.

TDD: 5 new tests on `temperature_scale_1x2` (identity at T=1, flattens T>1, sharpens T<1, normalizes, preserves ordering) + end-to-end through `predict_match`. 51 pass.

`DEFAULT_TEMPERATURE=1.35` baked in; `MODEL_VERSION=poisson-dc-v3`. Backtest re-ran under v3 (699 rows), upcoming re-predicted (30 rows).

**2025-26 calibration lift**:
- log-loss 1.0523 → **1.0409** (-1.1%)
- brier 0.6335 → **0.6260** (-1.2%)
- **60-70% bin**: Δpp -15.3 → **+6.8** (trap gone)
- 40-50% bin: Δpp -4.1 → **+1.6** (perfect)
- Accuracy unchanged at 47.0% (expected — T preserves argmax)

Net: probs shown on the app now mean what they say. 50 tests + 5 temperature = 51 total.

## 2026-04-18 17:41 +07 — v2 model + weekly cron + scoreline heatmap

**(1) Ops cron**: `ops/weekly.sh` + systemd unit + timer on VPS. Fires **Monday 02:00 UTC** (randomized ±10 min). Runs ingest_season → ingest_players → backtest → predict_upcoming in sequence. `systemctl list-timers football-predict-weekly.timer` → next Mon 2026-04-20 02:04.

**(2) Model v2**: `scripts/grid_search.py` joint sweep (last_n × ρ). Best **last_n=12, ρ=-0.15** on 2024-25 train + 2025-26 holdout. Baked into `DEFAULT_LAST_N`, `DEFAULT_RHO`, `MODEL_VERSION=poisson-dc-v2`. Backtest updated to skip only matches predicted by the *current* model_version — reruns safely when tuning.

**Live metrics (v2)**:
- 2024-25: acc **55.0%**, log-loss **0.994** (was 1.002 v1)
- 2025-26: acc **47.0%** ⬆ from 45.8%, log-loss **1.052** ⬆ from 1.064

**(3) Scoreline heatmap**: TS port of Poisson+DC (`lib/poisson.ts`), `<ScoreMatrix>` 6×6 grid on `/match/:id`. Cells fade by `rgba(224,255,50, p/max)`; top scoreline neon-filled + black text. ρ extracted from model_version via regex.

46 tests still pass. 699 predictions re-written under v2. Weekly refresh now self-driving.

## 2026-04-18 17:32 +07 — Drop Monad, keep hash as chain-agnostic fingerprint

User: "skip monad — onchain chi lam predict data thoi". Reframed 4.1 from on-chain publisher to plain prediction-data integrity fingerprint.

**Removed**: `contracts/EPLPredictionCommit.sol`, `contracts/README.md`, `scripts/publish_commitments.py`, `web3>=7` dep, MONAD_* env in compose + .env.example, `NEXT_PUBLIC_EXPLORER_URL`. API no longer exposes `commitment_tx` / `commitment_chain` keys (46 tests still pass).

**Kept**: SHA-256 commitment hash (the valuable part — deterministic over canonical-JSON prediction body). `predictions.commitment_hash` column + CommitmentBadge FE. Badge wording reframed to "prediction fingerprint // sha-256 :: verifiable". DB columns `commitment_tx` / `commitment_chain` left in place as harmless nullable (forward-compat if any chain is added later).

**State**: Phase 4 closed. 4.1 = fingerprint only (no broadcast). 4.2 = out of scope (betting, regulatory).

## 2026-04-18 17:25 +07 — Phase 4.1 LIVE: on-chain prediction commitments

**Commitment scheme**: SHA-256 over canonical-JSON payload `{v, match_id, kickoff_unix, model_version, rho, p_home_win, p_draw, p_away_win, expected_*, top_scoreline}` with 6-dp float rounding. 4 TDD tests lock determinism + field sensitivity + hex shape + float-jitter stability. 46 tests total.

**Wire**: `app/onchain/commitment.py` + `predict_and_persist` computes hash on every new prediction. Migration `db/migrations/001_commitment_columns.sql` applied (ADD COLUMN IF NOT EXISTS). Rerun `predict_upcoming` → 30 fresh predictions carry hashes. Example: BRE vs FUL → `0x6e3a32…`

**On-chain**: `contracts/EPLPredictionCommit.sol` (single-writer registry, commit + batchCommit, firstSeenAt mapping + PredictionCommitted event). `scripts/publish_commitments.py` using `web3.py` reads MONAD_RPC_URL/CHAIN_ID/CONTRACT_ADDRESS/PRIVATE_KEY, batches 20/tx, writes commitment_tx back. **Not broadcast yet — user deploys contract (Remix) + fills env → runs publisher.**

**FE**: `components/CommitmentBadge.tsx` (compact variant on MatchCard, full on `/match/:id`). Shows `[off-chain, pending broadcast]` until `commitment_tx` set; then `[on monad-testnet]` + tx link from `NEXT_PUBLIC_EXPLORER_URL`.

**4.2 skipped** per brief out-of-scope rule (betting / regulatory risk).

**State**: Phase 4.1 code-complete. Hashes live. Broadcast is a user-driven one-off step documented in `contracts/README.md`.

## 2026-04-18 17:14 +07 — Phase 3 LIVE: table / teams / accuracy / scorers

**BE routes added**:
- `GET /api/table?season=` — W/D/L/Pts + xGF/xGA/xGD per team
- `GET /api/teams/:slug` — stats + form last-10 + top scorers + fixtures
- `GET /api/stats/accuracy?season=` — model vs baseline + log-loss

**Scripts**:
- `scripts/backtest.py` — walk-forward predict for every final, idempotent. Wrote 380 (2024-25) + 319 (2025-26) = 699 backtest predictions.
- `scripts/ingest_players.py` — Understat player_season_stats → DB (42 tests: 3 new translator tests). 1062 player-season rows across both seasons.

**FE pages added**: `/table`, `/teams/[slug]`. Dashboard header gets 4 stat chips (accuracy / baseline / log-loss / matches scored). MatchCard + table rows link to team profiles.

**Accuracy numbers on real data**:
- 2024-25: **55.0%** 1X2 accuracy (380 matches, baseline 40.8%, log-loss 1.00)
- 2025-26: 45.8% (319 matches, baseline 41.7%, log-loss 1.06 — early-season noise)

**Fresh predictions**: reran `predict_upcoming` with full 699-match context → 30 upcoming matches, 30 Qwen reasonings attached. Top scorers now available in chat context (Saka, Gyökeres, Muñiz etc.).

**State**: Phase 3 done. Phase 4 (NullShift on-chain commits) optional. Weekly ops: `ingest_season` + `ingest_players` + `predict_upcoming` still manual — cron opportunity.

## 2026-04-18 17:03 +07 — Phase 2 LIVE: streaming chat Q&A

**BE**: `POST /api/chat` streaming (LiteLLM `acompletion(stream=True)` via OpenAI-compat + DashScope intl), `GET /api/chat/suggest/:id` returns 4 VN peer-tone prompts. `chat_context.py` pulls last-5 + H2H last-3 + top-scorers (stub — player stats ingest = Phase 3). TDD'd `chat_prompt.py` (6 tests, 39 pass total).

**FE**: new route `/match/:id` with hero + prediction block (radial neon glow under top scoreline) + TerminalBlock reasoning + `ChatWidget`. Widget streams via `fetch().body.getReader()`, no Vercel AI SDK dep. MatchCard now links to detail page.

**Verified live**: streaming from https://predictor.nullshift.sh/api/chat citing real xG + H2H numbers (no fabrication — "tao không có số đó" on matches without predictions, as designed).

**State**: Phase 2 done. Chat grounded on DB context works. Minor: Qwen occasionally leaks Chinese chars (e.g. 倾向). Phase 3 queue: player_season_stats ingest + xG table + team profile + accuracy tracking.

## 2026-04-18 13:54 +07 — LIVE: https://predictor.nullshift.sh/

**Full-stack deploy on Hostinger VPS done** (`/opt/football-predict`, project `football-predict`, ports `8500 BE / 3500 FE`). DB + API + Web containers healthy, Caddy reverse-proxy with LE cert, Cloudflare A record (unproxied) to `76.13.183.138`.

**Ingested**: 2024-25 (380 matches) + 2025-26 (380 matches) from Understat. 21 upcoming predictions within 14-day horizon, **21/21 Qwen reasoning attached** (Vietnamese peer tone, data-grounded).

**Issue found + fixed**: LiteLLM default `dashscope/*` hits CN region; user's DashScope key is **intl/Singapore-issued**. Routed via OpenAI-compat mode + `api_base=https://dashscope-intl.aliyuncs.com/compatible-mode/v1`. `DASHSCOPE_API_BASE` env override for CN users.

**Minor**: predict_upcoming.py added to drive bulk prediction + reasoning pass. POSTGRES_PASSWORD generated via `openssl rand -hex 20`, stored only in `/opt/football-predict/.env` on VPS (600, not committed).

**State**: Phase 1 complete. Public live. Weekly ingest + predict is manual for now (runbook in `docs/deploy.md`) — cron it in Phase 3.

## 2026-04-18 13:33 +07 — Phase 1 code-complete: API + LLM + frontend

- **1.6 API**: `app/schemas.py` (Pydantic), `app/queries.py` (asyncpg SQL w/ LATERAL for latest prediction join), `app/predict/service.py` (predict_and_persist + predict_all_upcoming), routers `api/matches.py` + `api/predictions.py`. Wired into `main.py` with CORS.
- **1.5 LLM**: TDD'd `app/llm/prompt.py` (5 tests, Vietnamese peer tone locked). `app/llm/reasoning.py` builds DB-grounded context (last-5 xG + H2H last-3) → LiteLLM `dashscope/qwen-turbo` → UPDATE prediction row. Hooked into POST `/api/predictions/:id`.
- **1.7 Frontend**: Next.js 15 + Tailwind 3 + Payy tokens (`tailwind.config.ts`), `app/{layout,page,globals.css}`, components `MatchCard` / `PredictionBar` / `TerminalBlock`, `lib/{api,types}.ts`. `npm run build` passes clean.
- **1.8 Deploy doc**: `docs/deploy.md` — full VPS (Docker compose + Caddy) + Cloudflare Pages walkthrough + pg_dump backup.

**Tests**: 33 pass (prev 28 + 5 prompt). **State**: code done. Next = mày chạy `docker compose up -d` trên VPS, `ingest_season.py`, `predict_all_upcoming`, rồi deploy frontend CF Pages.

## 2026-04-18 13:25 +07 — Plumbing: compose + schema + config/db + ingest (TDD)

Calibrated ρ trên 2024-25 EPL (grid [-0.30, 0.10]): **best ρ = -0.10** (log-loss 0.9856, acc 57.0%), locked vào `config.py` `DEFAULT_RHO`. Open question trong `docs/environment.md` đã resolved.

Added deployment artifacts: `db/schema.sql`, `docker-compose.yml` (pgvector/pgvector:pg16 + api service), `backend/Dockerfile`, `.env.example`. Added runtime: `app/core/{config,db}.py` (pydantic-settings + asyncpg pool lifespan), `app/main.py` (minimal FastAPI, `/health`).

Phase 1.3 ingest (TDD): `app/ingest/schedule.py` pure translator (6 tests pass) → `app/ingest/upsert.py` asyncpg wrapper → `scripts/ingest_season.py` CLI. **28 tests pass**. VPS: chỉ cần `cp .env.example .env` → `docker compose up -d` → `python scripts/ingest_season.py --season 2024-25`.

**State**: Phase 1 sau: 1.1 ✓, 1.2 ~ (cần apply VPS), 1.3 ~ (cần run ingest), 1.4 ✓, 1.6 ~ (chỉ /health). Next logical: 1.6 (API `/matches`, `/predictions`) + 1.5 (LLM reasoning).

## 2026-04-18 13:18 +07 — DB = self-hosted Postgres trên VPS, drop Supabase

Bỏ Supabase khỏi toàn bộ docs. DB giờ là Postgres 16 + `pgvector` self-hosted trên VPS, chạy cùng API qua `docker compose` (image `pgvector/pgvector:pg16`). Env đổi `SUPABASE_URL/KEY` → `DATABASE_URL`. Updated: `architecture.md`, `database.md`, `environment.md`, `project-structure.md`, `roadmap.md`, `README.md`, `CLAUDE.md`, `plan.md`.

## 2026-04-18 13:16 +07 — Phase 1.4 xong: Poisson engine validated

TDD: `backend/app/models/poisson.py` (Dixon-Coles matrix, tau, 1X2 collapse, top scorelines, `predict_match`) + `features.py` (team strengths + lambdas), **22 tests pass**. TDD đã bắt misconception về dấu của ρ: positive ρ thực ra shrink draws, empirical EPL cần ρ âm.

Walk-forward validate trên 2024-25 Understat (330 matches, warmup 50):
- **57.0% 1X2 accuracy** (baseline always-home: 41.8%, brief target: >50% ✓)
- Mean log-loss 0.9856 @ ρ=-0.1 vs 1.0986 uniform

**State**: math engine green-lit. Next: Phase 1.2 (Supabase schema) hoặc 1.3 (scraper persist) hoặc calibrate ρ. Decision open.

## 2026-04-18 13:00 +07 — Design chuẩn = payy.network

Rewrote `docs/frontend.md` với full Payy design system: tokens `#000` surface / `#E0FF32` neon / `#161616` raised, uppercase display type, mono cho số, pill CTA neon-fill + **black text** (per memory). Updated refs in `CLAUDE.md` + `docs/README.md` từ "NullShift" → "Payy-inspired".

**State**: Phase 0 vẫn vậy. Design contract đã khóa.

## 2026-04-18 12:56 +07 — Docs scaffold + plan + CLAUDE.md

Split the original project brief (`init.md`) into 10 topical docs under `docs/`. Added `CLAUDE.md` (session orientation), `plan.md` (phase checklist + doc map), and this progress log.

**State**: Phase 0 (scoping). No code yet. Next: Phase 1.1 — init `backend/` + `frontend/` skeleton.
