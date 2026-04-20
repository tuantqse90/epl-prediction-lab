import type { Metadata } from "next";
import Link from "next/link";

import { getLang, tFor } from "@/lib/i18n-server";
import { leagueByCode } from "@/lib/leagues";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "ROI by league — where the edge actually shows up · predictor.nullshift.sh",
  description:
    "Flat-stake ROI split per league on every model edge ≥ 5pp. " +
    "Walks the same bet universe as /roi but tells you which market the P&L " +
    "is actually coming from — EPL vs La Liga vs Serie A vs Bundesliga vs Ligue 1.",
  alternates: { canonical: "/roi/by-league" },
};

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type RoiLeague = {
  league_code: string;
  bets: number;
  wins: number;
  pnl_vig: number;
  pnl_nov: number;
  roi_vig_pct: number;
  roi_nov_pct: number;
  mean_log_loss: number;
  scored: number;
};

type RoiByLeague = {
  window: string;
  threshold: number;
  season: string | null;
  leagues: RoiLeague[];
};

const WINDOWS = ["7d", "30d", "90d", "season"] as const;
const THRESHOLDS = [0.03, 0.05, 0.07, 0.1] as const;

async function fetchByLeague(window: string, threshold: number): Promise<RoiByLeague | null> {
  const qs = new URLSearchParams({ window, threshold: String(threshold), season: "2025-26" });
  const res = await fetch(`${BASE}/api/stats/roi/by-league?${qs}`, { next: { revalidate: 600 } });
  if (!res.ok) return null;
  return res.json();
}

function signed(x: number, digits = 2) {
  return `${x > 0 ? "+" : ""}${x.toFixed(digits)}`;
}

export default async function RoiByLeaguePage({
  searchParams,
}: {
  searchParams: Promise<{ window?: string; threshold?: string }>;
}) {
  const sp = await searchParams;
  const window = (WINDOWS as readonly string[]).includes(sp.window ?? "")
    ? (sp.window as string)
    : "30d";
  const thr = Number(sp.threshold ?? "0.05");
  const threshold = (THRESHOLDS as readonly number[]).includes(thr) ? thr : 0.05;

  const lang = await getLang();
  const t = tFor(lang);
  const data = await fetchByLeague(window, threshold);

  if (!data) {
    return (
      <main className="mx-auto max-w-5xl px-6 py-12">
        <div className="card text-error">{t("dash.apiError")}</div>
      </main>
    );
  }

  const positives = data.leagues.filter((l) => l.bets >= 10 && l.roi_vig_pct > 0).length;
  const total = data.leagues.filter((l) => l.bets >= 10).length;

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-10">
      <Link href="/roi" className="btn-ghost text-sm">
        {t("common.back")}
      </Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">
          {lang === "vi"
            ? "ROI theo giải · edge ≥ 5pp, stake 1 đơn vị"
            : "Per-league ROI · edge ≥ 5pp, 1-unit flat stake"}
        </p>
        <h1 className="headline-section">
          {lang === "vi" ? "Biên lợi nhuận ở giải nào?" : "Where does the edge actually show up?"}
        </h1>
        <p className="max-w-2xl text-secondary">
          {lang === "vi"
            ? "Toàn thị trường có thể hòa vốn, nhưng P&L trong đó phân bố không đều. Trang này tách ROI flat-stake theo từng giải để bạn thấy giải nào model đang kiếm tiền thật, giải nào bị thị trường đè."
            : "Aggregate ROI can look flat while the underlying P&L is very uneven. This page splits it per league so you can see which markets the edge is actually coming from."}
        </p>
      </header>

      <section className="flex flex-wrap gap-2">
        <div className="flex flex-wrap gap-2 mr-4">
          <span className="font-mono text-[10px] uppercase tracking-wide text-muted self-center mr-1">
            window
          </span>
          {WINDOWS.map((w) => (
            <Link
              key={w}
              href={`/roi/by-league?window=${w}&threshold=${threshold}`}
              className={
                "rounded-full px-3 py-1 font-mono text-xs uppercase tracking-wide border " +
                (window === w
                  ? "border-neon bg-neon text-on-neon"
                  : "border-border text-secondary hover:border-neon hover:text-neon")
              }
            >
              {w}
            </Link>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="font-mono text-[10px] uppercase tracking-wide text-muted self-center mr-1">
            edge
          </span>
          {THRESHOLDS.map((thr) => (
            <Link
              key={thr}
              href={`/roi/by-league?window=${window}&threshold=${thr}`}
              className={
                "rounded-full px-3 py-1 font-mono text-xs uppercase tracking-wide border " +
                (Math.abs(thr - threshold) < 0.0001
                  ? "border-neon bg-neon text-on-neon"
                  : "border-border text-secondary hover:border-neon hover:text-neon")
              }
            >
              ≥ {Math.round(thr * 100)}%
            </Link>
          ))}
        </div>
      </section>

      <section className="card space-y-3">
        <p className="font-mono text-[10px] uppercase tracking-wide text-muted">
          {lang === "vi" ? "Tóm tắt" : "Summary"}
        </p>
        <p className="text-secondary">
          {lang === "vi"
            ? `${positives}/${total} giải có ROI dương (≥ 10 kèo). Mặc định trang chủ (QuickPicks) sẽ lọc bỏ giải có ROI 30d âm.`
            : `${positives}/${total} leagues have positive ROI (≥ 10 bets in sample). The home-page QuickPicks hides leagues with negative 30d ROI by default.`}
        </p>
      </section>

      <section className="card">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-[10px] uppercase tracking-wide text-muted">
              <tr className="text-left">
                <th className="py-2 pr-4">{lang === "vi" ? "Giải" : "League"}</th>
                <th className="py-2 pr-4 text-right">{lang === "vi" ? "Kèo" : "Bets"}</th>
                <th className="py-2 pr-4 text-right">{lang === "vi" ? "Thắng" : "Wins"}</th>
                <th className="py-2 pr-4 text-right">P&amp;L (u)</th>
                <th className="py-2 pr-4 text-right">ROI (vig)</th>
                <th className="py-2 pr-4 text-right">ROI (no-vig)</th>
                <th className="py-2 pr-4 text-right">Log-loss</th>
              </tr>
            </thead>
            <tbody>
              {data.leagues.map((l) => {
                const info = leagueByCode(l.league_code);
                const labelEmoji = info?.emoji ?? "🌍";
                const labelName = info ? (lang === "vi" ? info.name_vi : info.name_en) : l.league_code;
                const posVig = l.roi_vig_pct > 0;
                const posNov = l.roi_nov_pct > 0;
                const tooFew = l.bets < 10;
                return (
                  <tr key={l.league_code} className={"border-t border-border-muted " + (tooFew ? "text-muted" : "")}>
                    <td className="py-2 pr-4">
                      <span className="mr-2">{labelEmoji}</span>
                      <span className="font-display uppercase tracking-tighter">{labelName}</span>
                      {tooFew && (
                        <span className="ml-2 font-mono text-[9px] uppercase tracking-wide text-muted">
                          {lang === "vi" ? "ít mẫu" : "sparse"}
                        </span>
                      )}
                    </td>
                    <td className="py-2 pr-4 text-right font-mono tabular-nums">{l.bets}</td>
                    <td className="py-2 pr-4 text-right font-mono tabular-nums">{l.wins}</td>
                    <td className="py-2 pr-4 text-right font-mono tabular-nums">{signed(l.pnl_vig)}</td>
                    <td className={"py-2 pr-4 text-right font-mono tabular-nums " + (posVig ? "text-neon" : "text-error")}>
                      {signed(l.roi_vig_pct)}%
                    </td>
                    <td className={"py-2 pr-4 text-right font-mono tabular-nums " + (posNov ? "text-neon" : "text-error")}>
                      {signed(l.roi_nov_pct)}%
                    </td>
                    <td className="py-2 pr-4 text-right font-mono tabular-nums text-muted">
                      {l.mean_log_loss.toFixed(3)}
                    </td>
                  </tr>
                );
              })}
              {data.leagues.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-muted">
                    {lang === "vi" ? "Chưa có dữ liệu" : "No data"}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="font-mono text-[11px] uppercase tracking-wide text-muted space-y-1">
        <p>
          {lang === "vi"
            ? "• ROI (vig) = flat-stake 1u tại best-odds, ăn cả vig thị trường"
            : "• ROI (vig) = 1u flat stake at best available bookmaker odds"}
        </p>
        <p>
          {lang === "vi"
            ? "• ROI (no-vig) = mô phỏng thị trường Polymarket-style (0% phí)"
            : "• ROI (no-vig) = simulates a Polymarket-style zero-overround market"}
        </p>
        <p>
          {lang === "vi"
            ? "• Giải có ít hơn 10 kèo được đánh dấu 'ít mẫu' — chưa đủ để tin"
            : "• Leagues with fewer than 10 bets in the sample are marked 'sparse' — not trustworthy yet"}
        </p>
      </section>
    </main>
  );
}
