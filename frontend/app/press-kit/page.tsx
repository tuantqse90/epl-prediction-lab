import Link from "next/link";

import { getLang } from "@/lib/i18n-server";
import { tLang } from "@/lib/i18n-fallback";

export const metadata = {
  title: "Press kit · predictor.nullshift.sh",
  description: "Logos, screenshots, one-liner, and contact for media mentions.",
};

export default async function PressKitPage() {
  const lang = await getLang();
  return (
    <main className="mx-auto max-w-3xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
      </Link>
      <header>
        <p className="font-mono text-xs text-muted">docs · press kit</p>
        <h1 className="headline-section">Press kit</h1>
      </header>

      <section className="card space-y-3">
        <h2 className="label">One-liner</h2>
        <p className="text-secondary">
          Prediction Lab is an xG-driven football forecasting site covering the five biggest European leagues.
          Every match gets a Poisson + Elo + XGBoost ensemble prediction, value-bet edges vs the betting
          market, and plain-language LLM reasoning — no custody, no wallet, entertainment-grade only.
        </p>
      </section>

      <section className="card space-y-3">
        <h2 className="label">Key facts</h2>
        <ul className="space-y-1 text-sm text-secondary">
          <li>• 5 leagues: EPL, La Liga, Serie A, Bundesliga, Ligue 1</li>
          <li>• 7 seasons of historical matches · 12k+ graded predictions</li>
          <li>• 5-language UI (EN / VI / TH / ZH / KO)</li>
          <li>• 100% transparent: <Link href="/calibration" className="hover:text-neon">calibration</Link>, <Link href="/equity-curve" className="hover:text-neon">equity curve</Link>, and <Link href="/benchmark/by-team" className="hover:text-neon">per-team accuracy</Link> all public</li>
          <li>• Non-custodial: no stake placement, no wallet, no deposit</li>
        </ul>
      </section>

      <section className="card space-y-3">
        <h2 className="label">Embed</h2>
        <p className="text-sm text-secondary">
          Partners can show a prediction card on their site with a single snippet — see{" "}
          <Link href="/embed-docs" className="hover:text-neon">/embed-docs</Link>. Free. Credit appreciated.
        </p>
      </section>

      <section className="card space-y-3">
        <h2 className="label">Logo</h2>
        <p className="text-sm text-secondary">
          Wordmark = "Prediction Lab". Accent colour = <span className="inline-block h-3 w-3 rounded-full align-middle" style={{ background: "#E0FF32" }} /> <code className="font-mono text-xs">#E0FF32</code>.
          Type: Geist / Inter system stack. Use dark backgrounds.
        </p>
        <p className="text-sm text-secondary">
          <a href="/icon" className="hover:text-neon">/icon</a> serves a 512×512 PWA icon ·
          <a href="/apple-icon" className="hover:text-neon ml-1">/apple-icon</a> serves the 180×180 touch icon.
        </p>
      </section>

      <section className="card space-y-3">
        <h2 className="label">Contact</h2>
        <p className="text-sm text-secondary">
          Repo: <a href="https://github.com/tuantqse90/epl-prediction-lab" className="hover:text-neon" target="_blank" rel="noopener">github.com/tuantqse90/epl-prediction-lab</a>
        </p>
      </section>
    </main>
  );
}
