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

## 21. Stretch / maybe-never (~one-offs worth considering)

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

## 23. Out of scope (explicit)

- Live stake placement / API bridge to any book or exchange
- Handling real user money
- Tipster marketplace (tipsters table exists for log-loss scoring only, not monetisation)
- Chain-posted CLV attestations (commitment hash stays SHA-256 off-chain per Phase 4.1)
- Paid tier, subscriptions, API keys
- Neural-net anything — XGB is already at the natural ceiling for this dataset size; deep models would overfit
