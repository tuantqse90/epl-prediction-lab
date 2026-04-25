import type { Metadata } from "next";
import Link from "next/link";

import { getLang, getLeagueSlug, leagueForApi, tFor } from "@/lib/i18n-server";
import type { Lang } from "@/lib/i18n";
import { getLeague, leagueByCode } from "@/lib/leagues";
import { alternatesFor } from "@/lib/seo";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Historical accuracy — season by season · predictor.nullshift.sh",
  description:
    "Walk-forward model accuracy per season across every league we track.",
  alternates: alternatesFor("/history"),
};

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type HistorySeason = {
  season: string;
  scored: number;
  correct: number;
  accuracy: number;
  mean_log_loss: number;
  baseline_home_accuracy: number;
  leagues_covered: string[];
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

function copy(lang: Lang) {
  return {
    back: lang === "vi" ? "← Quay lại" : "← Back",
    title: lang === "vi" ? "Accuracy theo mùa" : "Historical accuracy",
    subhead: (n: number) =>
      lang === "vi"
        ? `Hiệu suất model trên trận đã kết thúc, qua ${n} mùa.`
        : `Season-by-season performance of the model on finals across ${n} season${n === 1 ? "" : "s"}.`,
    emptyAll: lang === "vi"
      ? "Chưa có dữ liệu lịch sử cho giải này."
      : "No prior-season data for this league.",
    weightedAcc: lang === "vi" ? "Accuracy (gia trọng)" : "Accuracy (weighted)",
    baseline: lang === "vi" ? "Baseline (luôn chủ nhà)" : "Baseline (always home)",
    logLoss: "Log-loss",
    matchesScored: lang === "vi" ? "Trận đã chấm" : "Matches scored",
    perSeason: lang === "vi" ? "Accuracy mỗi mùa" : "Per-season accuracy",
    perSeasonLogLoss: lang === "vi" ? "Log-loss mỗi mùa" : "Log-loss per season",
    lowerBetter: lang === "vi"
      ? "Thấp hơn tốt hơn. Baseline uniform-random = 1.099."
      : "Lower is better. Uniform-random baseline = 1.099.",
    barHint: lang === "vi"
      ? 'Vạch dọc = baseline "luôn chọn chủ nhà". Neon = model beat baseline, đỏ = thua.'
      : 'Vertical line = "always pick home" baseline. Neon = beats baseline, red = worse.',
    coverageHeader: lang === "vi" ? "Lưu ý về phạm vi data" : "Coverage caveat",
    coverageBody: (oldN: number, newN: number) =>
      lang === "vi"
        ? `${oldN} mùa đầu chỉ có EPL (~380 trận/mùa). Từ 2025-26, mình mở rộng sang ${newN} giải top 5 (~1,500 trận/mùa) nên số lượng tăng vọt. Weighted average so mùa cũ vs mới ko fair — nếu muốn số thuần nhất 1 giải, chọn league cụ thể trên header.`
        : `The oldest ${oldN} seasons are EPL-only (~380 matches/season). From 2025-26 we expanded to ${newN} top-5 leagues (~1,500 matches/season), so the counts jump. Weighted averages across mixed scopes aren't apples-to-apples — pick a specific league in the header for a clean series.`,
  };
}

export default async function HistoryPage() {
  const lang = await getLang();
  const t = tFor(lang);
  const league = await getLeagueSlug();
  const leagueInfo = getLeague(league);
  const leagueParam = leagueForApi(league);
  const rows = await fetchHistory(leagueParam);
  const leagueLabel = lang === "vi" ? leagueInfo.name_vi : leagueInfo.name_en;
  const c = copy(lang);

  if (rows.length === 0) {
    return (
      <main className="mx-auto max-w-5xl px-6 py-12 space-y-6">
        <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>
        <h1 className="headline-section">{c.title}</h1>
        <div className="card text-muted">{c.emptyAll}</div>
      </main>
    );
  }

  const maxAccuracy = Math.max(...rows.map((r) => r.accuracy), 0.55);
  const totalScored = rows.reduce((s, r) => s + r.scored, 0);
  const weightedAcc = rows.reduce((s, r) => s + r.correct, 0) / totalScored;
  const weightedBaseline =
    rows.reduce((s, r) => s + r.baseline_home_accuracy * r.scored, 0) / totalScored;
  const weightedLogLoss =
    rows.reduce((s, r) => s + r.mean_log_loss * r.scored, 0) / totalScored;

  // Coverage discrepancy: are some seasons single-league and others multi?
  const leaguesPerSeason = rows.map((r) => r.leagues_covered.length);
  const minLg = Math.min(...leaguesPerSeason);
  const maxLg = Math.max(...leaguesPerSeason);
  const hasMixedCoverage = maxLg > minLg && !leagueParam;
  const oldN = rows.filter((r) => r.leagues_covered.length === minLg).length;

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-10">
      <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">{leagueInfo.emoji} {leagueLabel}</p>
        <h1 className="headline-section">{c.title}</h1>
        <p className="text-secondary max-w-2xl">{c.subhead(rows.length)}</p>
      </header>

      {hasMixedCoverage && (
        <section className="rounded-xl border border-warning/40 bg-high p-5 space-y-2">
          <p className="font-mono text-[11px] uppercase tracking-wide text-warning">
            {c.coverageHeader}
          </p>
          <p className="text-secondary text-sm leading-relaxed">
            {c.coverageBody(oldN, maxLg)}
          </p>
        </section>
      )}

      <section className="card grid grid-cols-2 md:grid-cols-4 gap-6">
        <div>
          <p className="label">{c.weightedAcc}</p>
          <p className="stat text-neon">{pct(weightedAcc)}</p>
        </div>
        <div>
          <p className="label">{c.baseline}</p>
          <p className="stat">{pct(weightedBaseline)}</p>
        </div>
        <div>
          <p className="label">{c.logLoss}</p>
          <p className="stat">{weightedLogLoss.toFixed(3)}</p>
        </div>
        <div>
          <p className="label">{c.matchesScored}</p>
          <p className="stat">{totalScored.toLocaleString()}</p>
        </div>
      </section>

      {/* Per-season accuracy bars */}
      <section className="card space-y-4">
        <h2 className="label">{c.perSeason}</h2>
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
                <span className="w-32 shrink-0 flex items-center gap-0.5 font-mono text-[10px] text-muted overflow-hidden" title={r.leagues_covered.join(", ")}>
                  {r.leagues_covered.slice(0, 5).map((lc) => {
                    const info = leagueByCode(lc);
                    return (
                      <span key={lc} className="inline-block" title={info ? (lang === "vi" ? info.name_vi : info.name_en) : lc}>
                        {info?.emoji ?? "🏴"}
                      </span>
                    );
                  })}
                </span>
              </div>
            );
          })}
        </div>
        <p className="text-[11px] text-muted">{c.barHint}</p>
      </section>

      {/* Log-loss per season */}
      <section className="card space-y-3">
        <h2 className="label">{c.perSeasonLogLoss}</h2>
        <p className="text-[11px] text-muted">{c.lowerBetter}</p>
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
