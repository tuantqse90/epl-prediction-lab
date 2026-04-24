import Link from "next/link";

import { getLang } from "@/lib/i18n-server";
import { tLang } from "@/lib/i18n-fallback";

export const metadata = {
  title: "How the model works — methodology · predictor.nullshift.sh",
  description: "Full transparency on the ensemble: Poisson + Dixon-Coles + Elo (0.20) + XGBoost (0.60).",
};

export default async function MethodologyPage() {
  const lang = await getLang();
  return (
    <main className="mx-auto max-w-3xl px-6 py-12 space-y-8 blog-prose">
      <Link href="/" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
      </Link>
      <header>
        <p className="font-mono text-xs text-muted">docs · methodology</p>
        <h1 className="headline-section">
          {tLang(lang, {
            en: "How the model works",
            vi: "Mô hình hoạt động ra sao",
            th: "โมเดลทำงานอย่างไร",
            zh: "模型如何运作",
            ko: "모델 작동 방식",
          })}
        </h1>
      </header>

      <section className="space-y-4">
        <h2>Three-leg ensemble</h2>
        <p>
          Every match prediction is a weighted blend of three models that
          look at the same fixture from very different angles:
        </p>
        <ul>
          <li>
            <b>Poisson + Dixon-Coles</b> — builds a joint goal-count
            matrix from per-team attack / defense coefficients and a
            correction term ρ for low-scoreline correlation.
          </li>
          <li>
            <b>Elo (K=20, HFA=+70)</b> — chess-style rating updated after
            every result, weighted by goal difference. No xG; just outcomes.
          </li>
          <li>
            <b>XGBoost (27 features)</b> — gradient-boosted classifier
            trained on 7 seasons across 5 leagues. Features include team
            strengths, Elo, form, rest days, midweek flag, market-implied
            probabilities, and referee.
          </li>
        </ul>
        <p>
          Final probabilities = 0.20 × Elo + 0.60 × XGB + 0.20 × Poisson.
          Weights were tuned by grid-search on walk-forward log-loss.
        </p>
      </section>

      <section className="space-y-4">
        <h2>Adjustments on top</h2>
        <p>
          Predictions get multiplied by a stack of per-fixture context
          when it's available:
        </p>
        <ul>
          <li><b>Injury shrink</b> — subtract influence of missing starters.</li>
          <li><b>Weather</b> — wind / rain caps xG by a small factor.</li>
          <li><b>Referee lean</b> — goals-per-match trend per official.</li>
          <li><b>Lineup-sum</b> — when a confirmed XI arrives (T-60min typical).</li>
          <li><b>Fatigue</b> — rest days, 14-day congestion, midweek flag.</li>
        </ul>
      </section>

      <section className="space-y-4">
        <h2>What we don't do</h2>
        <ul>
          <li>No deep nets. Dataset is too small (~5k matches/season) to beat XGBoost; would overfit.</li>
          <li>No LLM-generated probabilities. Qwen writes reasoning prose; math never comes from it.</li>
          <li>No custody, no stake placement, no wallet. Entertainment-grade forecasting only.</li>
        </ul>
      </section>

      <section className="space-y-4">
        <h2>Honest gaps</h2>
        <p>
          See <Link href="/calibration">/calibration</Link> for the
          reliability curve — the model is mildly underconfident at 50%
          bands. See <Link href="/equity-curve">/equity-curve</Link>{" "}
          for the 7-season flat-stake P&L (negative overall at 5pp edge).
          See <Link href="/benchmark/by-team">/benchmark/by-team</Link>{" "}
          for where the model is strong (elite teams) vs weak (chaotic
          mid-table).
        </p>
        <p>
          The goal of these pages is transparency: a reader should be able
          to assess whether to trust the forecasts in under 60 seconds.
        </p>
      </section>
    </main>
  );
}
