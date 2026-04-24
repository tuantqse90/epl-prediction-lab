import Link from "next/link";

import { getLang } from "@/lib/i18n-server";
import { tLang } from "@/lib/i18n-fallback";

export const metadata = {
  title: "Terms of service · predictor.nullshift.sh",
  description: "Entertainment-grade forecasting. Not financial advice.",
};

export default async function TermsPage() {
  const lang = await getLang();
  return (
    <main className="mx-auto max-w-3xl px-6 py-12 space-y-6 blog-prose">
      <Link href="/" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
      </Link>
      <header>
        <p className="font-mono text-xs text-muted">docs · terms</p>
        <h1 className="headline-section">Terms of service</h1>
        <p className="text-muted text-sm">Last updated: 2026-04-24</p>
      </header>

      <section className="space-y-3">
        <h2>Forecasting, not advice</h2>
        <p>
          Prediction Lab is entertainment-grade football forecasting. Numbers published here
          are model output. Nothing on this site is financial, gambling, investment, or legal advice.
        </p>
        <p>
          You are solely responsible for any bets you place. Outcomes are probabilistic. Variance
          is real. Past performance does not predict future returns.
        </p>
      </section>

      <section className="space-y-3">
        <h2>Gambling-law note</h2>
        <p>
          You must be <b>18+</b> to follow sharp-betting analytics in most jurisdictions. Where
          gambling is regulated or prohibited (incl. Vietnam for most forms), follow your local law.
          We do not facilitate bets or process stakes. Problem gambling help lines:
        </p>
        <ul>
          <li>UK: <a className="hover:text-neon" href="https://www.begambleaware.org/" target="_blank" rel="noopener">BeGambleAware</a></li>
          <li>Australia: Gambling Help Online</li>
          <li>International: <a className="hover:text-neon" href="https://www.gamblersanonymous.org/" target="_blank" rel="noopener">Gamblers Anonymous</a></li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2>Service availability</h2>
        <p>
          Best-effort uptime. We do not guarantee continuity. We may change, pause, or discontinue
          any feature at any time.
        </p>
      </section>

      <section className="space-y-3">
        <h2>Trademarks</h2>
        <p>
          Club names, logos, and league marks are the property of their respective holders. Use
          on this site is descriptive only, under fair use for news/commentary purposes.
        </p>
      </section>
    </main>
  );
}
