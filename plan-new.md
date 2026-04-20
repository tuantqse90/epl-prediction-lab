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

## 9. Phase 11 — Rest, fatigue, fixture-congestion features

**Hypothesis.** Pros model fatigue explicitly. A team playing their 3rd match in 7 days, especially with European midweek travel, scores materially less than the same team on 4+ days rest. XGBoost can learn this if the features are present.

**Deliverables**

- [ ] **11.1** Feature engineering in `app/models/features.py` — add `compute_fixture_context(team_id, kickoff, df)` returning:
  - `rest_days_home`, `rest_days_away` (days since previous match)
  - `europe_midweek_flag` (did the team play a Champions/Europa fixture in the 4 days before this one?)
  - `congestion_score` (number of matches in the prior 14 days)
  - `away_travel_km` — optional (need team home city coords; park if too much effort)
- [ ] **11.2** Retrain XGBoost with the extended 24-feature set. `scripts/train_xgboost.py` already exists — extend.
- [ ] **11.3** Walk-forward backtest vs current 21-feature model on 2024-25 + 2025-26 EPL. Accept only if log-loss improves by ≥ 0.5% AND accuracy doesn't regress.
- [ ] **11.4** `PROGRESS.md` entry with before/after numbers + config snapshot.
- [ ] **11.5** 4 TDD tests for the feature computer — single match prior context, first-of-season edge case, midweek Euro flag detection, congestion score window boundary.

**Cost estimate.** Low. All inputs already in the DB. Retrain is seconds on our small dataset.

## 10. Phase 12 — Referee adjustment

**Hypothesis.** Referees have durable tendencies — some hand out more cards, some let more goals happen, some are fussier about penalties. `matches.referee` is already populated but the model doesn't read it.

**Deliverables**

- [ ] **12.1** Per-referee baseline calculator `app/models/referee.py` — rolling 2-season window per referee returning `goals_per_match_delta` (above/below league average) + `cards_per_match_delta`.
- [ ] **12.2** λ adjustment in `predict/service.py`: `goals_per_match_delta` feeds a multiplicative shrink on both team λ (symmetric — refs affect both sides). Cap ±10% so no single outlier ref nukes predictions.
- [ ] **12.3** Markets endpoint exposes the ref multiplier in the response so UI can show it.
- [ ] **12.4** On `/match/:id` — mention the referee + their tendency in a small chip: "Michael Oliver · 0.8 goals above league avg". Pure text, no new component.
- [ ] **12.5** Backtest: walk-forward on 2024-25. Accept only if 1X2 log-loss + O/U 2.5 log-loss both improve.
- [ ] **12.6** 5 TDD tests — referee with ≥ 30 match sample, sparse referee fallback, cap enforcement, symmetric application, no-referee-data graceful skip.

**Cost estimate.** Low. Data already stored, single-file change.

## 11. Phase 13 — Lineup-sum power rating

**Hypothesis.** Team attack/defense rating from opponent-adjusted rolling xG is coarse — it treats every player identically. Sharps reconstruct team strength at kickoff from the actual starting XI's individual xG contributions per 90. When the line-up is known (T-1h pre-KO), this dominates the team-level rating.

**Deliverables**

- [ ] **13.1** `app/models/lineup_strength.py` — given a starting XI + subs list from `match_lineups`, compute `lineup_xg_per_90 = sum(player xG per 90 × expected minutes)`. Expected minutes: 90 for starters, 15-30 for expected bench subs based on player position.
- [ ] **13.2** Blend the lineup rating with the team-level rating in `match_lambdas`: at T-1h when lineup is confirmed, weight lineup at 0.5; at T-24h when only team rating is available, weight lineup at 0.0.
- [ ] **13.3** Rerun prediction T-1h with lineup-informed λ. Over-write the pre-existing `predictions` row since we've gained info.
- [ ] **13.4** `/match/:id` surfaces both the T-24h and T-1h prediction side by side with a "lineup-adjusted" label when the 2nd is available.
- [ ] **13.5** Backtest on 2024-25 + 2025-26 where we have lineup history. Success criterion: **log-loss improves ≥ 1% over base ensemble**.
- [ ] **13.6** 6 TDD tests — full-strength XI vs weakened XI, sub-minutes weighting, positional weighting (forwards count more than centre-backs for xG sum), missing lineup fallback, weight-blending boundary, overwrite-existing-prediction idempotency.

**Cost estimate.** Medium. Requires thoughtful lineup → xG mapping (forwards contribute differently than defenders) and a second prediction-writer pass near kickoff. This is the highest-leverage single model improvement available.

## 12. Phase 14 — Market-line as XGB feature (experimental)

**Hypothesis.** The closing line encodes information from sharp bettors. Adding it as a feature can boost accuracy 1–2%. Caveat: feels circular (we're using market to predict market). Only attempt after Phases 11–13 have locked in the non-circular improvements so we know the baseline.

**Deliverables**

- [ ] **14.1** Add `market_home_fair_prob`, `market_draw_fair_prob`, `market_away_fair_prob` (devigged from earliest-available match_odds row) as 3 new features.
- [ ] **14.2** Retrain XGBoost with the 27-feature set (21 base + 3 fatigue from P11 + 3 market features).
- [ ] **14.3** Walk-forward backtest. Success criterion: **log-loss improves ≥ 0.5% vs post-P11+P12 baseline**. Abort if the model just reproduces the market (accuracy up but edge-betting ROI goes to zero — it's not independent signal anymore).
- [ ] **14.4** Manually inspect top XGBoost feature importances: if market-line features absorb all the signal and the xG / Elo / form features go to zero importance, we've over-fit to the market. Roll back.
- [ ] **14.5** 3 TDD tests — feature presence, missing-odds fallback to NaN, devig monotonicity.

**Cost estimate.** Low compute-wise, medium risk. The "don't just reproduce the market" check is the hardest part.

---

## 13. Sequencing

```
Analytics (done)      Phases 5, 6, 6b, 7, 8, 9-sharp       ✅
Analytics (parked)    Phase 10 in-play                     ⏸

Model quality (next)  Phase 12 referee        ──► Phase 14 market-line
                      Phase 11 fatigue        ──► Phase 14 market-line
                      Phase 13 lineup-sum     — independent, highest impact
```

**Recommended next order: 12 → 11 → 13 → 14.** 12 is tiny (data already there, single-file change), 11 shares the XGB retrain infra, 13 is the big win (requires lineup coverage), 14 only if the other three haven't already maxed out the edge.

---

## 14. Success criteria

Before closing a phase, `PROGRESS.md` entry must include:

- **Analytics phases**: backtest numbers over the last 2 full seasons (accuracy, ROI, CLV mean, log-loss). Live screenshot of the new surface. Tests-pass count + delta.
- **Model-quality phases**: walk-forward log-loss + accuracy before/after on out-of-sample seasons. Feature-importance diff (catch accidental reliance on a single feature). Live sample of the updated prediction on one match.

If CLV mean is still negative after Phase 5 data accumulates: stop model-quality work, diagnose the model. Adding features to a model whose closing line consistently beats us is polishing a losing strategy.

---

## 15. Out of scope (explicit)

- Live stake placement / API bridge to any book or exchange
- Handling real user money
- Tipster marketplace (tipsters table exists for log-loss scoring only, not monetisation)
- Chain-posted CLV attestations (commitment hash stays SHA-256 off-chain per Phase 4.1)
- Paid tier, subscriptions, API keys
- Neural-net anything — XGB is already at the natural ceiling for this dataset size; deep models would overfit
