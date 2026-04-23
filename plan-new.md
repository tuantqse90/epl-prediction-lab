# plan-new.md — Sharp-bettor tooling + model improvements

> Continuation of the MVP. This file scopes **Phase 5 onward** — first, sharp-bettor analytics on top of the existing prediction stack (Phases 5–10); then model-quality improvements that pro bettors actually use (Phases 11–14). Progress tracked in [`PROGRESS.md`](./PROGRESS.md).

---

## 0. Scoping

**What this file is.** Two bodies of work on top of the MVP:

1. **Analytics + display** of the same signals a professional bettor uses: closing-line value, best-odds shopping, correlated-market mispricing, fractional Kelly, per-league edge maps, sharp-consensus reference. (Phases 5–10.)
2. **Model improvements** that elite bettors bake into their own engines: rest/fatigue/fixture congestion, referee tendencies, lineup-sum power ratings, market-line features. (Phases 11–14.)

**What it is not.**

- Not a sportsbook. No balance, no deposit, no withdraw.
- Not a custodial market. The Phase 4.2 "non-custodial prediction market" stays dropped per `docs/environment.md` out-of-scope rule (regulatory risk, Vietnam context).
- Not "tipster" content. We publish our own edge numbers and the methodology; users decide whether to act.

---

## 1. Current state (what's already built)

| Capability | Status | Evidence |
|---|---|---|
| Best-odds shopping | ✅ Shipping | `backend/app/api/stats.py` — `best_odds` CTE picks MAX(odds) per outcome across `match_odds` sources |
| Edge threshold filter | ✅ Shipping | `/api/stats/roi?threshold=0.05`, `<QuickPicks>` at 5pp cutoff |
| Fair-probs devig | ✅ Shipping | `backend/app/ingest/odds.py` — `fair_probs()` + `edge()` |
| Fractional Kelly (FE) | ✅ Shipping | `frontend/app/parlay/page.tsx` — `kelly()` capped 0.25 |
| Per-league ROI | ✅ Shipping (Phase 8) | `GET /api/stats/roi/by-league`, `/roi/by-league` page, QuickPicks filter |
| CLV logging | ✅ Infra shipping (Phase 5) | `closing_odds` table, `ingest_closing_odds.py` cron every 5 min, `GET /api/stats/clv`, `/proof` card — waiting for data to accumulate |
| Correlated-market pricing | ✅ Shipping (Phase 6) | `prob_asian_handicap`, `prob_sgp_btts_and_over` in `app/models/markets.py`; `<MarketsEdge>` on `/match/:id` |
| Multi-market book odds | ✅ Shipping (Phase 6b) | `match_odds_markets` table, `ingest_apifootball_odds.py` (API-Football Ultra primary), the-odds-api fallback; `GET /api/matches/:id/markets-edge` with per-row best book odds + edge |
| Backend Kelly + virtual bankroll | ✅ Shipping (Phase 7) | `_compute_kelly_bankroll`, `GET /api/stats/roi/kelly`, `<KellyChart>` on `/roi` |
| Sharp-consensus reference | ✅ Shipping (Phase 9 replacement) | Pinnacle devigged column on `<MarketsEdge>` + amber flag on model-vs-sharp ≥ 3pp disagreement |
| In-play model | ⏸ Parked (Phase 10) | pre-match probabilities frozen at kickoff; live λ re-estimator + WebSocket broadcast = too much infra for now |

**Model quality:**

| Improvement | Status | Evidence |
|---|---|---|
| Rest-days feature | ❌ Not in XGB | — |
| Fixture congestion flag | ❌ Not in XGB | — |
| Referee adjustment | ❌ Not used | `matches.referee` stored, never read by the model |
| Lineup-sum player xG | ❌ Not built | `match_lineups` + `player_season_stats` joined for injury shrink only |
| Market-line as feature | ❌ Not built | one-way data flow: model → market edge, never back |

---

## 2. Phase 5 — Closing-Line Value (CLV) ✅

Infra all shipped. `closing_odds` table + cron every 5min + CLV endpoint + `/proof` card. Data will populate as fixtures approach kickoff.

**Next action once data fills in:** verify `mean_clv` is positive over a 100+ bet sample. Negative CLV = model is not picking winners the market slowly agrees with, and the edge-flagging at 5pp threshold is pure noise (Phase 7 Kelly simulator already hinted at this with 100% DD).

## 3. Phase 6 — Correlated markets ✅

Shipped. `prob_asian_handicap(matrix, line, side)` and `prob_sgp_btts_and_over(matrix, line)` in `app/models/markets.py`. `<MarketsEdge>` on `/match/:id` shows AH -1.5/-0.5/+0.5/+1.5 home-side + SGP note when joint differs from naive product. 7 TDD tests.

## 4. Phase 6b — Multi-market book odds ✅

Shipped. `match_odds_markets` table. `ingest_apifootball_odds.py` pulls 1X2 + O/U (0.5→7.5) + BTTS + AH ladder from API-Football Ultra (75k/day quota vs the-odds-api free 500/mo). ~40k per-book rows across top-5 leagues. `GET /api/matches/:id/markets-edge` joins model probs with best book odds; `<MarketsEdge>` flags rows at edge ≥ 5pp. Systemd timer `football-predict-af-odds.timer` every 30 min.

## 5. Phase 7 — Backend Kelly + virtual bankroll ✅

Shipped. `_compute_kelly_bankroll` walks value bets chronologically, compounds via fractional Kelly, tracks peak + max drawdown. 9 TDD tests (incl. a mutual-exclusivity test that caught an over-staking bug on first smoke test). `<KellyChart>` on `/roi` with Flat ↔ Kelly toggle.

## 6. Phase 8 — Per-league edge map ✅

Shipped. `_compute_roi_metrics` + `_compute_roi_by_league` pure aggregators (6 TDD tests). `GET /api/stats/roi/by-league?window=7d|30d|90d|season`. `/roi/by-league` page with per-league table + window + threshold chips. `<QuickPicks>` now hides leagues with 30d ROI < 0.

## 7. Phase 9 — Sharp-consensus reference ✅ (replaced)

Original scope (Betfair Exchange + Polymarket) dropped:
- Betfair Exchange already in API-Football's roster as `af:Betfair` — API-Football Ultra covers the feed.
- Polymarket soccer = 100 events but **0 individual-match markets** (all outrights: League Winner, Relegation, 2nd Place). Useless as a per-fixture sharp reference.

Replacement shipped: **Pinnacle devigged probability column on `<MarketsEdge>`**. Pinnacle's ~2% vig is the tightest on retail; devigging gives a sharp reference comparable in quality to an exchange mid for our analytics-only use case. Amber flag when model diverges from Pinnacle by ≥ 3pp.

## 8. Phase 10 — In-play model ⏸ parked

Requires per-second score/event feed + real-time λ re-estimator + WebSocket broadcast. Revisit when someone wants it enough to pay for the infra.

---

## 9. Phase 11 — Rest, fatigue, fixture-congestion features ✅

`app/models/fatigue.py` + 5 TDD tests. `compute_fixture_context` returns rest_days + congestion (14-day) + is_midweek. `/api/matches/:id/fatigue` endpoint + chip on match detail. **Phase 11b (XGB retrain with these features)** shipped in combined Phase 14 retrain — `is_midweek` reached rank-4 by feature importance.

## 10. Phase 12 — Referee adjustment ✅

`app/models/referee.py` + 6 TDD tests. Rolling 2-season per-ref goals-per-match delta, symmetric λ multiplier capped ±10%. Historical data backfilled across 3,634 top-5 league matches via API-Football `/fixtures`. `/api/matches/:id/referee` endpoint + chip `+0.38 g/game` on match detail.

## 11. Phase 13 — Lineup-sum power rating ✅

`app/models/lineup_strength.py` + 6 TDD tests. `lineup_xg_rating` aggregates starters (full) + bench (0.24×), multiplier clamped to [0.70, 1.30]. `/api/matches/:id/lineup-strength` endpoint + chip `XI: H×1.05 / A×0.92`. Kicks in only when ≥ 11 starters confirmed; no-op otherwise.

## 12. Phase 14 — Market-line XGB feature ✅

3 market features (`market_p_home/draw/away` devigged from earliest `:avg` odds) + 3 P11b fatigue features → 21→27 feature model. **Walk-forward retrain 2024-25 holdout: acc 53.3 → 55.41% (+2.1pp), log-loss 0.984 → 0.9790 (−0.5%), market-gain share 27.4%** (below the 50% circular-fit alarm). Saved to `/data/football-predict-xgb.json`; `predict_upcoming` refreshed 58 predictions.

---

## 13. Phase 15 — Strategy simulator (current)

**Hypothesis.** Users learn more from *watching* strategies fail on real data than from reading about them. A strategy simulator lets users flip between named strategies — some sharp, some bad — and see the full historical bankroll trajectory for each. Makes betting-math intuitive without editing code.

**Strategies to ship** (independent, shippable as own commits):

1. [ ] **15.1 Value ladder** — stake = base_unit × (edge_pp / 5pp), cap 5×. Middle-ground between flat-1u and full Kelly. ~1h.
2. [ ] **15.2 High-confidence filter** — flat 1u but only when `model_prob ≥ 0.60 AND edge_pp ≥ 5`. Noise filter. ~1h.
3. [ ] **15.3 Martingale** — double after loss, reset on win. Pedagogical ruin demo. ~1h.
4. [ ] **15.4 Favorite fade (contrarian)** — bet AGAINST the model pick when edge ≥ 10pp. Negative control — expected terrible ROI proves model has signal. ~1h.
5. [ ] **15.5 Compare view** — `/strategies/compare` renders 3 strategies side-by-side on the same season + bets. Martingale ruin vs Kelly growth in one screen. ~1h.

**Deliverables per strategy (uniform):**

- Pure simulator fn in `app/api/stats.py` — walks `_ROI_QUERY` rows, returns `{bets, starting, final, peak, max_drawdown_pct, points, roi_percent}` — same shape as `_compute_kelly_bankroll` so the chart is reusable.
- 2 TDD tests per strategy — core behaviour + one edge case.
- Endpoint `GET /api/stats/strategy-sim?name=X&threshold=Y&starting=100` — uniform response shape.
- `/strategies` page with dropdown selector reusing a `<StrategyChart>` component (fork of `<KellyChart>`).

**Cost.** ~1h per strategy, 5h total. No new data, no ingest, no model touch.

**Scope rule.** If the underlying model ROI is flat/negative at the chosen threshold (as Phase 7 Kelly already warned at 5pp), the page copy SAYS SO — not hide it. Transparency over marketing.

---

## 14. Sequencing

```
Analytics (done)      Phases 5, 6, 6b, 7, 8, 9-sharp       ✅
Analytics (parked)    Phase 10 in-play                     ⏸
Model quality (done)  Phases 11 (+11b), 12, 13, 14         ✅
Strategy sim (current)  Phase 15.1 → 15.2 → 15.3 → 15.4 → 15.5
```

Ship order: **15.1 → 15.2 → 15.3 → 15.4 → 15.5** — each ~1h independent commit; shared `<StrategyChart>` + endpoint stable from 15.1 onwards so later strategies are pure additions.

---

## 15. Success criteria

Before closing a phase, `PROGRESS.md` entry must include:

- **Analytics phases**: backtest numbers over the last 2 full seasons (accuracy, ROI, CLV mean, log-loss). Live screenshot of the new surface. Tests-pass count + delta.
- **Model-quality phases**: walk-forward log-loss + accuracy before/after on out-of-sample seasons. Feature-importance diff (catch accidental reliance on a single feature). Live sample of the updated prediction on one match.
- **Strategy sim**: final units / peak / max DD / ROI% over 2024-25 holdout with starting=100. Screenshot of `/strategies?name=X` page.

If CLV mean is still negative after Phase 5 data accumulates: stop model-quality work, diagnose the model. Adding features to a model whose closing line consistently beats us is polishing a losing strategy.

---

## 16. Sprint 16 — Ops watchdog (current)

**Why now.** Two silent failures hit prod in 48h: 100 fixtures with stale `kickoff_time` that hid Man City from live, and post-match recaps sitting empty for 9h because they were gated on the daily cron. Both were fixed reactively. A watchdog would have caught both within 5 min.

**Build.** One script `backend/scripts/ops_watchdog.py` runs 5 independent checkers. Each returns a list of offending row-ids + a short message; top-level dispatcher aggregates + posts one Telegram message per tick when any checker is non-empty. Idempotent via `ops_alerts` table (alert_hash, last_sent_at) so we don't re-spam the same issue every 5 min.

**Checkers (each a pure function, TDD):**

1. `fixture_drift` — `status='scheduled'` + `kickoff_time < NOW() - 2h`. Catches Man City.
2. `stale_live` — `status='live'` + `live_updated_at < NOW() - 5 min`. Catches a frozen feed.
3. `missing_recap` — `status='final'` + `recap IS NULL` + `kickoff_time < NOW() - 12h`. Catches LLM outages.
4. `low_quota` — last `x-ratelimit-requests-remaining` < 10k. Catches pre-exhaustion.
5. `stale_predictions` — `scheduled` + `kickoff_time < NOW() + 48h` + no `predictions` row. Catches predict_upcoming failing silently.

**Deliverables.**
- `ops_watchdog.py` + `ops_alerts` migration + 5 checker functions + TDD tests (2 per checker).
- systemd `football-predict-watchdog.timer` every 5 min.
- `/api/ops/status` endpoint + `/ops` public page with green/red row per subsystem (reuses the checker functions read-only).

**Done when.** Next stale kickoff / dead feed gets a Telegram ping within 5 min, and `/ops` shows exactly what's broken without ssh.

## 17–20. Roadmap blocks (Sprint 16 done · blocks ship in priority order)

The roadmap from here is organised into four **blocks** (not strict sprints). Each block is 4–6 days of shippable commits, each item inside a block is independently shippable (~0.5–1 day) so nothing is all-or-nothing.

Ship order top-to-bottom. Within a block, order can be swapped without breaking anything.

---

### Block 17 — Distribution (~5 days) · "get the data in front of more eyeballs"

Currently: predictor.nullshift.sh is the only surface. This block adds three second-channel distributions that all reuse existing APIs — minimal data work, maximal reach.

| # | Ship | Hours | Surface |
|---|---|---|---|
| 17.1 | **Telegram bot interactive** — `/pick today`, `/pick PSG`, `/edge`, `/clv`, `/roi 30d` | 6 | `@worldcup_predictor_bot` |
| 17.2 | **Telegram team subscriptions** — `/subscribe arsenal` → HT/FT/goal pings for that team | 4 | stored in `telegram_subscriptions` table |
| 17.3 | **Discord webhook poster** — daily digest + goal-time pings into any guild | 3 | `discord_webhooks` table (user-posted URLs) |
| 17.4 | **Email weekly digest** — opt-in, Mon 09:00 UTC, top picks + last week's hits/misses | 6 | `email_subscriptions` + Resend/SES transport |
| 17.5 | **Embed widget** — iframe + 12KB JS snippet for a single match prediction card | 4 | `/embed/match/:id` + `embed-loader.js` |

**Done when.** Three distinct surfaces beyond the web pulling the same data. Embed widget loads on a test blog without CSS bleed.

---

### Block 18 — Viral / engagement (~6 days) · "content people share without prompting"

Plenty of users open /table or /scorers once a week. This block adds high-interest seasonal pieces that drive repeat visits and social shares.

| # | Ship | Hours | Surface |
|---|---|---|---|
| 18.1 | **Title race Monte Carlo** — per league: P(champions), P(top-4), top-4 odds from simulated remaining fixtures | 8 | `/api/stats/title-race` · `/title-race` page |
| 18.2 | **Relegation race Monte Carlo** — same engine, bottom-3 probability + drama chart | 3 | reuse 18.1 · `/relegation` page |
| 18.3 | **Top-scorer race projection** — Golden Boot / Pichichi / Capocannoniere / Torschützenkönig / Soulier d'Or via per-player xG × remaining games | 5 | `/api/stats/top-scorer-race` · `/scorers-race` page |
| 18.4 | **Power rankings** — pure-elo-sorted league table with week-over-week arrows; "biggest movers" strip | 4 | `/power-rankings` page |
| 18.5 | **H2H on /compare** — "last 10 meetings, model accuracy on this pairing" block | 4 | extends `/compare/:home/:away` |
| 18.6 | **Per-team SEO page** — `/team/manchester-city` with 2k-word auto-generated story (Qwen-Plus once/week), JSON-LD `SportsTeam` schema, xG trend, upcoming | 8 | 100 new indexable pages (~20/league × 5) |
| 18.7 | **Weekly auto-blog** — every Mon 10:00 UTC, Qwen-Plus drafts "Week N: what the model learned" → `/blog/:slug` | 5 | `blog_posts` table + RSS feed |

**Done when.** Each viral piece shares a clean URL suited for Twitter/Telegram post embed. 18.6 + 18.7 compound over weeks → organic search growth.

---

### Block 19 — Sharp-bettor credibility (~5 days) · "show the homework"

Sharp users want to see receipts before trusting stake sizing. This block surfaces exactly how the model performs, where it's over-confident, and where the sharpest books disagree with it.

| # | Ship | Hours | Surface |
|---|---|---|---|
| 19.1 | **Calibration curve** — per prob-decile hit rate (predicted 60% → actual 58%) with Brier breakdown | 6 | `/calibration` page + `/benchmark` widget |
| 19.2 | **Team-specific model accuracy** — "Model hits Arsenal 62% · Crystal Palace 38%" cross-table | 4 | `/benchmark/by-team` page |
| 19.3 | **Ensemble disagreement flag** — Poisson/Elo/XGB three-leg vote; surface "tricky" matches where they disagree | 4 | flag on `/match/:id` + filter chip on homepage |
| 19.4 | **Line movement chart** — home odds from T-24h → T-0 per bookmaker, visible steam moves | 6 | `/match/:id` new tab · needs 30-min snapshots into new `odds_history` table |
| 19.5 | **Sharp vs square divergence** — when Pinnacle and Bet365 diverge ≥ 5%, explain what that means | 3 | adds column to `<MarketsEdge>` |
| 19.6 | **Season-over-season equity curve** — 7-year flat-Kelly P&L chart on `/benchmark` | 3 | `/api/stats/equity-curve` |

**Done when.** A user can answer "is the model actually sharp?" in under 60 seconds on the site.

---

### Block 20 — Personal layer (~5 days) · "your view, your ROI"

Non-custodial, no auth stack. Everything stored client-side by default; optional 6-digit PIN if the user wants cross-device sync.

| # | Ship | Hours | Surface |
|---|---|---|---|
| 20.1 | **My picks (localStorage)** — user logs their real bets per match; compares their pick to model pick | 5 | `/my-picks` page, existing `betslip.ts` foundation |
| 20.2 | **Personal ROI vs model ROI** — "You +4.2% · Model +1.8% · Flat 0%" comparison chart | 4 | extends 20.1 |
| 20.3 | **Watchlist / favourites** — pin teams; everything else on the site filters to those by default | 3 | `favorites.ts` localStorage helper + UI chip |
| 20.4 | **Optional PIN sync** — 6-digit code maps localStorage → `user_sync` table, pull/push across devices | 6 | no email, no password — PIN collision rare at this scale |
| 20.5 | **PWA install + push** — manifest already present, add service worker + Web Push VAPID for goal/FT pings | 8 | "Add to Home Screen" works on iOS 17.4+ |

**Done when.** User has a reason to come back beyond curiosity: their own log.

---

### Block 21 — Model depth v2 (~6 days) · "make the model noticeably sharper"

Phase 11-14 took the XGB from 21→27 features and added fatigue/referee/lineup adjustments. Ceiling on that branch is probably hit. This block pulls in six **structural** signals the current ensemble doesn't see at all.

| # | Ship | Hours | What moves |
|---|---|---|---|
| 21.1 | **Home/away split per team** — separate Poisson λ when home vs away | 6 | fixes Liverpool's Anfield premium, City's away struggles |
| 21.2 | **Derby multiplier** — tag derby fixtures (NLD, El Clasico, Merseyside, etc.), inflate variance | 4 | `match_tags` table; UI chip "derby" |
| 21.3 | **Manager change tracker** — 14-day rolling xG before/after, flag "new-manager bounce" | 6 | `manager_tenure` table populated from RSS + manual admin |
| 21.4 | **Player xG vs defense strength** — adjust striker xG by opponent's conceded-xG rank | 5 | extends `ingest_players.py` + `predict/service.py` λ calc |
| 21.5 | **DC rho re-estimate per league quarter** — dynamic ρ instead of a single season constant | 4 | `calibrate_rho.py` rerun per (league, quarter) |
| 21.6 | **Cup-vs-league prior** — Copa del Rey vs La Liga get different λ priors | 5 | needs a `competition_type` column + separate train step |

**Done when.** Walk-forward backtest on 2024-25 shows +0.5pp accuracy or −0.3% log-loss over current 27-feature baseline. No improvement → revert per-item (not whole block).

---

### Block 22 — Sharp tooling v2 (~5 days) · "tools bettors actually pay for"

Sharp readers get 19.1–19.6 (calibration, line movement, etc.). This block gives them action-oriented calculators that weren't in the Sprint 6 correlated-markets pass.

| # | Ship | Hours | Surface |
|---|---|---|---|
| 22.1 | **Arbitrage detector** — per fixture, find 2-book combinations where Σ(1/odds) < 1 | 5 | `/arb` page + filter on `/match/:id` |
| 22.2 | **Middle-gap finder** — Pinnacle AH −0.5 vs Bet365 AH +0.5 on same fixture; both cash on exact draw | 4 | `/middles` page |
| 22.3 | **Closing-line beat rate per market** — historical CLV split by 1X2 vs O/U vs AH vs BTTS | 3 | extends `/proof` card |
| 22.4 | **Kelly fraction explorer** — slider 0.1–1.0, see DD vs growth tradeoff for user's bankroll | 4 | new `<KellyExplorer>` on `/roi` |
| 22.5 | **Book weight calculator** — Pinnacle 0.6, Bet365 0.3, Betfair 0.1 weighted consensus | 3 | improves `MarketsEdge` sharp column |
| 22.6 | **Tax-aware ROI toggle** — adjust for VN / EN / EU book tax | 2 | dropdown in `/roi` |

**Done when.** Arb + middles pages return at least one opportunity on a typical matchday (even 0.3% arb is enough proof of working pipeline).

---

### Block 23 — UX polish (~4 days) · "reduce bounce rate without adding features"

Plenty of small papercuts. No single item is load-bearing; the compound effect is real.

| # | Ship | Hours |
|---|---|---|
| 23.1 | **Dark/light theme toggle** — Payy is black-first but let power users switch | 3 |
| 23.2 | **Mobile bottom nav** — 5 icons (home, matches, strategies, telegram, ops) instead of cramped dropdown | 4 |
| 23.3 | **Skeleton loaders** on all data-fetching pages — no more mid-SSR blank flash | 3 |
| 23.4 | **Tooltip glossary** — hover "xG" / "CLV" / "Kelly" / "edge" → 2-line definition + link to `/glossary` | 4 |
| 23.5 | **Keyboard shortcuts panel** — `?` key opens cheat sheet (already have `⌘K`) | 2 |
| 23.6 | **Sound on goal (toggleable)** + haptic on mobile for picks | 3 |
| 23.7 | **Inline edit betslip** — stake + odds editable without leaving the card | 3 |

**Done when.** Mobile Lighthouse PWA score ≥ 90. First contentful paint < 1.5s on 3G.

---

### Block 24 — Internal tools (~4 days) · "help me ship faster + safer"

Ops watchdog is external-facing. This block is the admin-facing counterpart.

| # | Ship | Hours |
|---|---|---|
| 24.1 | **Error log dashboard** — read-only `/admin/errors` over existing `error_log` table with filter by endpoint/time | 4 |
| 24.2 | **Page-level analytics** — self-hosted Plausible or a 50-line custom logger → `/admin/analytics` | 5 |
| 24.3 | **Feature flags** — simple `feature_flags` table + `useFlag()` React hook, admin toggle | 4 |
| 24.4 | **Staging environment** — `docker compose --env-file .env.staging` twin on port 3501/8501, deploys from `staging` branch | 6 |
| 24.5 | **One-click rollback** — `deploy/rollback.sh` retags the prior image + restarts | 2 |
| 24.6 | **Quota forecast** — ops watchdog extension: "at current rate API-Football exhausts at 23:42 UTC" | 3 |
| 24.7 | **DB snapshot drill** — monthly automated pg_dump restore test to a scratch container, email pass/fail | 4 |

**Done when.** A new contributor can deploy to staging + roll back without asking me. Error log surfaces bugs within an hour of happening.

---

### Block 25 — Content / SEO depth (~5 days) · "long-tail organic traffic"

Block 18 seeded viral content. This block builds the durable long-tail — things that keep pulling search traffic after the hype fades.

| # | Ship | Hours |
|---|---|---|
| 25.1 | **`/glossary` page** — every jargon term on the site (xG, CLV, Kelly, devig, SGP, AH) with examples | 4 |
| 25.2 | **`/about-our-model`** — methodology transparency; Poisson + DC + Elo 0.20 + XGB 0.60 ensemble explained in plain English | 4 |
| 25.3 | **Season story per team** — auto-generated long-form recap at season end: "Arsenal 2024-25 in 20 predictions" | 6 |
| 25.4 | **Match of the week** — auto-picked every Friday: highest model-vs-market edge + most-interesting pairing | 3 |
| 25.5 | **Player deep pages** — `/players/:slug` already exists; add historical xG trend chart + career photo carousel + model-based fantasy value | 5 |
| 25.6 | **Changelog page** — public `/changelog` rendered from `PROGRESS.md` filtered for user-visible changes | 2 |
| 25.7 | **Press-kit page** — logos, screenshots, one-line description, contact email | 2 |

**Done when.** Indexable page count ≥ 800 (5 leagues × ~20 teams × 1 story page + 100 glossary + 50 match-of-week + blog archive). Organic search traffic trends up month-over-month.

---

### Block 26 — Developer API + partner tier (~6 days)

Make the data queryable programmatically. No custody, no real money — just clean API + quota + key management so partner sites can build on top.

| # | Ship | Hours |
|---|---|---|
| 26.1 | **API key issuance** — `/api/keys` admin page + `api_keys` table (hash, scope, rate_limit, last_used) | 5 |
| 26.2 | **Rate limiting** — Redis-free in-process token bucket keyed on `Authorization: Bearer <key>` | 4 |
| 26.3 | **Usage metrics** — per-key request counts, p95 latency, errors → `/api/keys/:id/metrics` | 4 |
| 26.4 | **Public OpenAPI docs page** — curated subset of endpoints at `/api-docs` with examples in curl/python/JS | 3 |
| 26.5 | **Webhook callback** — partner registers a URL; we POST on new prediction / new FT result | 6 |
| 26.6 | **CORS whitelist per key** — partners can call the API from their browser without exposing the key server-side | 3 |
| 26.7 | **Billing-ready stub** — usage row per request, Stripe integration deferred but schema ready | 2 |

**Done when.** External developer can `curl -H "Authorization: Bearer pl_xxx" https://predictor.nullshift.sh/api/matches` and have it respected with quotas/metrics.

---

### Block 27 — Deeper analytics (~7 days) · "signal nobody else surfaces"

Beyond the Block 19 credibility pass. These are the pieces we'd be proud to pitch to a sharp-bettor community.

| # | Ship | Hours |
|---|---|---|
| 27.1 | **Player radar charts** — xG/match, xA/match, shots/90, key passes/90 vs position baseline | 5 |
| 27.2 | **Manager tenure tracker** — plot every manager's win rate, points-per-game, xGD/game across their tenure | 6 |
| 27.3 | **Transfer-window impact** — flag matches where a team's starter changed ≥ 3 from the prior window; measure λ adjust | 6 |
| 27.4 | **Set-piece specialist detection** — % goals from corners/free-kicks per team, and which player executes | 5 |
| 27.5 | **Squad depth index** — (bench lineup_xg_rating / starter lineup_xg_rating) — lower = thinner squad | 4 |
| 27.6 | **Travel distance proxy** — km between consecutive fixtures; deep-away-trip penalty on λ | 4 |
| 27.7 | **Chain-of-form streaks** — 5-match rolling xG vs expected; flag teams due for regression | 3 |

**Done when.** Every match detail page has at least one "you won't find this on FlashScore" widget.

---

### Block 28 — Localisation depth (~5 days) · "real VI/TH/ZH/KO not just EN fallback"

Right now TH/ZH/KO fall through to EN for anything not explicitly translated. This block makes non-EN first-class.

| # | Ship | Hours |
|---|---|---|
| 28.1 | **Translation audit** — extract every `tLang` dict, find all en-only keys, fill with Qwen-Plus once (not LLM at runtime) | 6 |
| 28.2 | **VN-specific: local bookmaker odds** — FB88 / Vietbet scraper + show VND-denominated stakes on `/roi` | 8 |
| 28.3 | **ZH Simplified & Traditional split** — zh-CN vs zh-TW; default via Accept-Language | 3 |
| 28.4 | **KR: date + currency format** — ₩ denominations on bankroll, YYYY-MM-DD (dd) local style | 2 |
| 28.5 | **Non-EN OG images** — per-locale Twitter/FB card renders | 3 |

**Done when.** A VN user never sees English text unless we explicitly lacked a translation.

---

### Block 29 — Performance + scale (~5 days) · "serve 100× current load without pager"

Right now traffic is low; one VPS suffices. This block preps the stack for a marketing push or viral moment.

| # | Ship | Hours |
|---|---|---|
| 29.1 | **Postgres read replica** — second pg container, asyncpg reader pool, routes heavy SELECTs | 6 |
| 29.2 | **Edge cache warmer** — cron GETs hot pages post-deploy so first user gets cached response | 3 |
| 29.3 | **Image CDN** — bundle team logos + player photos into a single sprite + signed Cloudflare URLs | 4 |
| 29.4 | **Query cost budget per endpoint** — SLO doc; alert when `/api/stats/*` p95 > 400ms | 3 |
| 29.5 | **Backend connection pool tuning** — asyncpg pool size based on observed concurrency | 2 |
| 29.6 | **Load test harness** — `vegeta` or `k6` hitting 50 rps sustained on `/match/:id` | 3 |

**Done when.** 50 rps sustained on `/match/:id` stays < 300ms p95.

---

### Block 30 — Legal / compliance (~4 days) · "can't dodge this if serious"

This is a serious project (user's phrase). Treat legal surface as a first-class concern, not a footnote.

| # | Ship | Hours |
|---|---|---|
| 30.1 | **Privacy policy page** — what we collect (IP, email, nothing else), retention, data subject rights | 3 |
| 30.2 | **Terms of service** — "entertainment forecasting, not financial advice", jurisdiction | 3 |
| 30.3 | **Cookie consent banner** — GDPR-style opt-in (we use no tracking beyond Plausible anyway) | 3 |
| 30.4 | **Gambling-law disclaimers** — geo-appropriate: "must be 18+", no-custody reminder, local helpline links | 3 |
| 30.5 | **Data export + delete** — user can request their data (email subs, bet log) via signed email link | 4 |

**Done when.** Site is safe to link from regulated surfaces (VN, EN, EU) without ducking legal issues.

---

### Block 31 — Observability v2 (~4 days)

Ops watchdog (Sprint 16) is user-facing. This is operator-facing. Move from "SSH the VPS to debug" to "read the dashboard".

| # | Ship | Hours |
|---|---|---|
| 31.1 | **Prometheus exporter** on the api + web containers | 4 |
| 31.2 | **Grafana self-hosted** with dashboards: request rate, DB pool, LLM cost, match ingest lag | 6 |
| 31.3 | **Sentry** integration for exceptions (or a self-hosted OSS alternative) | 3 |
| 31.4 | **Loki** for log aggregation across all compose services | 4 |
| 31.5 | **Alertmanager → Telegram** pipeline duplicating the watchdog but for infra-level signals | 3 |

**Done when.** I can answer "what's the DB p95 right now?" without SSH-ing.

---

### Block 32 — Research / experimentation (~5 days)

Right now ensemble tuning is ad-hoc (`grid_search.py`, `compare_configs.py`). Make it a discipline.

| # | Ship | Hours |
|---|---|---|
| 32.1 | **Config sweeps** — YAML-driven walk-forward sweep over ρ, α (elo weight), XGB depth etc. | 6 |
| 32.2 | **Model registry** — `model_versions` table stores every trained booster with meta (date, holdout score, feature set) | 3 |
| 32.3 | **A/B model serving** — route N% of predictions through challenger, log both; compare log-loss fair | 5 |
| 32.4 | **Feature-importance diff** — track how feature_gain changes across retrains | 3 |
| 32.5 | **Leakage detector** — automated check that no feature uses info from the current or future match | 3 |

**Done when.** Every retrain answers "is this better than what's in prod?" automatically.

---

### Block 33 — Community + tipsters (~5 days)

`tipsters` + `tipster_picks` tables exist but nothing consumes them. Activate the community layer without custody.

| # | Ship | Hours |
|---|---|---|
| 33.1 | **Tipster signup** — non-custodial, PIN-sync pattern from Block 20; pick creates `tipster_picks` row | 4 |
| 33.2 | **Tipster leaderboard** — sort by log-loss (proper scoring) not raw win rate | 3 |
| 33.3 | **Tipster profile page** — `/tipsters/:slug` with past picks + calibration curve | 4 |
| 33.4 | **Follow / feed** — localStorage favorite tipsters surface in your dashboard | 3 |
| 33.5 | **Weekly tipster digest** — best scoring tipster of the week → Telegram channel announcement | 2 |

**Done when.** A user can pick a tipster whose picks beat model ROI and follow them alongside the model.

---

### Block 34 — Brand / marketing surface (~4 days)

Content for investors, journalists, job candidates — same repo, distinct tone.

| # | Ship | Hours |
|---|---|---|
| 34.1 | **Methodology page** — long-form write-up of Poisson + DC + Elo 0.20 + XGB 0.60 ensemble with equations | 5 |
| 34.2 | **"How this is built" page** — the stack, the cron pattern, the ops watchdog — transparency as marketing | 3 |
| 34.3 | **Press kit + logos** already listed in Block 25; align styling here | 1 |
| 34.4 | **Founder story / mission** — 1-page plain English | 2 |
| 34.5 | **Investor one-pager** — if/when relevant | 3 |

**Done when.** A cold reader can assess in 5 minutes whether to trust the forecasts and engage with the team.

---

## 35. Full block sequencing cheat sheet

```
Distribution + engagement (user-facing)
Block 17  Distribution         5d   ← Telegram + Discord + email + embed          ✅ DONE
Block 18  Viral / engagement   6d   ← Title race + top-scorer race + SEO          ◐ 3/7
Block 19  Sharp credibility    5d   ← Calibration + line movement + equity
Block 20  Personal layer       5d   ← My picks + watchlist + PWA push

Depth (quality-first)
Block 21  Model depth v2       6d   ← Home/away split + derbies + manager
Block 22  Sharp tooling v2     5d   ← Arb + middles + Kelly explorer
Block 23  UX polish            4d   ← Theme + mobile nav + skeleton
Block 24  Internal tools       4d   ← Staging + rollback + flags + errors
Block 25  Content / SEO depth  5d   ← Glossary + team stories + changelog

Platform + scale (serious-project)
Block 26  Developer API        6d   ← Keys + rate limits + OpenAPI docs
Block 27  Deeper analytics     7d   ← Radar charts + manager + set-piece
Block 28  Localisation depth   5d   ← Full VI/TH/ZH/KO + VND + VN odds
Block 29  Performance + scale  5d   ← Read replica + image CDN + load test
Block 30  Legal / compliance   4d   ← Privacy + ToS + cookie + export
Block 31  Observability v2     4d   ← Prom + Grafana + Sentry + Loki
Block 32  Research / experim.  5d   ← Config sweeps + registry + A/B
Block 33  Community / tipsters 5d   ← Signup + leaderboard + follow
Block 34  Brand / marketing    4d   ← Methodology + stack + press

Total shippable work: ~90 days across 80+ independently-shippable items.
```

Run blocks sequentially or parallel depending on the sequencing rule in §22. Don't try to ship two blocks on the same day — stays shippable by keeping focus.

---

## 27. Stretch / maybe-never (~one-offs worth considering)

Listed so they don't get re-raised. Scope-creep defence.

- **Multi-league expansion** (Championship / Eredivisie / Liga Portugal) — blocked until current 5 leagues show clean positive CLV. Adds ingest + maintenance without proportional demand.
- **iOS native app** — PWA (20.5) ships 80% of the value at 10% of the cost.
- **AI live commentary** — Qwen-Plus running text during live matches. Cool, but cost unbounded and adds zero signal beyond the score/event feed we already have.
- **Voice / podcast summary** — TTS audio recap per match. Interesting; needs ElevenLabs budget.
- **Scrape pundits for model-vs-expert leaderboard** — legal grey (scraping Sky/BBC column text), small signal.
- **Paid tier / API keys** — not until there's real demand pulling us there. Current infra easily handles one VPS.

---

## 22. Sequencing rule

Blocks 17 → 18 → 19 → 20 is the default ship order, but swap if data tells you to:

1. If **/ops flags a model issue** (CLV stays negative, calibration poor), **Block 19 jumps first** — diagnose before distributing broken signal.
2. If a **Telegram channel pulls >100 subs in the first week** of 17.1, **defer 17.4+17.5** and push directly into 18 — users are already here.
3. If **SEO traffic flatlines after 18.6+18.7**, **deprioritise 17.4 email** — send the energy into 20.x personal layer for retention.

---

## 28. Out of scope (explicit)

- Live stake placement / API bridge to any book or exchange
- Handling real user money
- Tipster marketplace (tipsters table exists for log-loss scoring only, not monetisation)
- Chain-posted CLV attestations (commitment hash stays SHA-256 off-chain per Phase 4.1)
- Paid tier, subscriptions, API keys
- Neural-net anything — XGB is already at the natural ceiling for this dataset size; deep models would overfit
