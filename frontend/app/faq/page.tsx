import type { Metadata } from "next";
import Link from "next/link";

import { getLang, tFor } from "@/lib/i18n-server";
import { alternatesFor } from "@/lib/seo";

export const metadata: Metadata = {
  title: "FAQ · predictor.nullshift.sh",
  description:
    "Answers to the most-asked questions about the model, the commitment hash, the backtest methodology, and why we publish losing numbers alongside winning ones.",
  alternates: alternatesFor("/faq"),
};

type QA = { q: string; a: React.ReactNode };

const QUESTIONS: QA[] = [
  {
    q: "How is this different from other football prediction sites?",
    a: (
      <>
        Two specific differences. (1) Every probability is SHA-256 committed
        from the canonical JSON body before kickoff, so probabilities can&apos;t
        be silently edited after the fact — the hash would no longer match.
        (2) We publish negative evidence on the same page as positive evidence.
        The <Link href="/proof" className="text-neon underline">/proof</Link> page shows the model beats bookmakers by +2.1pp over
        the last 30 days and loses to them by −2.0pp across 3,760 finals since
        2019. Most prediction sites hide the second number.
      </>
    ),
  },
  {
    q: "Can I actually bet with this?",
    a: (
      <>
        Kelly stake is shown for any outcome with ≥5pp edge over fair market
        price, fractional Kelly capped at 25% of bankroll. That&apos;s a peer-
        reviewable number, not advice. Even a well-calibrated model has losing
        streaks. If you choose to bet, size down. If you&apos;re new, don&apos;t.
      </>
    ),
  },
  {
    q: "Is the backtest honest?",
    a: (
      <>
        Walk-forward: every feature (xG strengths, Elo ratings, XGBoost
        features) is computed from matches with a kickoff strictly before the
        target match. The scripts are in{" "}
        <a
          href="https://github.com/tuantqse90/epl-prediction-lab/tree/main/backend/scripts"
          className="text-neon underline underline-offset-2 hover:opacity-80"
        >
          backend/scripts
        </a>
        {" "}— `compare_configs.py`, `tune_ensemble.py`, `backtest.py`. Run them
        with `docker compose up` and you&apos;ll get the same numbers we report.
      </>
    ),
  },
  {
    q: "Why commit a hash if nothing is on-chain?",
    a: (
      <>
        The commitment mechanism is chain-agnostic. SHA-256 proves the body
        hasn&apos;t changed since the hash was computed; you don&apos;t need
        blockchain for that, you just need a timestamp. The DB row&apos;s
        `created_at` plus the stored hash plus the publicly-documented
        canonical encoding give a third party everything needed to verify
        "these probabilities are exactly what the server had at time T". We
        could publish each hash to a chain for extra proof-of-existence, but
        we&apos;d rather not add gas costs for a feature 99% of users don&apos;t need.
      </>
    ),
  },
  {
    q: "Why XGBoost weight = 0.60? Isn't that trusting one model too much?",
    a: (
      <>
        The walk-forward grid sweep
        (<Link href="/blog/xgb-weight-jump" className="text-neon underline">writeup</Link>)
        sampled 1,816 out-of-sample matches. Weights elo=0.20, xgb=0.60 gave
        log-loss 0.9278 and accuracy 56.2%, meaningfully better than any
        lower-xgb config at p&lt;0.05. The booster was trained on all seasons
        prior to the evaluation window, with features that don&apos;t include
        anything unavailable before kickoff. Every week the booster retrains
        from scratch on the newest data.
      </>
    ),
  },
  {
    q: "Why losing to bookmakers cumulatively? What&apos;s missing?",
    a: (
      <>
        We break this down in{" "}
        <Link href="/blog/all-time-gap" className="text-neon underline">this post</Link>.
        Short version: bookmakers aggregate late team news, sharp-money pressure,
        referee tendencies, and other non-xG signals the model doesn&apos;t see.
        Our features are public xG + Elo + rest days + derby flag + XGBoost on 21
        dimensions. Closing a 2pp gap against professional market-makers aggregating
        private information is hard, and in the honest case impossible from
        purely public inputs. Most of the gap probably closes with injury-position
        weighting and referee stats; the rest is structural.
      </>
    ),
  },
  {
    q: "Can I use this for American football / NBA / cricket / etc?",
    a: (
      <>
        Not out of the box. The math engine is general (Poisson process + 1X2
        3-way output), but the ingest pipeline is soccer-specific and the
        features are xG-based. You could fork the repo and swap the ingest +
        features for your sport — the scaffolding around commitment, calibration,
        and blend tuning would carry over. The five seeded leagues are the ones
        with clean Understat coverage.
      </>
    ),
  },
  {
    q: "Why not sell tips or charge?",
    a: (
      <>
        We want the methodology to be adversarially verifiable, which means the
        code, the backtest, the weights, and the encoding spec all have to be
        public. Paywalling any of that would undermine the core claim. It also
        keeps our incentives clean — we win only if the model is genuinely
        better, not if we write better marketing copy.
      </>
    ),
  },
  {
    q: "How often does the model update?",
    a: (
      <>
        Predictions refresh daily at 06:00 UTC for the next 14 days of fixtures,
        plus a full retrain of XGBoost every Monday 02:00 UTC. During live
        matches, a 10-second systemd timer re-pulls scores and updates
        remaining-time probabilities from the current score + remaining Poisson
        mass. Every re-prediction gets its own DB row and hash.
      </>
    ),
  },
  {
    q: "Who runs this?",
    a: (
      <>
        A small independent research group. See{" "}
        <Link href="/about" className="text-neon underline">/about</Link>. No
        commercial backers. Funded out-of-pocket at €13/month running cost.
      </>
    ),
  },
];

// Parallel plain-text answers for FAQPage JSON-LD — Google's rich
// results require strings, not JSX. Keep questions in lockstep with the
// QUESTIONS array above; if you add a Q&A there, add the prose answer here.
const LD_ANSWERS: string[] = [
  "Two specific differences. (1) Every probability is SHA-256 committed from the canonical JSON body before kickoff, so probabilities can't be silently edited after the fact — the hash would no longer match. (2) We publish negative evidence on the same page as positive evidence. The /proof page shows the model beats bookmakers by +2.1pp over the last 30 days and loses to them by −2.0pp across 3,760 finals since 2019. Most prediction sites hide the second number.",
  "Kelly stake is shown for any outcome with ≥5pp edge over fair market price, fractional Kelly capped at 25% of bankroll. That's a peer-reviewable number, not advice. Even a well-calibrated model has losing streaks. If you choose to bet, size down. If you're new, don't.",
  "Walk-forward: every feature is computed from matches with a kickoff strictly before the target match. Scripts are open-source on GitHub. We retrain XGBoost weekly on all prior seasons holding out the current one for honest out-of-sample metrics.",
  "Each prediction's canonical JSON body (probabilities, top scoreline, expected goals) is hashed with SHA-256 before kickoff. If we ever change the numbers post-fact, the hash on the original commitment row would no longer match — and we expose every commitment hash on /match/:id.",
  "Free forever. Pro tier ($9/mo, optional) unlocks 10× higher API rate limits + early access to new features. The model itself is the same on both tiers.",
  "5 European top leagues — EPL, La Liga, Serie A, Bundesliga, Ligue 1 — plus UEFA Champions League and Europa League. ~2,000 matches per season covered with full pre-match xG ensemble.",
  "API-Football Ultra (75k requests/day) for 1X2 + over/under + BTTS + Asian handicap odds across 60+ bookmakers. The-odds-api as fallback. Closing odds snapshotted 5 minutes before kickoff for CLV measurement.",
  "Goals + cards + substitutions + VAR events come from API-Football's /fixtures/events endpoint, polled every 10 seconds during live matches. Live model probabilities recompute from remaining-time Poisson mass on the same cadence.",
  "Predictions refresh daily at 06:00 UTC for the next 14 days of fixtures, plus a full retrain of XGBoost every Monday 02:00 UTC. During live matches, a 10-second systemd timer re-pulls scores and updates remaining-time probabilities from the current score + remaining Poisson mass.",
  "A small independent research group. See /about. No commercial backers. Funded out-of-pocket at ~$13/month running cost.",
];

function faqPageLd() {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: QUESTIONS.map((qa, i) => ({
      "@type": "Question",
      name: qa.q,
      acceptedAnswer: {
        "@type": "Answer",
        text: LD_ANSWERS[i] ?? "",
      },
    })),
  };
}

export default async function FAQPage() {
  const lang = await getLang();
  const t = tFor(lang);

  return (
    <main className="mx-auto max-w-3xl px-6 py-12 space-y-10">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqPageLd()) }}
      />
      <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>

      <header className="space-y-3">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-neon">faq</p>
        <h1 className="headline-hero">Frequently asked</h1>
        <p className="text-secondary text-base md:text-lg">
          Answers to the 10 questions we get most often. If yours isn&apos;t
          here, open a{" "}
          <a
            href="https://github.com/tuantqse90/epl-prediction-lab/discussions"
            className="text-neon underline underline-offset-2 hover:opacity-80"
          >
            GitHub Discussion
          </a>
          .
        </p>
      </header>

      <section className="space-y-6">
        {QUESTIONS.map((qa, i) => (
          <details
            key={i}
            className="card group"
            open={i < 2}
          >
            <summary className="cursor-pointer list-none flex items-baseline justify-between gap-3">
              <h2 className="font-display text-lg md:text-xl font-semibold text-primary leading-tight">
                {qa.q}
              </h2>
              <span className="font-mono text-neon text-xl group-open:rotate-45 transition-transform shrink-0">+</span>
            </summary>
            <div className="mt-4 text-secondary leading-relaxed">{qa.a}</div>
          </details>
        ))}
      </section>
    </main>
  );
}
