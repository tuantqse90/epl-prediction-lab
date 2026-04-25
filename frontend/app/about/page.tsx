import type { Metadata } from "next";
import Link from "next/link";

import { getLang, tFor } from "@/lib/i18n-server";
import { alternatesFor } from "@/lib/seo";

export const metadata: Metadata = {
  title: "About · predictor.nullshift.sh",
  description:
    "Predictor Labs is a small independent research group shipping an open 3-leg football forecasting model. Here's who we are, why we built this, and how we pay for it.",
  alternates: alternatesFor("/about"),
};

export default async function AboutPage() {
  const lang = await getLang();
  const t = tFor(lang);

  return (
    <main className="mx-auto max-w-3xl px-6 py-12 space-y-10">
      <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>

      <header className="space-y-3">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-neon">about</p>
        <h1 className="headline-hero">Predictor Labs</h1>
        <p className="text-secondary text-base md:text-lg">
          A small independent research group publishing an open, fully auditable
          football forecasting model for the top five European leagues.
        </p>
      </header>

      <section className="space-y-4">
        <h2 className="headline-section text-xl md:text-2xl">What we do</h2>
        <p className="text-secondary leading-relaxed">
          We maintain a 3-leg ensemble — Dixon-Coles Poisson on opponent-adjusted
          xG, goal-weighted Elo, and an XGBoost softprob classifier — that
          forecasts every fixture across the Premier League, La Liga, Serie A,
          Bundesliga, and Ligue 1. Probabilities are SHA-256 committed before
          kickoff so the record can be independently verified after full-time.
        </p>
        <p className="text-secondary leading-relaxed">
          The code is public on{" "}
          <a
            href="https://github.com/tuantqse90/epl-prediction-lab"
            className="text-neon underline underline-offset-2 hover:opacity-80"
          >
            GitHub
          </a>
          . Anyone can reproduce the walk-forward backtest locally, audit the
          hash encoding, or fork the model with different weights.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className="headline-section text-xl md:text-2xl">What we don&apos;t do</h2>
        <ul className="list-disc pl-6 space-y-2 text-secondary">
          <li>We don&apos;t sell tips.</li>
          <li>We don&apos;t take affiliate or referral commissions from any sportsbook.</li>
          <li>We don&apos;t run ads.</li>
          <li>We don&apos;t track visitors beyond first-party page analytics.</li>
          <li>We don&apos;t promise profit. If the model costs you money, that&apos;s on you.</li>
        </ul>
      </section>

      <section className="space-y-4">
        <h2 className="headline-section text-xl md:text-2xl">How this is funded</h2>
        <p className="text-secondary leading-relaxed">
          Out of pocket. The site runs on a €8/month VPS. DashScope costs for
          Qwen-Turbo reasoning run under €5/month at current volume. There is
          no commercial model, no freemium tier, no upsell. It will stay this
          way as long as we can absorb the running cost.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className="headline-section text-xl md:text-2xl">Editorial stance</h2>
        <p className="text-secondary leading-relaxed">
          We publish the numbers the model outputs, including when the model
          is wrong. The <Link href="/proof" className="text-neon underline">proof page</Link> shows the model beating bookmakers over
          recent 30-day windows but losing to them cumulatively over 3,760
          matches. Both numbers are maintained live. We&apos;ll never hide one to
          flatter the other.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className="headline-section text-xl md:text-2xl">Contact</h2>
        <p className="text-secondary leading-relaxed">
          Bugs, feature ideas, methodology questions — open an{" "}
          <a
            href="https://github.com/tuantqse90/epl-prediction-lab/issues"
            className="text-neon underline underline-offset-2 hover:opacity-80"
          >
            issue
          </a>
          {" "}or start a{" "}
          <a
            href="https://github.com/tuantqse90/epl-prediction-lab/discussions"
            className="text-neon underline underline-offset-2 hover:opacity-80"
          >
            discussion
          </a>
          . Telegram channel for weekly picks is{" "}
          <a
            href="https://t.me/worldcup_predictor"
            className="text-neon underline underline-offset-2 hover:opacity-80"
          >
            @worldcup_predictor
          </a>
          .
        </p>
      </section>

      <section className="space-y-4 card">
        <h2 className="font-display text-lg font-semibold uppercase tracking-tight text-primary">
          Responsible gambling
        </h2>
        <p className="text-sm text-secondary leading-relaxed">
          The Kelly stake suggestions on this site are statistical guidance,
          not betting advice. Fractional Kelly is capped at 25% of bankroll for
          a reason — even a well-calibrated model has losing streaks. If you or
          someone you know has a gambling problem, stop and reach out to a
          helpline. UK: GamCare (0808 8020 133). US: 1-800-GAMBLER.
        </p>
      </section>
    </main>
  );
}
