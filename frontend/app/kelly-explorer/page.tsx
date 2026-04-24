import Link from "next/link";

import { getLang } from "@/lib/i18n-server";
import { tLang } from "@/lib/i18n-fallback";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type KellyResult = {
  starting_units: number;
  final_units: number;
  peak_units: number;
  max_drawdown_pct: number;
  total_bets: number;
  roi_percent: number;
  points: { date: string; bets: number; bankroll: number }[];
};

const CAPS = [0.10, 0.15, 0.25, 0.50, 0.75, 1.00];

async function fetchKelly(cap: number): Promise<KellyResult | null> {
  try {
    const res = await fetch(
      `${BASE}/api/stats/roi/kelly?threshold=0.05&cap=${cap}&starting=100`,
      { next: { revalidate: 600 } },
    );
    if (!res.ok) return null;
    return (await res.json()) as KellyResult;
  } catch {
    return null;
  }
}

export default async function KellyExplorerPage() {
  const lang = await getLang();
  const results = await Promise.all(CAPS.map(async (c) => ({ cap: c, r: await fetchKelly(c) })));
  const good = results.filter((x) => x.r) as Array<{ cap: number; r: KellyResult }>;

  if (good.length === 0) {
    return <main className="mx-auto max-w-3xl px-6 py-12"><div className="card text-error">—</div></main>;
  }

  // All curves share the same timeline — use the first one for x-axis.
  const ref = good[0].r;
  const W = 720, H = 240, PAD = 40;
  const allBk = good.flatMap((x) => x.r.points.map((p) => p.bankroll));
  const minB = Math.min(...allBk, ref.starting_units * 0.5);
  const maxB = Math.max(...allBk, ref.starting_units * 1.5);
  const toX = (i: number) => PAD + (i / (Math.max(ref.points.length - 1, 1))) * (W - 2 * PAD);
  const toY = (v: number) => H - PAD - ((v - minB) / (maxB - minB || 1)) * (H - 2 * PAD);

  const palette = ["#E0FF32", "#4ea0ff", "#ff72a6", "#ffc247", "#9cff9c", "#b888ff"];

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-8">
      <Link href="/roi" className="btn-ghost text-sm">
        {tLang(lang, { en: "← ROI", vi: "← ROI", th: "← ROI", zh: "← ROI", ko: "← ROI" })}
      </Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">sharp · kelly explorer</p>
        <h1 className="headline-section">
          {tLang(lang, {
            en: "Kelly fraction — where's your sweet spot?",
            vi: "Kelly fraction — điểm ngọt ở đâu?",
            th: "Kelly fraction",
            zh: "Kelly 分数",
            ko: "Kelly 분수",
          })}
        </h1>
        <p className="max-w-2xl text-secondary">
          {tLang(lang, {
            en: "Same bet universe (edge ≥ 5pp), same starting bankroll (100u), 6 different Kelly caps. Lower cap = smoother DD, slower growth. Higher = volatile, faster either direction.",
            vi: "Cùng tập kèo (edge ≥ 5pp), cùng bankroll 100u, 6 cap Kelly khác nhau. Cap thấp = DD mượt, tăng chậm. Cao = biến động mạnh, nhanh cả 2 chiều.",
            th: "Kelly cap ที่ต่างกัน ผลลัพธ์ต่างกัน",
            zh: "不同 Kelly 上限,不同结果",
            ko: "다른 Kelly 상한, 다른 결과",
          })}
        </p>
      </header>

      <section className="card">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
          <line x1={PAD} y1={toY(100)} x2={W - PAD} y2={toY(100)}
                stroke="#555" strokeDasharray="3 3" opacity="0.5" />
          <text x={6} y={toY(100) + 3} fill="#777" fontSize="10">100u</text>
          {good.map(({ cap, r }, i) => (
            <polyline
              key={cap}
              fill="none"
              stroke={palette[i % palette.length]}
              strokeWidth={cap === 0.25 ? 2.5 : 1.5}
              points={r.points.map((p, idx) => `${toX(idx)},${toY(p.bankroll)}`).join(" ")}
              opacity={cap === 0.25 ? 1 : 0.85}
            />
          ))}
        </svg>
      </section>

      <section className="card p-0 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-[10px] uppercase tracking-wide text-muted">
            <tr className="border-b border-border">
              <th className="px-3 py-3 text-left">Cap</th>
              <th className="px-3 py-3 text-right">Bets</th>
              <th className="px-3 py-3 text-right">Peak</th>
              <th className="px-3 py-3 text-right">Final</th>
              <th className="px-3 py-3 text-right">ROI</th>
              <th className="px-3 py-3 text-right">Max DD</th>
            </tr>
          </thead>
          <tbody>
            {good.map(({ cap, r }, i) => (
              <tr key={cap} className="border-t border-border-muted">
                <td className="px-3 py-2 flex items-center gap-2">
                  <span className="inline-block h-2 w-4 rounded" style={{ background: palette[i % palette.length] }} />
                  <span className="font-mono tabular-nums">{(cap * 100).toFixed(0)}%</span>
                </td>
                <td className="px-3 py-2 text-right font-mono tabular-nums">{r.total_bets}</td>
                <td className="px-3 py-2 text-right font-mono tabular-nums">{r.peak_units.toFixed(1)}</td>
                <td className={`px-3 py-2 text-right font-mono tabular-nums ${r.final_units > r.starting_units ? "text-neon" : "text-error"}`}>
                  {r.final_units.toFixed(1)}
                </td>
                <td className={`px-3 py-2 text-right font-mono tabular-nums ${r.roi_percent > 0 ? "text-neon" : "text-error"}`}>
                  {r.roi_percent > 0 ? "+" : ""}{r.roi_percent.toFixed(1)}%
                </td>
                <td className="px-3 py-2 text-right font-mono tabular-nums text-error">
                  -{r.max_drawdown_pct.toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <p className="font-mono text-[11px] uppercase tracking-wide text-muted">
        • Bolder line = 25% fractional Kelly (the conventional default). Most practitioners start there or lower.
      </p>
    </main>
  );
}
