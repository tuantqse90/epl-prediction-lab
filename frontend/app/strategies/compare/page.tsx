import type { Metadata } from "next";
import Link from "next/link";

import { getLang, getLeagueSlug, leagueForApi, tFor } from "@/lib/i18n-server";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Strategy compare — four sizings on the same bets · predictor.nullshift.sh",
  description:
    "Four named staking strategies on the same season + same bet universe. " +
    "Watch Martingale ruin vs high-confidence filter survive on real data.",
  alternates: { canonical: "/strategies/compare" },
};

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

const STRATEGIES = [
  { slug: "high-confidence", label_en: "High-confidence", label_vi: "Lọc tự tin", color: "#E0FF32" },
  { slug: "value-ladder",    label_en: "Value ladder",    label_vi: "Bậc thang",   color: "#60B0FF" },
  { slug: "martingale",      label_en: "Martingale",      label_vi: "Martingale",  color: "#FF4D4F" },
  { slug: "favorite-fade",   label_en: "Favorite fade",   label_vi: "Ngược model", color: "#FFB020" },
] as const;

type Point = { date: string; bets: number; bankroll: number };
type StrategyData = {
  name: string;
  starting_units: number;
  final_units: number;
  peak_units: number;
  max_drawdown_pct: number;
  total_bets: number;
  roi_percent: number;
  points: Point[];
};

async function fetchOne(name: string, threshold: number, league?: string): Promise<StrategyData | null> {
  const qs = new URLSearchParams({ name, threshold: String(threshold), starting: "100", season: "2025-26" });
  if (league) qs.set("league", league);
  const r = await fetch(`${BASE}/api/stats/strategy-sim?${qs}`, { cache: "no-store" });
  if (!r.ok) return null;
  return r.json();
}

const THRESHOLDS = [0.03, 0.05, 0.07, 0.10] as const;

export default async function StrategyComparePage({
  searchParams,
}: {
  searchParams: Promise<{ threshold?: string }>;
}) {
  const sp = await searchParams;
  const rawThreshold = Number(sp.threshold ?? "0.05");
  const threshold = (THRESHOLDS as readonly number[]).includes(rawThreshold) ? rawThreshold : 0.05;

  const lang = await getLang();
  const t = tFor(lang);
  const league = await getLeagueSlug();
  const leagueParam = leagueForApi(league);

  const results = await Promise.all(
    STRATEGIES.map(async (s) => ({ meta: s, data: await fetchOne(s.slug, threshold, leagueParam) })),
  );

  // All curves share one x-axis (bet index) and one y-axis (bankroll units).
  const W = 760, H = 260, PAD = 10;
  const maxBets = Math.max(...results.map((r) => r.data?.total_bets ?? 0), 1);
  const allUnits = results.flatMap((r) => r.data?.points.map((p) => p.bankroll) ?? [100]);
  const yMin = Math.min(0, ...allUnits);
  const yMax = Math.max(100, ...allUnits);
  const rangeY = yMax - yMin || 1;

  const project = (idx: number, bankroll: number) => ({
    x: PAD + (idx / maxBets) * (W - 2 * PAD),
    y: H - PAD - ((bankroll - yMin) / rangeY) * (H - 2 * PAD),
  });
  const startY = H - PAD - ((100 - yMin) / rangeY) * (H - 2 * PAD);

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-8">
      <Link href="/strategies" className="btn-ghost text-sm">{t("common.back")}</Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">
          {lang === "vi" ? "So sánh · cùng data, 4 cách stake" : "Compare · same data, 4 sizing rules"}
        </p>
        <h1 className="headline-section">
          {lang === "vi" ? "Chiến thuật nào sống sót trên data thật?" : "Which strategy actually survives on real data?"}
        </h1>
        <p className="max-w-3xl text-secondary">
          {lang === "vi"
            ? "Cùng tập kèo 2025-26, cùng ngưỡng edge, 4 cách size stake khác nhau. Bankroll bắt đầu 100u cho mỗi chiến thuật. Đường nào sống tới cuối là chiến thuật đáng học; đường nào rơi thẳng xuống 0 là điều user NÊN TRÁNH."
            : "Same 2025-26 value-bet universe, same edge threshold, four different staking rules. Bankroll starts at 100u for each. The lines that survive are the patterns to learn; the ones that plummet to zero are exactly what to avoid."}
        </p>
      </header>

      <nav className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[10px] uppercase tracking-wide text-muted mr-1">edge</span>
        {THRESHOLDS.map((thr) => (
          <Link
            key={thr}
            href={`/strategies/compare?threshold=${thr}`}
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
      </nav>

      <section className="card space-y-4">
        <h2 className="font-display font-semibold uppercase tracking-tight">
          {lang === "vi" ? "4 đường bankroll trên 1 biểu đồ" : "4 bankroll curves on one chart"}
        </h2>

        <div className="flex flex-wrap gap-x-5 gap-y-1 font-mono text-[10px] uppercase tracking-wide">
          {results.map(({ meta, data }) => (
            <span key={meta.slug} className="inline-flex items-center gap-1.5">
              <span className="w-3 h-0.5" style={{ background: meta.color }} />
              <span className="text-secondary">{lang === "vi" ? meta.label_vi : meta.label_en}</span>
              <span className="text-muted">{data ? `· ${data.roi_percent >= 0 ? "+" : ""}${data.roi_percent.toFixed(0)}%` : ""}</span>
            </span>
          ))}
        </div>

        <div className="overflow-x-auto">
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full min-w-[360px]" preserveAspectRatio="none">
            {/* starting reference at 100u */}
            <line x1={PAD} x2={W - PAD} y1={startY} y2={startY} stroke="#242424" strokeDasharray="4 4" />

            {results.map(({ meta, data }) => {
              if (!data || data.points.length < 2) return null;
              const coords = data.points.map((p, i) => project(i, p.bankroll));
              const path = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ");
              return (
                <g key={meta.slug}>
                  <path d={path} fill="none" stroke={meta.color} strokeWidth="2" strokeLinejoin="round" opacity={0.85} />
                  {coords.length > 0 && (
                    <circle cx={coords[coords.length - 1].x} cy={coords[coords.length - 1].y} r="3.5" fill={meta.color} />
                  )}
                </g>
              );
            })}
          </svg>
        </div>
      </section>

      <section className="card">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-[10px] uppercase tracking-wide text-muted">
              <tr className="text-left">
                <th className="py-2 pr-4">{lang === "vi" ? "Chiến thuật" : "Strategy"}</th>
                <th className="py-2 pr-4 text-right">{lang === "vi" ? "Kèo" : "Bets"}</th>
                <th className="py-2 pr-4 text-right">{lang === "vi" ? "Đỉnh" : "Peak"}</th>
                <th className="py-2 pr-4 text-right">{lang === "vi" ? "Cuối" : "Final"}</th>
                <th className="py-2 pr-4 text-right">ROI</th>
                <th className="py-2 pr-4 text-right">Max DD</th>
              </tr>
            </thead>
            <tbody>
              {results.map(({ meta, data }) => {
                if (!data) return (
                  <tr key={meta.slug} className="border-t border-border-muted">
                    <td className="py-2 pr-4 font-mono text-xs">{lang === "vi" ? meta.label_vi : meta.label_en}</td>
                    <td colSpan={5} className="py-2 text-muted">{lang === "vi" ? "không có dữ liệu" : "no data"}</td>
                  </tr>
                );
                const up = data.final_units >= data.starting_units;
                const color = up ? "text-neon" : "text-error";
                return (
                  <tr key={meta.slug} className="border-t border-border-muted">
                    <td className="py-2 pr-4 font-mono text-xs text-secondary">
                      <span className="inline-block w-2 h-2 mr-2 align-middle" style={{ background: meta.color }} />
                      <Link href={`/strategies?name=${meta.slug}&threshold=${threshold}`} className="hover:text-neon">
                        {lang === "vi" ? meta.label_vi : meta.label_en}
                      </Link>
                    </td>
                    <td className="py-2 pr-4 text-right font-mono tabular-nums">{data.total_bets}</td>
                    <td className="py-2 pr-4 text-right font-mono tabular-nums text-neon">{data.peak_units.toFixed(1)}u</td>
                    <td className={"py-2 pr-4 text-right font-mono tabular-nums " + color}>{data.final_units.toFixed(1)}u</td>
                    <td className={"py-2 pr-4 text-right font-mono tabular-nums " + color}>
                      {data.roi_percent >= 0 ? "+" : ""}{data.roi_percent.toFixed(1)}%
                    </td>
                    <td className="py-2 pr-4 text-right font-mono tabular-nums text-error">−{data.max_drawdown_pct.toFixed(1)}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="font-mono text-[11px] uppercase tracking-wide text-muted space-y-1">
        <p>
          {lang === "vi"
            ? "• High-confidence filter: stake flat 1u khi model_prob ≥ 60% VÀ edge ≥ ngưỡng"
            : "• High-confidence: flat 1u when model_prob ≥ 60% AND edge ≥ threshold"}
        </p>
        <p>
          {lang === "vi"
            ? "• Value ladder: stake 1u × (edge_pp / 5), cap 5u — không compound"
            : "• Value ladder: stake = 1u × (edge_pp / 5), cap 5u — no compounding"}
        </p>
        <p>
          {lang === "vi"
            ? "• Martingale: double sau loss, reset sau win — educational, sẽ cháy"
            : "• Martingale: double after loss, reset on win — educational ruin"}
        </p>
        <p>
          {lang === "vi"
            ? "• Favorite fade: đặt NGƯỢC model → nếu strategy này LÃI nghĩa là model ko có edge thật"
            : "• Favorite fade: bet AGAINST model → if this is profitable, model has no real signal"}
        </p>
      </section>
    </main>
  );
}
