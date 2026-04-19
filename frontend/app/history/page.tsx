import Link from "next/link";

import { getLang, getLeagueSlug, leagueForApi, tFor } from "@/lib/i18n-server";
import { getLeague } from "@/lib/leagues";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type HistorySeason = {
  season: string;
  scored: number;
  correct: number;
  accuracy: number;
  mean_log_loss: number;
  baseline_home_accuracy: number;
};

async function fetchHistory(league?: string): Promise<HistorySeason[]> {
  const qs = league ? `?league=${encodeURIComponent(league)}` : "";
  const res = await fetch(`${BASE}/api/stats/history${qs}`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

function pct(x: number) {
  return `${Math.round(x * 100)}%`;
}

export default async function HistoryPage() {
  const lang = await getLang();
  const t = tFor(lang);
  const league = await getLeagueSlug();
  const leagueInfo = getLeague(league);
  const rows = await fetchHistory(leagueForApi(league));
  const leagueLabel = lang === "vi" ? leagueInfo.name_vi : leagueInfo.name_en;

  if (rows.length === 0) {
    return (
      <main className="mx-auto max-w-5xl px-6 py-12 space-y-6">
        <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>
        <h1 className="headline-section">History</h1>
        <div className="card text-muted">No prior-season data for this league.</div>
      </main>
    );
  }

  const maxAccuracy = Math.max(...rows.map((r) => r.accuracy), 0.55);
  const weightedAcc =
    rows.reduce((s, r) => s + r.correct, 0) /
    rows.reduce((s, r) => s + r.scored, 0);
  const weightedBaseline =
    rows.reduce((s, r) => s + r.baseline_home_accuracy * r.scored, 0) /
    rows.reduce((s, r) => s + r.scored, 0);
  const weightedLogLoss =
    rows.reduce((s, r) => s + r.mean_log_loss * r.scored, 0) /
    rows.reduce((s, r) => s + r.scored, 0);

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-10">
      <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">{leagueInfo.emoji} {leagueLabel}</p>
        <h1 className="headline-section">Historical accuracy</h1>
        <p className="text-secondary max-w-2xl">
          Season-by-season performance of the model on finals across {rows.length} season{rows.length === 1 ? "" : "s"}.
        </p>
      </header>

      <section className="card grid grid-cols-2 md:grid-cols-4 gap-6">
        <div>
          <p className="label">Accuracy (weighted)</p>
          <p className="stat text-neon">{pct(weightedAcc)}</p>
        </div>
        <div>
          <p className="label">Baseline (always home)</p>
          <p className="stat">{pct(weightedBaseline)}</p>
        </div>
        <div>
          <p className="label">Log-loss</p>
          <p className="stat">{weightedLogLoss.toFixed(3)}</p>
        </div>
        <div>
          <p className="label">Matches scored</p>
          <p className="stat">{rows.reduce((s, r) => s + r.scored, 0).toLocaleString()}</p>
        </div>
      </section>

      {/* Per-season accuracy bars */}
      <section className="card space-y-4">
        <h2 className="label">Per-season accuracy</h2>
        <div className="space-y-2">
          {rows.map((r) => {
            const widthPct = (r.accuracy / maxAccuracy) * 100;
            const baselineLeftPct = (r.baseline_home_accuracy / maxAccuracy) * 100;
            const beatsBaseline = r.accuracy > r.baseline_home_accuracy;
            return (
              <div key={r.season} className="flex items-center gap-3 font-mono text-xs">
                <span className="w-20 shrink-0 text-muted">{r.season}</span>
                <div className="relative flex-1 h-6 rounded bg-high overflow-hidden">
                  <div
                    className={`h-full transition-all ${beatsBaseline ? "bg-neon" : "bg-error"}`}
                    style={{ width: `${widthPct}%` }}
                  />
                  <div
                    aria-label="baseline"
                    className="absolute top-0 bottom-0 w-[2px] bg-secondary/60"
                    style={{ left: `${baselineLeftPct}%` }}
                  />
                </div>
                <span className={`w-12 shrink-0 text-right tabular-nums ${beatsBaseline ? "text-neon" : "text-error"}`}>
                  {pct(r.accuracy)}
                </span>
                <span className="w-16 shrink-0 text-right tabular-nums text-muted">
                  {r.scored}m
                </span>
              </div>
            );
          })}
        </div>
        <p className="text-[11px] text-muted">
          Vertical line = &quot;always pick home&quot; baseline. Neon bar = beats baseline, red bar = worse than baseline.
        </p>
      </section>

      {/* Log-loss line, text-based */}
      <section className="card space-y-3">
        <h2 className="label">Log-loss per season</h2>
        <p className="text-[11px] text-muted">Lower is better. Uniform-random baseline = 1.099.</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono text-sm">
          {rows.map((r) => {
            const good = r.mean_log_loss < 1.099;
            return (
              <div key={r.season}>
                <p className="text-xs text-muted">{r.season}</p>
                <p className={`stat text-2xl ${good ? "text-neon" : "text-error"}`}>
                  {r.mean_log_loss.toFixed(3)}
                </p>
              </div>
            );
          })}
        </div>
      </section>
    </main>
  );
}
