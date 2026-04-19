# plan-new.md — Sharp-bettor strategies

> Continuation of [`plan.md`](./plan.md). `plan.md` delivered the MVP (Phases 1–4: ingestion, model, chat, commitment hash). This file scopes **Phase 5 onward** — sharp-bettor analytics on top of the existing prediction stack. Progress tracked in [`PROGRESS.md`](./PROGRESS.md).

---

## 0. Scoping

**What this phase is.** Surface the same signals a professional bettor uses when deciding whether a price is wrong: closing-line value, best-odds shopping across books, correlated-market mispricing, fractional Kelly, per-league edge maps, and no-vig reference prices from sharp exchanges. Everything is **analytics + display only.**

**What it is not.**

- Not a sportsbook. No balance, no deposit, no withdraw.
- Not a custodial market. The Phase 4.2 "non-custodial prediction market" stays dropped per `docs/environment.md` out-of-scope rule (regulatory risk, Vietnam context).
- Not "tipster" content. We publish our own edge numbers and the methodology; users decide whether to act.

**Why now.** Walk-forward 2025-26 at 5pp edge is +2.0% flat-stake ROI on the composite ensemble (204 bets / +4.01u), and per-league simulation showed EPL alone at +5.68% ROI / 276 bets — meaningful signal buried in an aggregate that looks break-even. Existing UI surfaces a single `best_edge` chip but no CLV, no correlated pricing, no bankroll tracking. This phase closes that gap.

---

## 1. Current state (what's already built)

| Capability | Status | Evidence |
|---|---|---|
| Best-odds shopping | ✅ Shipping | `backend/app/api/stats.py` — `best_odds` CTE picks MAX(odds) per outcome across `match_odds` sources |
| Edge threshold filter | ✅ Shipping | `/api/stats/roi?threshold=0.05`, `<QuickPicks>` at 5pp cutoff |
| Fair-probs devig | ✅ Shipping | `backend/app/ingest/odds.py` — `fair_probs()` + `edge()` |
| Fractional Kelly (FE only) | ✅ Shipping | `frontend/app/parlay/page.tsx` — `kelly()` capped 0.25; `<OddsPanel>` popout when `best_edge ≥ 10pp` |
| Per-league ROI | 🧪 Exists in ad-hoc script | `/tmp/niche_league_sim.py` — not exposed in UI |
| Polymarket-style no-vig ROI | 🧪 Exists in ad-hoc script | `/tmp/polymarket_sim.py` — not exposed in UI |
| CLV logging | ❌ Not built | no closing-line capture, no beat-rate metric |
| Correlated-market pricing | ❌ Not built | no BTTS / O-U 2.5 / handicap derived from xG matrix |
| Backend Kelly endpoint | ❌ Not built | only FE calculator |
| Bankroll simulator | ❌ Not built | no virtual balance state, no stake history |
| Sharp-exchange reference | ❌ Not built | Polymarket / Betfair prices not pulled |
| In-play model | ❌ Not built | live scores only; pre-match probabilities frozen at kickoff |

---

## 2. Phase 5 — Closing-Line Value (CLV)

**Hypothesis.** Consistently beating the closing line is the single best long-term proxy for a sharp. If our model's pick at T-24h has a shorter closing price than we took, we're picking winners the market is slowly agreeing with.

**Deliverables**

- [ ] **5.1** New table `closing_odds` (`match_id`, `source`, `odds_home`, `odds_draw`, `odds_away`, `captured_at`) — separate from `match_odds` so we can keep historical snapshots cheap
- [ ] **5.2** Cron job `ingest_closing_odds.py` — runs T-5min before kickoff per match, pulls from the-odds-api (same source as `ingest_live_odds`), stores one row per source
- [ ] **5.3** CLV calculator in `backend/app/ingest/odds.py` — given our stake odds and closing odds, returns `clv_pct = (stake_odds / closing_odds) − 1` for the side we picked
- [ ] **5.4** New endpoint `GET /api/stats/clv?days=30&threshold=0.05` — for every value bet we flagged with edge ≥ threshold, return `mean_clv`, `pct_bets_beat_close`, per-league breakdown
- [ ] **5.5** `/proof` page addendum — render a CLV card next to the accuracy card. Headline: "How often did the market agree with us by kickoff?" Number: % of edge bets where our taken price > closing price
- [ ] **5.6** TDD: 6 tests — devig roundtrip, CLV sign convention, null-close fallback, per-league aggregation, stake-side projection, % beat rate

**Cost estimate.** Low. Adds ~1 the-odds-api call per match at T-5min (already under 30-call budget on the free plan). One new table, one new endpoint, one UI card.

## 3. Phase 6 — Correlated markets

**Hypothesis.** The xG scoreline matrix we already compute (0-0 through 5-5) fully specifies correlated multi-market probabilities: `BTTS`, `Over 1.5 / 2.5 / 3.5`, Asian handicap, half-time result, combined `(Over 2.5 & BTTS)`. Books sometimes price these independently, mispricing the correlation.

**Deliverables**

- [ ] **6.1** `backend/app/models/markets.py` extension — add `btts_yes()`, `over_under(line, matrix)`, `asian_handicap(line, matrix)`, `sgp(conditions, matrix)` — all pure functions over the scoreline matrix
- [ ] **6.2** Ingest `match_odds_markets` table — same shape as `match_odds` but keyed by `(match_id, source, market_code)` where market_code ∈ `1X2, BTTS, OU25, AH-0, SGP-O25-BTTS`. Populated by extending `ingest_live_odds.py`
- [ ] **6.3** Per-match correlated edge endpoint — `GET /api/matches/:id/markets-edge` returning one row per market with `model_prob`, `fair_prob`, `best_odds`, `edge_pp`
- [ ] **6.4** `<MarketsEdge>` component on `/match/[id]/` — table below 1X2 predictions showing BTTS / O-U / AH lines, neon highlight on ≥5pp edge rows
- [ ] **6.5** Backtest script `scripts/backtest_markets.py` — replay last 2 seasons against stored BTTS + O-U odds to validate. Expected: BTTS book margin lower than 1X2 (~4% vs 6%), so EV should be cleaner
- [ ] **6.6** TDD: 10 tests — matrix sums to 1, BTTS symmetry, O-U boundary (exactly line.5), AH push handling, SGP independence check, market-code canonicalization

**Cost estimate.** Medium. Requires ingest changes for O-U + BTTS odds (the-odds-api supports them on the same endpoint, one more URL query param). Two backtests before we trust it.

## 4. Phase 7 — Backend Kelly + virtual bankroll

**Hypothesis.** The existing FE Kelly is a single-match calculator. A proper bankroll tracks stakes over time, compounds correctly, and keeps a drawdown record so the user can see what their strategy actually did — not just what a single matchday looked like.

**Deliverables**

- [ ] **7.1** New table `virtual_bankroll_state` (singleton row: `starting_units`, `current_units`, `peak_units`, `max_drawdown_pct`, `last_settled_match_id`, `updated_at`)
- [ ] **7.2** New table `virtual_stake_log` (`match_id`, `side`, `stake_units`, `odds_taken`, `closing_odds`, `outcome`, `pnl_units`, `bankroll_after`, `settled_at`)
- [ ] **7.3** Settler job `scripts/settle_virtual_stakes.py` — on every finalized match, look up that match in the value-bet log, compute win/loss, update bankroll state. Idempotent via unique `(match_id, side)` in the stake log
- [ ] **7.4** Stake-sizing service `backend/app/predict/kelly.py` — `fractional_kelly(p, odds, cap=0.25)` + tests. Feeds `/api/matches/:id/markets-edge` with a `kelly_units` column
- [ ] **7.5** `/roi` page upgrade — add a "virtual bankroll" toggle: Kelly-sized stakes vs flat-1u. Chart shows both lines, drawdown shaded in `--color-error`, current DD% in a chip
- [ ] **7.6** TDD: 8 tests — Kelly formula, 0-edge = 0 stake, cap enforcement, settler idempotency, bankroll compounding, drawdown tracking

**Cost estimate.** Medium. One new service, two tables, one settler. No external data needed — uses what we already store.

## 5. Phase 8 — Per-league edge map

**Hypothesis.** Not all leagues are equal. Ad-hoc sim showed EPL at +5.68% 5pp-edge ROI (276 bets) while some leagues are deeply negative. A sharp reads the heat-map before betting; users should too.

**Deliverables**

- [ ] **8.1** Endpoint `GET /api/stats/roi/by-league?threshold=0.05&window=7d|30d|season` — per-league `bets, wins, roi_vig, roi_no_vig, mean_log_loss, clv_mean`
- [ ] **8.2** New page `/roi/by-league` — 5-column table with a neon-green bar on positive ROI rows, red on negative. Sorted by bets-per-league
- [ ] **8.3** `<QuickPicks>` filter — hide picks from leagues where 30-day rolling ROI < 0. Add a small footer chip "Showing only leagues with positive recent edge"
- [ ] **8.4** TDD: 5 tests — per-league split correctness, window boundary, zero-bet handling, sort stability, filter integration

**Cost estimate.** Low. Pure aggregation over data we already store.

## 6. Phase 9 — Sharp-exchange reference prices

**Hypothesis.** Betfair + Polymarket are low-vig / no-vig markets. Their prices are closer to true probability than any bookmaker. Logging them next to our own probability gives the user a second opinion and lets us sanity-check our model against a sharp market, not just a bookmaker.

**Deliverables**

- [ ] **9.1** Integrations:
  - Betfair Exchange: free keyed API — scrape `MATCH_ODDS` market best back/lay per outcome
  - Polymarket: public GraphQL on CLOB — only covers high-profile matches but zero-vig
- [ ] **9.2** Normalise to the existing `match_odds` shape with `source: 'betfair:back'`, `'polymarket:mid'`. Already 0% vig or near zero, so `fair_probs()` just returns the implied
- [ ] **9.3** `<OddsPanel>` extension — a row for each exchange source with `vig ≈ 0%` label. Highlight when our model disagrees ≥ 3pp with the exchange consensus (potential model bias or exchange opportunity)
- [ ] **9.4** Endpoint `GET /api/matches/:id/consensus` — weighted-mean probability across book-avg, exchange-avg, our model; spread metric flagged if disagreement > 5pp
- [ ] **9.5** TDD: 6 tests — exchange vs bookmaker devig parity, weighted consensus, spread-disagreement flag, missing-source fallback

**Cost estimate.** Medium. Two new integrations with auth. Polymarket covers maybe 10% of our fixtures — that's fine, it's a reference not a source of truth.

## 7. Phase 10 — In-play (optional, v2)

Kept on the roadmap but **not scoped now**. Requires per-second score/event feed, a real-time λ re-estimator, and WebSocket broadcast to the frontend. High infra cost (API-Football Ultra → per-minute updates → Redis pub/sub → SSE). Revisit after Phases 5–9 are live and stable.

---

## 8. Sequencing

```
Phase 5 (CLV)     ──► Phase 7 (Bankroll + Kelly)  [depends on closing odds + stake log]
Phase 6 (Markets) ──► Phase 7                    [markets expand the bet universe]
Phase 8 (By-league) — independent, cheapest, ship first-or-second as filler
Phase 9 (Exchanges) — independent, do after 5/6 so the exchange row has CLV + multi-market context
Phase 10 (In-play) — parked
```

Recommended order: **8 → 5 → 6 → 7 → 9**. 8 is tiny and gives immediate UI value. 5 unlocks CLV as the reference metric for 6/7/9. 6 enlarges the bet universe so 7 has more to do.

---

## 9. Success criteria

Before closing a phase, `PROGRESS.md` entry must include:

- Backtest numbers over the last 2 full seasons (accuracy, ROI, CLV mean, log-loss)
- One screenshot or URL pointing at the new surface
- Tests-pass count and coverage delta

If CLV mean is negative on Phase 5, stop and diagnose before Phase 6 — the model may be reading stale lines, not predicting, and the whole edifice collapses.

---

## 10. Out of scope (explicit)

- Live stake placement / API bridge to any book or exchange
- Handling real user money
- Tipster marketplace (tipsters table exists for log-loss scoring only, not monetisation)
- Chain-posted CLV attestations (commitment hash stays SHA-256 off-chain per Phase 4.1)
- Paid tier, subscriptions, API keys
