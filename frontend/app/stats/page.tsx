import Link from "next/link";

import RoiChart from "@/components/RoiChart";
import { getLang, tFor } from "@/lib/i18n-server";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type Overall = {
  season: string;
  scored: number;
  correct: number;
  accuracy: number;
  baseline_home_accuracy: number;
  mean_log_loss: number;
  uniform_log_loss: number;
};

type WeekBucket = {
  week: number;
  week_start: string;
  n: number;
  accuracy: number;
  mean_log_loss: number;
};

type CalibrationBin = {
  bin_lo: number;
  bin_hi: number;
  n: number;
  mean_predicted: number;
  actual_hit_rate: number;
};

type StatsOut = {
  season: string;
  overall: Overall;
  brier: number;
  by_week: WeekBucket[];
  by_confidence: CalibrationBin[];
};

async function fetchStats(season: string): Promise<StatsOut | null> {
  const res = await fetch(`${BASE}/api/stats/calibration?season=${encodeURIComponent(season)}`, {
    cache: "no-store",
  });
  if (!res.ok) return null;
  return res.json();
}

function pct(x: number) {
  return `${Math.round(x * 100)}%`;
}

function deltaPP(actual: number, predicted: number) {
  return Math.round((actual - predicted) * 100);
}

export default async function StatsPage() {
  const lang = await getLang();
  const t = tFor(lang);
  const s = await fetchStats("2025-26");
  if (!s) {
    return (
      <main className="mx-auto max-w-5xl px-6 py-12">
        <div className="card text-error">{t("dash.apiError")}</div>
      </main>
    );
  }

  const o = s.overall;
  const baselineLine = o.baseline_home_accuracy;

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-10">
      <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">{t("common.season")} {s.season}</p>
        <h1 className="headline-section">{t("stats.title")}</h1>
        <p className="max-w-2xl text-secondary">{t("stats.subhead")}</p>
      </header>

      <section className="card grid grid-cols-2 md:grid-cols-5 gap-6">
        <div>
          <p className="text-xs text-muted">{t("dash.stat.accuracy")}</p>
          <p className="stat text-neon">{pct(o.accuracy)}</p>
        </div>
        <div>
          <p className="text-xs text-muted">{t("dash.stat.baseline")}</p>
          <p className="stat">{pct(o.baseline_home_accuracy)}</p>
        </div>
        <div>
          <p className="text-xs text-muted">{t("dash.stat.logloss")}</p>
          <p className="stat">{o.mean_log_loss.toFixed(3)}</p>
        </div>
        <div>
          <p className="text-xs text-muted">{t("stats.brier")}</p>
          <p className="stat">{s.brier.toFixed(3)}</p>
        </div>
        <div>
          <p className="text-xs text-muted">{t("dash.stat.matches")}</p>
          <p className="stat">{o.scored}</p>
        </div>
      </section>

      <RoiChart season={s.season} threshold={0.05} lang={lang} />

      <section className="card space-y-4">
        <h2 className="font-display font-semibold uppercase tracking-tight">{t("stats.bins.title")}</h2>
        <p className="text-muted text-sm">{t("stats.bins.hint")}</p>

        <div className="overflow-x-auto">
          <table className="w-full font-mono text-sm">
            <thead className="text-muted">
              <tr className="border-b border-border">
                {[
                  t("stats.bins.bin"),
                  t("stats.bins.n"),
                  t("stats.bins.pred"),
                  t("stats.bins.actual"),
                  t("stats.bins.delta"),
                  t("stats.bins.reliability"),
                ].map((h) => (
                  <th key={h} className="label px-3 py-2 text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {s.by_confidence.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 py-4 text-muted">
                    {t("stats.bins.empty")}
                  </td>
                </tr>
              )}
              {s.by_confidence.map((b) => {
                const dpp = deltaPP(b.actual_hit_rate, b.mean_predicted);
                const deltaClass =
                  dpp >= 2 ? "text-neon" : dpp <= -2 ? "text-error" : "text-muted";
                const predLeft = b.mean_predicted * 100;
                const actLeft = b.actual_hit_rate * 100;
                return (
                  <tr key={`${b.bin_lo}-${b.bin_hi}`} className="border-b border-border-muted">
                    <td className="px-3 py-3 text-primary">
                      {pct(b.bin_lo)}–{pct(b.bin_hi)}
                    </td>
                    <td className="px-3 py-3 tabular-nums">{b.n}</td>
                    <td className="px-3 py-3 tabular-nums text-secondary">
                      {pct(b.mean_predicted)}
                    </td>
                    <td className="px-3 py-3 tabular-nums text-primary">{pct(b.actual_hit_rate)}</td>
                    <td className={`px-3 py-3 tabular-nums ${deltaClass}`}>
                      {dpp > 0 ? "+" : ""}
                      {dpp}pp
                    </td>
                    <td className="px-3 py-3 w-64">
                      <div className="relative h-2 rounded-full bg-raised">
                        <div
                          className="absolute top-[-4px] h-4 w-[2px] bg-muted"
                          style={{ left: `${predLeft}%` }}
                        />
                        <div
                          className="absolute h-full rounded-full bg-neon"
                          style={{ left: 0, width: `${actLeft}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card space-y-4">
        <h2 className="font-display font-semibold uppercase tracking-tight">{t("stats.weekly.title")}</h2>
        <p className="text-muted text-sm">
          {t("stats.weekly.hint", { baseline: pct(baselineLine) })}
        </p>

        <div className="flex gap-1 items-end h-40 overflow-x-auto pb-2">
          {s.by_week.map((w) => {
            const h = Math.max(4, w.accuracy * 140);
            const beats = w.accuracy > baselineLine;
            return (
              <div
                key={w.week}
                className="flex flex-col items-center gap-1 min-w-[36px]"
                title={`Week ${w.week} ${w.week_start}: ${pct(w.accuracy)} (${w.n})`}
              >
                <span className="font-mono text-[10px] text-muted tabular-nums">
                  {pct(w.accuracy)}
                </span>
                <div
                  className={`w-6 rounded-t ${beats ? "bg-neon" : "bg-high"}`}
                  style={{ height: `${h}px` }}
                />
                <span className="font-mono text-[10px] text-muted">W{w.week}</span>
              </div>
            );
          })}
        </div>
      </section>
    </main>
  );
}
