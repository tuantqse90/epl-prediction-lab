import Link from "next/link";

import { getLang } from "@/lib/i18n-server";
import { tLang } from "@/lib/i18n-fallback";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type SeasonResult = {
  season: string;
  bets: number;
  wins: number;
  pnl: number;
  roi_percent: number;
  cumulative_pnl: number;
};

type Response = {
  threshold: number;
  seasons: SeasonResult[];
};

async function fetchData(): Promise<Response | null> {
  try {
    const res = await fetch(`${BASE}/api/stats/equity-curve?threshold=0.05`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return (await res.json()) as Response;
  } catch {
    return null;
  }
}

export default async function EquityCurvePage() {
  const lang = await getLang();
  const data = await fetchData();
  if (!data || data.seasons.length === 0) {
    return <main className="mx-auto max-w-3xl px-6 py-12"><div className="card text-muted">—</div></main>;
  }

  const total_bets = data.seasons.reduce((s, x) => s + x.bets, 0);
  const total_pnl = data.seasons.reduce((s, x) => s + x.pnl, 0);
  const overall_roi = total_bets > 0 ? (total_pnl / total_bets) * 100 : 0;
  const final_cumulative = data.seasons[data.seasons.length - 1]?.cumulative_pnl ?? 0;
  const peak = Math.max(...data.seasons.map((s) => s.cumulative_pnl), 0);
  const trough = Math.min(...data.seasons.map((s) => s.cumulative_pnl), 0);

  // SVG equity curve
  const W = 720, H = 280, PAD = 40;
  const minCum = Math.min(trough, -1);
  const maxCum = Math.max(peak, 1);
  const spanY = maxCum - minCum;
  const toX = (i: number) => PAD + (i / (data.seasons.length - 1 || 1)) * (W - 2 * PAD);
  const toY = (v: number) => H - PAD - ((v - minCum) / spanY) * (H - 2 * PAD);

  const points = data.seasons.map((s, i) => `${toX(i)},${toY(s.cumulative_pnl)}`).join(" ");

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-10">
      <Link href="/benchmark" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Benchmark", vi: "← Benchmark", th: "← Benchmark", zh: "← 基准", ko: "← 벤치마크" })}
      </Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">benchmark · equity curve</p>
        <h1 className="headline-section">
          {tLang(lang, {
            en: "Season-over-season equity curve",
            vi: "Đường cong P&L qua các mùa",
            th: "เส้น equity ต่อฤดูกาล",
            zh: "逐季资金曲线",
            ko: "시즌별 자금 곡선",
          })}
        </h1>
        <p className="max-w-2xl text-secondary">
          {tLang(lang, {
            en: "1u flat stake on every model pick with edge ≥ 5pp vs best available odds, per season. Shows whether the edge compounds or is just a recent-form quirk.",
            vi: "Stake 1u mỗi pick model edge ≥ 5pp vs best-odds, tính từng mùa. Kiểm tra edge có bền hay chỉ variance gần đây.",
            th: "เดิมพัน 1u ทุกพิกที่โมเดลมี edge ≥ 5pp",
            zh: "模型 edge ≥ 5pp 的每个选择平 1u",
            ko: "모델 엣지 ≥ 5pp인 매 선택에 1u 플랫",
          })}
        </p>
      </header>

      <section className="card grid grid-cols-2 md:grid-cols-4 gap-6">
        <div>
          <p className="label">{tLang(lang, { en: "Seasons", vi: "Mùa", th: "ฤดูกาล", zh: "赛季", ko: "시즌" })}</p>
          <p className="stat">{data.seasons.length}</p>
        </div>
        <div>
          <p className="label">{tLang(lang, { en: "Total bets", vi: "Tổng kèo", th: "เดิมพันรวม", zh: "总注数", ko: "총 베팅" })}</p>
          <p className="stat">{total_bets.toLocaleString()}</p>
        </div>
        <div>
          <p className="label">{tLang(lang, { en: "Final bankroll", vi: "Tổng kết", th: "สุดท้าย", zh: "最终", ko: "최종" })}</p>
          <p className={`stat ${final_cumulative > 0 ? "text-neon" : final_cumulative < 0 ? "text-error" : ""}`}>
            {final_cumulative > 0 ? "+" : ""}{final_cumulative.toFixed(1)}u
          </p>
        </div>
        <div>
          <p className="label">{tLang(lang, { en: "Overall ROI", vi: "ROI tổng", th: "ROI รวม", zh: "总 ROI", ko: "전체 ROI" })}</p>
          <p className={`stat ${overall_roi > 0 ? "text-neon" : "text-error"}`}>
            {overall_roi > 0 ? "+" : ""}{overall_roi.toFixed(1)}%
          </p>
        </div>
      </section>

      <section className="card">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
          {/* Zero baseline */}
          <line x1={PAD} y1={toY(0)} x2={W - PAD} y2={toY(0)}
                stroke="#555" strokeDasharray="3 3" opacity="0.5" />
          <text x={6} y={toY(0) + 3} fill="#777" fontSize="10">0u</text>
          {/* Y ticks */}
          {[peak, trough].filter((v) => Math.abs(v) > 0.5).map((v) => (
            <text key={v} x={6} y={toY(v) + 3} fill="#777" fontSize="10">
              {v > 0 ? "+" : ""}{v.toFixed(0)}u
            </text>
          ))}
          {/* Season line */}
          <polyline
            fill="none"
            stroke="#E0FF32"
            strokeWidth="2.5"
            points={points}
          />
          {/* Season dots */}
          {data.seasons.map((s, i) => (
            <g key={s.season}>
              <circle
                cx={toX(i)}
                cy={toY(s.cumulative_pnl)}
                r="4"
                fill={s.pnl > 0 ? "#E0FF32" : "#ff5a5a"}
              />
              <text
                x={toX(i)}
                y={H - 8}
                fill="#999"
                fontSize="10"
                textAnchor="middle"
              >
                {s.season}
              </text>
            </g>
          ))}
        </svg>
      </section>

      <section className="card p-0 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-[10px] uppercase tracking-wide text-muted">
            <tr className="border-b border-border">
              <th className="px-3 py-3 text-left">
                {tLang(lang, { en: "Season", vi: "Mùa", th: "ฤดู", zh: "赛季", ko: "시즌" })}
              </th>
              <th className="px-3 py-3 text-right">
                {tLang(lang, { en: "Bets", vi: "Kèo", th: "เดิมพัน", zh: "注数", ko: "베팅" })}
              </th>
              <th className="px-3 py-3 text-right">
                {tLang(lang, { en: "Wins", vi: "Thắng", th: "ชนะ", zh: "胜", ko: "승" })}
              </th>
              <th className="px-3 py-3 text-right">P&amp;L</th>
              <th className="px-3 py-3 text-right">ROI</th>
              <th className="px-3 py-3 text-right">Σ</th>
            </tr>
          </thead>
          <tbody>
            {data.seasons.map((s) => (
              <tr key={s.season} className="border-t border-border-muted">
                <td className="px-3 py-2 font-mono">{s.season}</td>
                <td className="px-3 py-2 text-right font-mono tabular-nums">{s.bets}</td>
                <td className="px-3 py-2 text-right font-mono tabular-nums">{s.wins}</td>
                <td className={`px-3 py-2 text-right font-mono tabular-nums ${s.pnl > 0 ? "text-neon" : s.pnl < 0 ? "text-error" : ""}`}>
                  {s.pnl > 0 ? "+" : ""}{s.pnl.toFixed(2)}
                </td>
                <td className={`px-3 py-2 text-right font-mono tabular-nums ${s.roi_percent > 0 ? "text-neon" : s.roi_percent < 0 ? "text-error" : ""}`}>
                  {s.roi_percent > 0 ? "+" : ""}{s.roi_percent.toFixed(1)}%
                </td>
                <td className={`px-3 py-2 text-right font-mono tabular-nums ${s.cumulative_pnl > 0 ? "text-neon" : "text-error"}`}>
                  {s.cumulative_pnl > 0 ? "+" : ""}{s.cumulative_pnl.toFixed(1)}u
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="font-mono text-[11px] uppercase tracking-wide text-muted space-y-1">
        <p>• Threshold {(data.threshold * 100).toFixed(0)}pp edge vs best bookmaker odds across all stored books</p>
        <p>• Peak bankroll: {peak > 0 ? "+" : ""}{peak.toFixed(1)}u · Trough: {trough.toFixed(1)}u</p>
      </section>
    </main>
  );
}
