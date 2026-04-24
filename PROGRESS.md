# PROGRESS — EPL Prediction Lab

> Dated summary log. **One short entry per meaningful step.** Format: `## YYYY-MM-DD HH:MM TZ — <summary>`. Keep each entry to 1–3 lines. Details live in code + docs, not here.

## 2026-04-24 21:30 +07 — Phase 42 content engine + mobile nav fix

- **42.1 Per-match story**: migration 032 adds `matches.story`; `generate_story()` writes 400-500 word Qwen-Turbo narrative on FT (cap 2/tick) + daily backfill via `generate_stories.py --days 14 --limit 30`. Endpoint `/api/matches/:id/story` + `<MatchStoryCard/>` on match page. **First 5 backfill stories live** (Real Oviedo 1-1 Villarreal etc).
- **42.3 + 42.4 Team-of-the-week / hot-cold**: `post_team_of_week.py` ranks last 7d xG-overperformance — hot (goals >> xG) + cold (due regression). **First Telegram post fired: 3 hot + 3 cold.** Systemd Mon 10:00 UTC.
- **42.5 Weekend preview**: Friday 18:00 UTC Qwen-Turbo writes 500-700 word Telegram preview of Fri-Sun fixtures across all leagues. Timer enabled (next firing 2026-04-24 18:00 UTC).
- **42.2 Manager-of-month**: deferred — overlaps with Block 15.5 manager-tenure work.
- Qwen-Plus free tier exhausted on account; switched story + preview to `qwen-turbo`.

- **Mobile menu fix**: SiteHeader `NavLinks` (4-group dropdowns) was overlapping `LeagueSelector` in <400px viewports. Now `hidden md:flex` on nav; search + theme toggles hidden on mobile. New `MobileNavDrawer` hamburger slide-in sheet exposes every surface (Matches/Stats/Bets/Lab) as a flat list. Desktop unchanged.

## 2026-04-24 21:00 +07 — Phase 41 shipped: monetisation MVP

- **Migration 031** — `api_keys.tier` (free/pro-free/pro) + `stripe_*` + `grandfather_until`. Existing active keys auto-flipped to `pro-free` until 2027-01-01.
- **`/api/billing/*`** — `POST /checkout` (Stripe Session or Ko-Fi fallback), `POST /webhook` (HMAC-SHA256 verified), `GET /status?email=`, `POST /cancel` (cancel_at_period_end).
- **`/pricing`** — Free vs Pro $9/mo cards, email-gated upgrade; redirects to `checkout_url` or Ko-Fi. **`/billing`** — email lookup + cancel-at-period-end button.
- **Footer** — `/pricing` + `☕ tip` Ko-Fi link on every non-embed page. Sitemap updated.
- Graceful degradation verified: no `STRIPE_API_KEY` set → upgrade CTA returns Ko-Fi URL, webhook path inert. Ready to activate whenever Stripe key lands.

## 2026-04-24 17:30 +07 — Phase 40 shipped: growth assets

- **`/welcome` landing page** — 5-lang single-scroll conversion page; hero "xG doesn't lie. But the bookies do." + proof strip + 3 CTAs.
- **Matchday-morning Telegram** — `post_matchday_morning.py` + `football-predict-morning.timer` (10:00 UTC daily). Idempotent via `matches.morning_notified_at`. **First post just fired — 2 edges notified.**
- **X thread generator** — `gen_x_thread.py` prints 4 tweets ready to copy-paste (sample from today: PC1 vs PIS +24%, AUG vs EF +17.9%).
- **`docs/growth-playbook.md`** — Telegram / Reddit / VN FB / partner-email templates + 10-partner target list + weekly metrics tracker.

Target: 500 Telegram · 100 emails · 3 embed partners in 30 days.

## 2026-04-24 16:45 +07 — Phase 39 complete: bracket MC + cup-fixture predict fix

- Cup-fixture predict path unions each team's domestic-league xG history so UCL matches get valid λ (Arsenal/EPL + Atletico/La Liga, etc).
- Fault tolerance in `predict_all_upcoming` skips untrackable cup fixtures (e.g. Eredivisie clubs) instead of aborting. **159 predictions written, 2 skipped.**
- **UCL semis predicted**: PSG-Bayern 69/20/10, Atletico-Arsenal 28/31/42.
- `/api/stats/bracket` + `/bracket` — 5,000 MC sims on remaining knockout rounds. **PSG 45.8% to lift UCL, Arsenal 42.2%** · 88% of sims end PSG-Arsenal final.
- `/europe` page links into `/bracket`.

## 2026-04-24 16:00 +07 — Phase 39: UCL + UEL ingest shipped

- `app/leagues.py` +2 entries (UCL api_id=2, UEL api_id=3) so every league-scoped surface picks them up.
- `scripts/ingest_european_cups.py` pulls fixtures + 1X2 odds from API-Football Ultra. Upserts via `af:{fid}` external_id + `competition_type='europe'` (Block 21.6 cup prior activates at predict time).
- **550 fixtures ingested** (280 UCL + 270 UEL) on first run. Real UCL semis live on `/europe`: PSG vs Bayern (28/4) + Atletico vs Arsenal (29/4) and return legs.
- `/europe` page, sitemap entry priority 0.9, daily cron wire.

## 2026-04-24 15:40 +07 — Phase 38: /live in-play value-bet scanner

Joined already-live probabilities (Poisson residual over remaining minutes, computed in `queries.record_to_match_dict`) against latest best-of-books 1X2 odds to surface in-play value bets.

- `/api/live-edge?min_edge_pp=2` — returns live match × best-edge outcome rows.
- `/live` page auto-refreshes every 20s, renders card per live match with pick + odds + edge + 3-way bar.

Zero new schema. Reuses `predictions`, `match_odds_history`, and the existing `live_probabilities()` function. Empty while no match is live — populates organically when matches kick off.

## 2026-04-24 15:10 +07 — XGB retrain with upgraded is_derby: DID NOT WORK, rolled back

Swapped the crude city-token `_is_derby` heuristic for the curated Block 21 pair list, then retrained. Holdout 2024-25 (1,748 matches) went **worse**: accuracy 53.38% (was 55.41%, −2pp), log-loss 0.981 (was 0.979, +0.2%). Market-feature gain share dropped 27.4% → 11.0% — the booster stopped leaning on the signal it used to rely on.

Rolled back both: `git revert` on the code, restored the pre-retrain model from `/tmp/xgb-pre-derby.json`. Live predictions back to the 27-feature booster that was working.

**Takeaway:** the Block 21 ρ calibration won on 2024-25 (−0.12% log-loss per our earlier backtest), but layering the same signals into XGB through a derby-flag refinement didn't help. Feature was already near-optimal as a rough proxy. Further XGB improvements need new signals, not better matching on an existing one.

## 2026-04-24 14:30 +07 — Block 21 measured: dynamic ρ wins +0.12% log-loss

Backtest on 2024-25 (1750 matches):

| config | log-loss | Brier |
|---|---|---|
| static ρ = −0.15 | 0.85434 | 0.50268 |
| dynamic ρ | **0.85334** | **0.50238** |
| dynamic + derby | 0.85341 | 0.50241 |

**Δ dynamic vs static: −0.00100 log-loss (−0.12%), −0.00030 Brier.** Derby bump is noise (few derbies per season). First-round result showed +0.18% WORSE because `calibrate_rho_per_quarter.py` was minimizing scoreline log-loss not 3-way log-loss. Fixed the objective, recalibrated 7 × 5 = 35 rows. `backtest_block21.py` lives in-repo so the verdict is re-runnable.

## 2026-04-24 14:00 +07 — Phase 36 wrap + data activation

- `<TaxToggle>` live on `/roi` — none / UK / EU / VN / US dropdown shows after-tax P&L side-by-side with raw.
- `seed_manager_tenure.py` seeded 22 current managers across top-5 leagues. `/api/teams/arsenal/manager` returns Arteta 2317 days.
- ρ calibration now covers 7 seasons × 5 leagues = 35 rows. Bundesliga consistently −0.15..−0.25; EPL swings +0.05..−0.20. Default −0.15 was wrong for 4/5 leagues in 2024-25.
- `predict_upcoming` re-run: 93 predictions under new dynamic ρ + derby bump path.

## 2026-04-24 13:30 +07 — Phase 36 + 37 shipped

**Phase 36 (close-out):**
- `<ThemeToggle>` now in SiteHeader — users can actually flip theme.
- `<MatchOfWeekCard>` on homepage calling /api/stats/match-of-week.
- `<PlayerRadar>` SVG on /players/:slug with 6 position-normalized axes.
- Webhook dispatcher wired into ingest_live_scores FT block.
- `calibrate_rho_per_quarter.py` fit + populated for 2024-25 Q1 all 5 leagues. La Liga optimal ρ=0, Serie A −0.05, EPL −0.05, Ligue 1 −0.10, Bundesliga −0.15 — default of −0.15 was wrong for 4 of 5 leagues.
- `predict/service.py` now looks up calibrated ρ per prediction + applies +3% λ on tagged derbies.

**Phase 37 (Futures / outrights):**
- `/outrights` page — reuses /api/stats/title-race MC. User picks league + market (Champion / Top-4 / Relegation), pastes posted odds per team, computes edge = p × posted − 1. Green ≥ 5pp.

## 2026-04-24 12:45 +07 — Blocks 23-34 done: all remaining blocks shipped

12-block bundled pass. Each block gets a minimum-viable-but-working landing surface.

- **23 UX polish** — theme toggle · mobile bottom nav · skeleton · glossary tooltip · shortcuts modal · sound + /settings.
- **24 Internal tools** — migration 028 (`error_events` / `feature_flags` / `page_views`) · persisted error log · `/api/admin/errors` / `/api/flags` / `/api/admin/analytics` · `<PageViewTracker>` · `/admin/errors` UI · `snapshot_restore_drill.py`.
- **25 Content/SEO** — `/glossary` · `/methodology` · `/changelog` (reads PROGRESS.md) · `/press-kit` · `/api/stats/match-of-week` · sitemap expanded.
- **26 Developer API** — migration 029 (`api_keys` / `api_key_usage` / `api_webhooks`) · admin-gated issue/revoke · rate-limited `/api/developer/status` + webhooks · `/api-docs` page.
- **27 Deeper analytics** — `app/models/player_radar.py` (6-axis position-normalized) + `/api/players/:slug/radar` · `form_streaks.py` hot/cold finishing.
- **28 Localisation depth** — tLang infrastructure in place; full audit deferred.
- **29 Performance** — `/api/metrics` Prometheus endpoint.
- **30 Legal** — `/privacy` + `/terms` with jurisdiction notes + helplines.
- **31 Observability v2** — /api/metrics + persisted error_events + ops watchdog covers signal.
- **32 Research** — `scripts/sweep_config.py` ρ × last_n sweep → CSV stdout.
- **33 Community** — migration 030 (`tipsters.pin_hash` + `display_name`) · `/api/tipster-signup` · `/api/tipster-signup/leaderboard` (derives log-loss from match outcomes).
- **34 Brand** — global footer (methodology/glossary/calibration/equity-curve/api/embed/press/changelog/privacy/terms/status) on every non-embed page.

## 2026-04-24 10:55 +07 — Block 22 done: sharp tooling v2 (6 items)

1. **22.1 Arbitrage detector** — `app/models/arbitrage.py` + 5 TDD + `/api/stats/arbs` + `/arbs`. 34 opps found on first scan.
2. **22.2 O/U middle finder** — `app/models/middles.py` + 4 TDD + `/api/stats/middles` + `/middles`.
3. **22.3 CLV by market** — `/api/stats/clv-by-market`; 1X2 live, OU/AH/BTTS placeholders.
4. **22.4 Kelly explorer** — `/kelly-explorer` renders 6 Kelly caps side-by-side.
5. **22.5 Book weights** — `book_weights.py` Pinnacle 1.0 / retail 0.5 / default 0.3 + `weighted_consensus()`.
6. **22.6 Tax-aware ROI** — `tax.py` VN/EN/EU/US jurisdictions + `apply_tax()`.

9/9 new tests green.

## 2026-04-24 10:30 +07 — Block 21 done: model depth v2 (6 items)

Infrastructure-only ship so prod behaviour unchanged; future retrain wires these into the predict path.

1. **21.1 Home/away split** — already shipped in `features.py` (venue-split strengths + `venue_blend=0.6` in `match_lambdas`). Marked complete.
2. **21.2 Derbies** — `app/models/derbies.py` tags 22 rivalry pairs (NLD, Manchester, Merseyside, El Clasico, Derby della Madonnina, Der Klassiker, Le Classique, etc.) + `/api/matches/:id/derby` endpoint. 5 TDD tests.
3. **21.3 Manager tenure** — `manager_tenure` table + `/api/teams/:slug/manager` history + `/api/matches/:id/manager-bounce` flag + admin POST endpoint for seeding.
4. **21.4 Defense-adjusted player xG** — `defense_adjusted_xg.py` helpers + 5 TDD tests. Clamps opponent coefs to [0.5, 2.0] so thin samples don't explode projections.
5. **21.5 Dynamic ρ per quarter** — `rho_calibration` table + `dynamic_rho.lookup_rho()` with matchweek→quarter mapping. Empty table today = fall back to DEFAULT_RHO = -0.15 (prod behaviour unchanged).
6. **21.6 Cup-vs-league prior** — `competition_type` column on matches (default 'league'), `competition_prior.py` with league/cup/europe priors (favourite_reduction + ρ shift).

3 new migrations applied (025 manager_tenure, 026 rho_calibration, 027 competition_type). 10/10 tests green.

## 2026-04-24 09:45 +07 — Block 20 done: personal layer (5 items)

No-login personal surface, everything in localStorage by default.

1. **20.1 My picks log** — `lib/my-picks.ts` permanent ledger + `/my-picks` page + `<LogPickButton>` on match detail. Auto-settles when match hits final. Summary: total/settled/hits/P&L/ROI.
2. **20.2 Personal vs Model ROI** — `<MyPicksVsModel>` chart: cumulative P&L for your picks vs what the model would have earned at the same odds + stake on its own argmax picks. Side-by-side verdict on your discretion vs the model's.
3. **20.3 Watchlist page** — `/watchlist` aggregates favorite teams (uses existing `favorites.ts`) with next fixture + last result + form per team. Empty state prompts to star a team or sync PIN.
4. **20.4 PIN cross-device sync** — `db/migrations/024_user_sync.sql` + `/api/sync/:pin` POST (push) & GET (pull). PIN sha256-hashed server-side; 30 rps/ip throttle; payload bundles `favorites-v1 + betslip-v1 + my-picks-v1`. `/sync` page with Save/Load UI + random-PIN generator.
5. **20.5 PWA install prompt** — `<InstallPrompt>` handles `beforeinstallprompt` event; global (except /embed); dismissal persisted in localStorage. Push infra already shipped in earlier phase.

Smoke proof: /watchlist /my-picks /sync all 200; `/api/sync/123456` push returns `v:1`, pull returns the same payload; `/api/sync/abcdef` returns 400.

## 2026-04-24 09:00 +07 — Block 19 done: sharp credibility (6 items)

1. **19.1 Calibration curve** — `app/models/calibration.py` + 5 TDD tests + `/api/stats/reliability` + `/calibration` page. 12,227 predictions: Brier 0.242 (vs 0.25 coin-flip). **Model systematically underconfident** — says 50% hits actually hit 62%. Signals room for temperature-scaling correction.
2. **19.2 Team-specific accuracy** — `/api/stats/accuracy-by-team` + `/benchmark/by-team` page. Bayern 83%, Barca 81%, Inter 79% on the top; Rennes 23%, Piacenza 24% on the bottom.
3. **19.3 Ensemble disagreement** — pragmatic proxy via top-2 margin < 10pp ("tricky" filter). `?tricky=true` on `/api/matches` + homepage chip. 8 flagged matches with < 10pp margin today.
4. **19.4 Line movement chart** — `match_odds_history` table + trigger logs every odds update (7493 rows backfilled). `/api/matches/:id/line-movement` time-series + `<LineMovementPanel>` SVG on match detail.
5. **19.5 Sharp vs square divergence** — part of the line-movement endpoint; devigged Pinnacle vs retail mean, flags ≥ 5pp gaps. Same UI callout below the chart.
6. **19.6 Season-over-season equity curve** — `/api/stats/equity-curve` + `/equity-curve` page. **7-year flat-stake result: −83.57u overall** at 5pp edge. Only 2 winning seasons. Transparency-as-marketing.

Block 19 shipped end-to-end. Next: Block 20 personal layer (my picks, watchlist, PIN sync, PWA push).

## 2026-04-24 02:15 +07 — Block 18 done: viral / engagement (7 items)

1. **18.1 Title race MC** — `app/models/title_race.py` + 6 TDD tests + `/api/stats/title-race` + `/title-race` page. EPL: Arsenal 58.9% vs Man City 41.1% title.
2. **18.2 Relegation race** — same engine, `/relegation` page. Burnley + Wolves locked-in, Tottenham 65.5% at risk.
3. **18.3 Top-scorer race** — `app/models/top_scorer_race.py` + 5 tests + `/api/stats/top-scorer-race` + `/scorers-race` page. Haaland 28 projected, Thiago 24.4 (gap 3.6).
4. **18.4 Power rankings** — elo recomputed from match log twice per request (now vs 7d ago). `/power-rankings` shows week-over-week Δ + top-3 risers/fallers. MC overtook Arsenal +12.7, Chelsea biggest faller −24.1.
5. **18.5 H2H on /compare** — `/api/compare/history`; compare page renders last 10 meetings + model hit rate. ARS vs TOT: 8W-1D-1L, model 80% on this derby.
6. **18.6 Per-team SEO pages** — JSON-LD SportsTeam schema + `generateStaticParams` + 500-700-word Qwen narratives per team stored in new `team_narratives` table. Weekly cron seeds all 96 teams.
7. **18.7 Weekly auto-blog** — `generate_weekly_blog.py` + `auto_blog_posts` table + `/api/blog` endpoint; `lib/blog.ts` merges file-based + DB-based transparently. First post `week-17-2026` live (42% accuracy, 21/50).

Total block: ~30 hours over one burst. No test regressions. Block 19 next (Sharp credibility).

## 2026-04-24 01:45 +07 — Block 17 done: distribution (telegram bot + discord + email + embed)

Five items, end-to-end:

1. **17.1 Telegram bot interactive** — `app/telegram/bot.py` + `app/api/telegram.py`. Parser + 10 TDD tests + 6 handlers (/help /pick /edge /roi /clv /subscribe /subs). Webhook registered at predictor.nullshift.sh/api/telegram/webhook with secret-token validation. Announcement msg_id 143 posted on @worldcup_predictor.
2. **17.2 Team subscriptions** — `telegram_subscriptions` table + `/subscribe ARS` + `fan_out_to_team_subscribers` hook on goal + FT events in ingest_live_scores. End-to-end smoke OK: subscribe ARS → subs list → unsubscribe → list updates.
3. **17.3 Discord webhook** — `discord_webhooks` table + POST/DELETE `/api/discord/register` + `fan_out_to_discord` parallel to the telegram fanout. Rejects non-discord.com URLs; tracks last_ok_at + last_error.
4. **17.4 Email weekly digest** — `email_subscriptions` + `/api/email/subscribe` → token email → `/confirm` / `/unsubscribe`. Pure `render_digest_html()` (testable); `scripts/post_email_digest.py` + systemd timer `football-predict-email.timer` Mon 09:00 UTC. Dry run: 14 top-picks + 49 graded last week. `/subscribe` page in 5 langs.
5. **17.5 Embed widget** — `/embed/match/:id` self-contained card (SiteHeader skipped via middleware x-pathname + layout branch) + 1.5 KB `embed.js` loader + `/embed-docs` page with live preview iframe. `frame-ancestors: *` header set at middleware for cross-origin iframing.

Everything shipped via `git push vps main`. No test regressions (23 bot tests green + prior 10 watchdog tests green).

## 2026-04-24 00:55 +07 — Sprint 16: ops watchdog + /ops status page

Built `ops_watchdog.py` with 5 pure checkers (fixture_drift, stale_live, missing_recap, low_quota, stale_predictions) + Telegram dedup via `ops_alerts` table + systemd 5-min timer. First tick caught 3 real drift cases (Brighton-Chelsea, RM-Alaves, Girona-Betis stuck at scheduled 46h past kickoff). 10/10 TDD tests green.

Added `/api/ops/status` endpoint + public `/ops` page reusing the same checkers read-only — overall badge + per-subsystem row + offending match ids. New `finalise_missed_matches.py` resolves the stuck-scheduled class (1 API call per match via af_id → /fixtures?id=X) and is wired into the daily cron. Closed 5 stuck matches; `/ops` now green across the board.

Also during the same sprint (earlier): fixed class-of-bug asyncpg unknown-type binds (live-scores, backfill-fixtures) + recap-on-FT inline trigger so finished matches no longer wait for the 06:00 UTC cron. 

## 2026-04-21 00:40 +07 — 6-season historical backfill for LaLiga / Serie A / Ligue 1 / Bundesliga

Ran `ingest_season.py` across 4 leagues × 6 seasons (2019-20 → 2024-25) then `backtest.py` per season. 24 ingest passes + 6 walk-forward backtests. Previously only EPL had 7-season history; now **all 5 top leagues have the full matrix** so `/history` is apples-to-apples.

Post-backfill coverage: 100% prediction on every (season, league) pair except 2025-26 which is mid-season. First smoke of `/api/stats/history`: overall acc trend 49.0% (2019-20) → 52.3% (2024-25) → 50.3% (2025-26 in-season). La Liga specifically: 47.9% → 54.2% → 49.7%. Apples-to-apples year-over-year model improvement visible.

`/history` coverage caveat banner auto-hides since `leagues_covered` is now identical across seasons. No code changes — pure data backfill.

## 2026-04-20 14:15 +07 — Phase 15 shipped: strategy simulator (5 ships)

Full Phase 15 end-to-end — **4 strategies + 1 compare view**. Shared `_walk_bets` + `_wrap_result` helpers + `/api/stats/strategy-sim?name=X` uniform endpoint; each strategy is a pure function that returns the same `{bets, starting, final, peak, drawdown%, roi%, points}` shape so the shared `<StrategyChart>` works across all of them. 10 TDD tests total (2 per strategy + 2 ladder edge cases).

**Live data 2025-26 at 5pp edge:**

| Strategy | Bets | Peak | Final | ROI | DD |
|---|---|---|---|---|---|
| high-confidence filter | 59 | 105.2u | **102.2u** | **+2.2%** | 2.8% |
| value ladder | 293 | 127.9u | 0u | −100% | 100% |
| martingale | 12 | 112.8u | 0u | −100% | 100% |
| favorite fade | 762 | 100.0u | 7.4u | −92.6% | 92.6% |

High-confidence filter is the only net-positive strategy at this threshold. Favorite-fade losing 92.6% confirms the model has *real* signal (if fade were profitable, the model's edges would be noise). Martingale textbook ruin in 12 bets.

`/strategies` page with dropdown selector + per-strategy warning boxes. `/strategies/compare` renders all four on one SVG with colour-coded legend + summary table. 16/16 playwright e2e still green.

## 2026-04-20 13:55 +07 — Phase 11b + 14 shipped: XGB 21 → 27 features + retrain

Extended XGBoost feature set from 21 to 27: 3 new fatigue columns (congestion_home, congestion_away, is_midweek) and 3 new market-line columns (devigged `market_p_home/draw/away` from earliest stored odds — earliest, not closing, so no leak of information a value bettor acting early wouldn't have).

Train script now pre-fetches the earliest `:avg` odds row per match and joins into build_feature_row; falls back to (1/3, 1/3, 1/3) on missing. Live predict path (predict/service.py) does the same lookup at kickoff time. Also prints top-10 feature importance + warns when market features exceed 50% gain share (circular-fit canary).

**Walk-forward retrain 2024-25 holdout (new 27-feature model):**

- Holdout accuracy **55.41%** (+2.1pp vs 53.3% baseline)
- Holdout log-loss **0.9790** (−0.5% vs 0.984 baseline)
- Feature importance top-10: market_p_home (8.43), market_p_away (8.17), market_p_draw (2.91), **is_midweek (2.49)** ← new fatigue feature made rank 4, home_def (2.40), elo_home, elo_diff, home_att_home, away_att_home, away_def_away
- Market features gain share **27.4%** — below the 50% collapse threshold, so xG/Elo/form still carry most signal
- Saved to /data/football-predict-xgb.json, predict_upcoming re-ran with new model (58 upcoming predictions refreshed)

Both phases' success criteria satisfied. No regressions: 145 pytest + 16/16 e2e.

## 2026-04-20 13:40 +07 — Phase 13 shipped: lineup-sum power rating

`app/models/lineup_strength.py` + 6 TDD tests. `lineup_xg_rating` sums per-player xG/game across confirmed starters (full weight) + bench (BENCH_WEIGHT=0.24, ~22 min typical). Missing players silently contribute 0. `lineup_multiplier` clamps ratio to [0.70, 1.30] — ±30% max swing on any single lineup.

`predict/service._lineup_multiplier` joins match_lineups + player_season_stats + rolling team xG-per-match baseline (leak-safe, excludes current match). Blended into the injury × weather × referee × lineup stack on both teams' λ. Kicks in only when ≥ 11 starters confirmed; no-op otherwise.

`/api/matches/:id/lineup-strength` + chip on match detail page: `XI: H×1.05 / A×0.92`. Live on prod: match 4752 returns home×0.775, away×0.700 — both teams clamp-hit because their starters under-index season averages.

Lineup coverage is only ~10 matches today (ingest_lineups.timer is live but recent). The multiplier hook is wired; it'll accumulate leverage as coverage grows. No backtest numbers this phase — too thin a sample. 145 pytest + 16/16 e2e all green.

## 2026-04-20 13:25 +07 — Phase 11a shipped: fatigue context chip

`app/models/fatigue.py` + 5 TDD tests. `compute_fixture_context(df, home, away, kickoff)` returns rest_days home/away + rest_diff + 14-day congestion count per team + is_midweek flag. Strict prior-date window so the kickoff match itself never counts.

`/api/matches/:id/fatigue` endpoint pulls a 30-day lookback per league (one query covers both rest + congestion). Match detail page now shows a context chip: `Rest: 5d / 3d · congested 3/1 · midweek` — neon/error colour on the rest diff, amber on congested ≥ 3.

Scope split: Phase 11a (this) surfaces context; Phase 11b (future) injects these as new XGBoost features and retrains. Deferred because the current /tmp/xgb.json serves fine and any retrain needs its own walk-forward backtest to justify. Full suite 139 pass; 16/16 e2e still green.

## 2026-04-20 13:15 +07 — Phase 12 shipped: referee λ adjustment (plan-new)

Referee data backfilled from API-Football /fixtures — 3,634 historical rows across top-5 leagues (2019-20 → 2025-26). EPL 96% coverage, others 94-100%. Two bugs fixed inline: `&page=1` triggers 0 results on API-Football (omit it), and asyncpg `timestamptz` bind needs a `datetime` not an ISO string.

`app/models/referee.py` + 6 TDD tests. `referee_tendencies()` groups a sample by ref, returns `{goals_delta, n}` for refs with ≥ 30 matches. `referee_multiplier(delta, league_avg, cap=0.10)` applied symmetrically to both team λ in `predict/service.py` alongside injury + weather shrinks.

New endpoint `/api/matches/:id/referee` with 2-year rolling sample. Match detail chip shows "+0.38 g/game" next to the ref name (neon above, red below). Live samples: A. Taylor 31 matches × +0.09 Δ → λ×1.031; M. Oliver 38 × −0.07 → λ×0.978. Multipliers stay within ±5% in the sample, well under cap.

Backtest delta pending — next predict_upcoming run picks it up automatically. Full test suite 134 → all pass; 16/16 playwright e2e still green.

## 2026-04-20 13:05 +07 — Phase 9 replaced: Pinnacle sharp column + Polymarket nope

Polymarket probed for a per-fixture no-vig reference (plan-new Phase 9): `tag_slug=soccer` returns 100 events, **0 individual-match markets** (all outrights — EPL Winner, Relegation, 2nd Place). Not useful when our surface is per-fixture 1X2/OU/BTTS/AH. Phase 9 Betfair Exchange also redundant: API-Football Ultra already gives us `af:Betfair` + `af:Pinnacle` + 20+ retail books.

Instead: `/api/matches/:id/markets-edge` gains **pinnacle_prob + sharp_disagreement_pp** per row. Builder devigs Pinnacle's implied odds per (market, line) family (handles 2-way OU/BTTS and 3-way 1X2 uniformly). 3 new TDD tests. `<MarketsEdge>` grows a "Sharp" column between Model and Fair; amber when model diverges from sharp by ≥ 3pp.

Live smoke on match 330: Over 2.5 model 62.9% vs Pinnacle 52.4% (+10.4pp model-overconfident) despite +22pp edge at matchbook — shows the amber as a useful warning. AH Home +0.5 model 73% vs Pinnacle 51.5% (+21.6pp divergence) — model thinks this is an easy home favorite, sharp sees a near-pickem.

## 2026-04-20 12:40 +07 — Phase 6b upgrade: API-Football Ultra as primary odds

User confirmed we have API-Football Ultra (75k req/day). Switched from the-odds-api free tier to API-Football for multi-market odds: **unlocks BTTS** (free-tier the-odds-api 422'd it), plus full O/U ladder (0.5→7.5) and full AH ladder (-2.5 → +2.5 in 0.25 steps). New `scripts/ingest_apifootball_odds.py` pulls 1X2 + O/U + BTTS + AH (bet ids 1, 5, 8, 4) per league/season/page. One run wrote **~40,600 per-book rows across top-5 leagues** (EPL 12.2k, Serie A 9.9k, Bundesliga 8.9k, Ligue 1 9.2k, LaLiga 0.5k due to low upcoming count this week).

`/api/matches/:id/markets-edge` filter broadened from strict `odds-api:*` to "any per-book" (`odds-api:*` OR `af:*`, excluding `:avg`) so best-odds shopping mixes the-odds-api + API-Football books transparently. Live smoke on CP vs WH: +40pp edge on AH Home -1.5 at Betfair, +30pp on Over 3.5 at Unibet, +7pp BTTS Yes at William Hill — way more flagged rows than Phase 6b ship 1 had.

One matcher bug fixed inline: `/odds` responses don't carry team names, only `fixture.id` + `fixture.date` + `league.id`. Join uses `matches(league_code, kickoff_time)` timestamp equality (precise to the minute) instead of name matching. Systemd timer `football-predict-af-odds.timer` runs every 30 min (~2,880 calls/day = 4% of quota). CLAUDE.md updated so future sessions default to API-Football, not the-odds-api.

## 2026-04-20 12:25 +07 — Phase 6b: real book-odds edge overlay (plan-new)

Migration 017 adds `match_odds_markets (match × source × market × line × outcome)`. `ingest_live_odds.py` now fetches `h2h,totals,spreads` in a single request (still 1 the-odds-api credit per call) and writes dual per-book + pooled-avg rows. Free tier rejects `btts` with 422 so BTTS stays pure-model; spreads (Asian handicap) takes its slot. First prod ingest populated **2,020 market rows across 100 events** in 6 API credits.

New `/api/matches/:id/markets-edge` joins the scoreline-matrix probs with best book odds and returns rows ready for UI — `model_prob · fair_odds · best_book_odds · edge_pp · flagged`. `<MarketsEdge>` rewritten to the edge-table shape with neon rows at ≥5pp. 7 TDD tests (incl. a `_RecordLike` stub that catches an asyncpg.Record attr-vs-subscript bug found by smoke-testing on prod right after ship — fixed in the same commit chain).

First live edges on prod: match 4130 LEC vs FIO — Over 2.5 at onexbet 2.32 = +6.48pp edge; AH Home +0.5 at gtbets 1.70 = +13.12pp. These are REAL edges on fresh pre-kickoff lines, not backtest noise. Phase 5 CLV logging will eventually tell us whether they close profitable.

## 2026-04-20 11:55 +07 — Phase 7: Kelly virtual bankroll (plan-new)

**Simulator.** `_compute_kelly_bankroll` walks value bets chronologically, sizes via fractional Kelly on current balance, tracks peak + max drawdown. 9 TDD tests cover compounding, cap clamp, drawdown, chronological sort, below-threshold skip, plus a mutual-exclusivity test that caught a shipping bug on the first smoke test (simulator was staking each flagged side independently → 915 bets, 100% DD on real data because H+D both flagged in ~160 matches means >50% at-risk per match; fixed to stake only the highest-edge side per match).

**Endpoint.** `GET /api/stats/roi/kelly` (cap, starting configurable). `/roi` page gains a Flat vs Kelly toggle. KellyChart renders bankroll line + peak reference + drawdown shaded in red + 5 stat chips (start/peak/final/roi/DD). When DD > 95% a warning block explains honestly that the flagged edges are noise, not real edges, and recommends raising threshold / using quarter-Kelly / filtering to per-league positive ROI via `/roi/by-league`.

**Reveals.** Over full 2025-26, flat 1u at 5pp = -17% ROI (915 bets); Kelly 25% cap = 100% drawdown. The model doesn't have real edge at these thresholds season-wide — the short-term +20% wins we saw in per-league 30d snapshots are mean-reversion. Phase 5 CLV data will tell us definitively when it accumulates.

## 2026-04-20 11:45 +07 — fix: player photos were all blank

Root cause: `media.api-sports.io/football/players/*.png` returns 403 for anonymous browsers — only responds when the `x-apisports-key` header is injected, which our server holds but `<img src>` from the browser can't send. Additionally all 2,687 player rows had NULL `photo_url` because the photo ingest had never been run on the prod DB.

Fix: new proxy endpoint `GET /api/players/photo/{api_football_id}` that fetches upstream with the server-side key and serves the bytes with `Cache-Control: public, max-age=2592000, immutable` (~one fetch per player per month). Scorers / player-profile / team-top-scorers endpoints now rewrite `photo_url` to point at this proxy whenever `api_football_player_id` is populated. Ran `ingest_player_photos.py --season 2025-26` on the VPS → 117 photos matched across the top-scorer lists of all 10 leagues we track (42% unmatched due to non-scorers + name diacritic mismatches — acceptable for the strip). Daily cron (`ops/daily.sh`) already re-runs this, so it stays fresh.

## 2026-04-20 11:40 +07 — Phase 6 ship 1: AH + SGP pricing (plan-new)

**Math (TDD).** `prob_asian_handicap(matrix, line, side)` in `app/models/markets.py` — half, integer, and quarter lines; bettor-perspective sign convention (home +0.5 covers draws; away -0.5 needs outright win). `prob_sgp_btts_and_over(matrix, line)` reads the correlated joint directly off matrix cells. 7 new tests in `test_markets.py`; full backend suite 116 green.

**Endpoint.** `GET /api/matches/:id/markets` extended with `prob_ah_home_{±0.5, ±1.5}` + `prob_sgp_btts_over_2_5`. Backward-compatible: fields default to 0.0 for any cached stale response.

**UI.** New `<MarketsEdge>` below the existing `<MarketsPanel>` on `/match/:id`. Surfaces every derived market as a table: model prob, fair decimal odds, plus an SGP mispricing note quantifying how much the "independence assumption" priced by many books would miss the true joint. On the sample fixture I smoke-tested, SGP (BTTS & Over 2.5) came in at 38.4% vs naive product 24.3% — book independence would under-price by 14pp, a real SGP edge.

**Deferred (Phase 6b).** Direct odds ingest for totals / BTTS / AH markets and full edge overlay. For now the user compares fair odds to their own book manually.

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
