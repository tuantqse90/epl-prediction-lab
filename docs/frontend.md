# Frontend UX — Payy-inspired design system

> **Design reference**: [payy.network](https://payy.network/) — pure-black surface, neon-lime accent, uppercase display type, black-on-neon CTAs. Tokens below are the canonical Payy palette (also used in `TascoDrive/DesignSystem/Colors.swift`). **Treat this as the visual contract for the entire app.**

---

## 1. Design principles (Payy house style)

1. **Pure black, not dark-gray.** Surface is `#000000`. Elevation is done with `#161616` → `#242424` → `#363636`, not with lightening the base.
2. **Neon lime is the hero, used sparingly.** One neon element per viewport — hero CTA, a key number, a single highlight. Overuse kills the signal.
3. **Black text on neon, always.** Any `#E0FF32` surface carries black (`#000`) text. White-on-neon reads tacky and low-contrast. No exceptions.
4. **Type does the work, illustrations don't.** Uppercase display headlines, tight tracking, mono for numbers. No stock illustration, no gradient blobs.
5. **Generous whitespace, short copy.** Declarative one-liners. "Every stablecoin transaction is a permanent data leak." style.
6. **Terminal motifs, light touch.** Loading bars (`█░░░`), status syntax (`> status`, `[PRIVATE]`), mono stat blocks. Not a full ASCII gimmick.

---

## 2. Color tokens (canonical)

```css
/* Surfaces — pure black base, charcoal elevation */
--bg-surface:         #000000;   /* page background */
--bg-raised:          #161616;   /* cards, sections */
--bg-high:            #242424;   /* elevated card, hovered row */
--bg-max:             #363636;   /* tooltip, modal */

/* Accent — Payy electric lime */
--accent-neon:        #E0FF32;   /* primary CTA, hero number, key highlight */
--accent-neon-dim:    #B8CC28;   /* pressed/hover dim, gradient stop */
--on-neon:            #000000;   /* text/icon on any neon surface — black, never white */

/* Charcoal accent (secondary fill) */
--charcoal:           #161616;

/* Text */
--text-primary:       #FFFFFF;   /* headings, body on dark */
--text-secondary:     #D9D9D9;   /* supporting text */
--text-muted:         #778899;   /* labels, captions (payy's #789) */

/* Semantic */
--color-success:      #E0FF32;   /* success = neon, not traditional green */
--color-warning:      #FFB020;
--color-error:        #FF4D4F;
--color-danger:       #E8212D;   /* critical-only */

/* Dividers */
--border:             #242424;
--border-muted:       #161616;
```

### Prediction-bar role mapping

Probability bars and stat deltas map onto the palette deliberately — keep neon for the *most likely* outcome only, so the eye lands on one thing per card:

| Role | Token |
|---|---|
| Highest probability (home/draw/away winner of the row) | `--accent-neon` with `--on-neon` text |
| Other probabilities | `--text-secondary` on `--bg-high` |
| Positive delta (xG over) | `--accent-neon` |
| Negative delta (xG under) | `--color-error` |
| Draw / neutral | `--text-muted` |

---

## 3. Typography

```css
--font-display: 'Geist', 'Inter', system-ui, sans-serif;   /* uppercase hero type */
--font-body:    'Geist', 'Inter', system-ui, sans-serif;   /* body */
--font-mono:    'JetBrains Mono', ui-monospace, monospace; /* numbers, scores, xG, status */

/* Display headline — Payy signature */
.headline-hero {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: clamp(3rem, 8vw, 7rem);
  line-height: 0.95;
  letter-spacing: -0.02em;
  text-transform: uppercase;
}

/* Section title */
.headline-section {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: clamp(1.75rem, 3vw, 2.5rem);
  letter-spacing: -0.01em;
  text-transform: uppercase;
}

/* Body */
.body {
  font-family: var(--font-body);
  font-weight: 400;
  font-size: 1rem;
  line-height: 1.55;
  color: var(--text-secondary);
}

/* Label / caption — uppercase tracked */
.label {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
}

/* Stat — big number in mono */
.stat {
  font-family: var(--font-mono);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  font-size: clamp(1.5rem, 3vw, 2.25rem);
  color: var(--text-primary);
}
```

**Rules of thumb**

- Headlines → uppercase, tight tracking, display font.
- Numbers (scores, probabilities, xG, minute marks) → **always** mono, tabular nums.
- Body → sentence case, `--text-secondary`.
- Labels → uppercase mono, `--text-muted`, `tracking-wider`.

---

## 4. Buttons / CTA

### Primary (hero) — neon fill, **black text**

```css
.btn-primary {
  background: var(--accent-neon);
  color: var(--on-neon);              /* #000 — never white */
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 0.875rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 0.875rem 1.5rem;
  border-radius: 9999px;              /* pill */
  border: 0;
  transition: background 120ms ease;
}
.btn-primary:hover  { background: var(--accent-neon-dim); }
.btn-primary:active { transform: translateY(1px); }
```

### Secondary — charcoal fill, white text

```css
.btn-secondary {
  background: var(--bg-high);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 9999px;
  padding: 0.875rem 1.5rem;
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.btn-secondary:hover { background: var(--bg-max); }
```

### Ghost / link — no fill, muted → neon on hover

```css
.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  padding: 0.5rem 0.75rem;
}
.btn-ghost:hover { color: var(--accent-neon); }
```

**Corner radius**: pill (`9999px`) for CTAs; `12px` for cards; `6px` for inputs and chips.

---

## 5. Visual motifs

- **Neon glow behind key numbers.** Soft radial (`radial-gradient(closest-side, rgba(224,255,50,0.35), transparent)`) under the big P(home win) or the top scoreline. Single glow per card.
- **Progress / probability bars.** Filled track = `--accent-neon`, rail = `--bg-raised`, 4–6px tall, full-width. For 3-way (H/D/A), stack horizontally with neon on the winner only.
- **Status syntax.** Small labels in the style `> matchweek 34`, `[FINAL]`, `[LIVE]`, `[SCHEDULED]` — mono, muted, uppercase.
- **Terminal loading.** For async states: `█░░░░░ loading xG…` (mono, text-secondary, no spinner).
- **Borders are hairlines.** `1px solid var(--border)` on cards; never shadows. Payy is flat.
- **No illustrations.** If something needs a visual, use a stat, a chart, or a typographic treatment.

---

## 6. Routes

The app is multi-league (EPL / La Liga / Bundesliga / Serie A / Ligue 1) with a cookie-driven locale (en / vi / th / zh / ko). Every page respects both.

### Core

- `/` — **Dashboard.** Hero line (`> football-predict :: matchweek {n}`), `<ProofStrip>` (Model / Bookmakers / Always-Home / Random accuracy bars on last 30d), `<QuickPicks>` (top 3 upcoming where `best_edge ≥ 5pp`), match grid (3–4 cols desktop / 1 col mobile). Each `<MatchCard>` has a model-pick banner, `+X% vs market` chip, neon-on-winner 3-way bar, top scoreline + confidence, and a ghost `VIEW MATCH →`.
- `/match/[id]` — **Match detail.** 4-tab layout (Preview / Markets / Analysis / Community) via `<MatchTabs>`. Prediction block is the single neon moment (big favoured % with radial glow, top scoreline mono-huge, 16–84% CI band). Reasoning block as terminal panel. `<OddsPanel>` with Kelly popout at `best_edge ≥ 10pp`. `<ScoreMatrix>` 6×6 heatmap. Lineups, injuries, weather, H2H, scorers. Bottom-docked `<ChatWidget>` with suggested prompts per locale.
- `/leagues` and `/leagues/[slug]` — per-league hub + standings.

### Stats + betting signal

- `/proof` — **Trust / methodology.** Weighted accuracy + log-loss chips, 30d head-to-head bar chart, per-season accuracy, calibration reliability table, 4-step hash-verification how-to.
- `/roi` — flat-stake PnL line chart; edge-threshold selector (3/5/7/10pp); cumulative P&L on model picks with drawdown shaded.
- `/last-weekend` — 7-day hit/miss window, summary strip + card grid with model pick vs final score.
- `/benchmark` — model vs baselines (bookmakers, always-home, random) side by side.
- `/stats` — generic stats dashboard (log-loss, accuracy, weighted vs raw).
- `/history` — per-season accuracy bars.
- `/table` — xG-adjusted standings, real vs xG, sortable, overperformers neon / underperformers red.
- `/scorers` — top 25 by season; sortable across G / xG / npxG / Δ / A / xA / KP / GP.

### Teams + players

- `/teams/[slug]` — radial-gradient crest hero, 4 stat tiles, Attack/Defense gauges vs league, next-fixture + last-result spotlight, top-scorer card with neon goal count, recent + upcoming fixtures.
- `/players` and `/players/[slug]` — searchable leaderboard + individual history.
- `/compare` — player/team head-to-head.

### Betting tools (analytics only — never takes real stakes)

- `/parlay` — parlay builder with fractional-Kelly calculator capped at 0.25.
- `/betslip` — localStorage-backed slip scratchpad.
- `/tipsters` — community leaderboard (handle → picks → log-loss).
- `/fpl` — Fantasy Premier League selector.

### Meta

- `/news` — team-filtered news feed.
- `/admin` — quota + ingest freshness + per-league counts.
- `/faq`, `/about`, `/docs`, `/blog`.

See [`plan-new.md`](../plan-new.md) for upcoming surfaces — `/roi/by-league` (Phase 8), `<MarketsEdge>` on match page (Phase 6), virtual bankroll view on `/roi` (Phase 7), exchange-consensus row in `<OddsPanel>` (Phase 9).

---

## 7. Implementation notes (Next.js 15 + Tailwind)

- Register tokens in `tailwind.config.ts` under `theme.extend.colors` with the names above (`surface`, `raised`, `neon`, `on-neon`, etc.) so classes read like `bg-surface`, `text-neon`, `bg-neon text-on-neon`.
- `fontFamily` block: `display`, `body`, `mono` (all hardcoded to the stacks in §3).
- Add a Tailwind plugin or `@layer components` for `.btn-primary` / `.btn-secondary` / `.label` / `.stat` — don't scatter the rules across components.
- Dark mode is the *only* mode. Do not add a light variant.
- Shadcn / Radix primitives OK for behavior (dialog, tabs, select), but restyle every one — default shadcn theming breaks the palette.

---

## 8. What to avoid

- White text on neon (tacky, low-contrast — see memory `feedback_tascodrive_neon_cta`).
- Multiple neon elements per viewport (kills hierarchy).
- Rounded-xl cards with drop shadows (not Payy — flat + hairline border).
- Gradients beyond the one-stop neon highlight in §4 and the radial glow in §5.
- Emoji, stock icons, illustrations of footballs. Type and data only.
- Light-gray backgrounds to imply "neutral" — stay pure black.
