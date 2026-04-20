import { tFor } from "@/lib/i18n-server";
import type { Lang } from "@/lib/i18n";

// Shared by every Phase 15 strategy. Forks KellyChart's rendering + chips
// so new strategies are a 10-line page change, not a chart rewrite.
type Point = { date: string; bets: number; bankroll: number };
type Data = {
  name: string;
  season: string;
  threshold: number;
  starting_units: number;
  final_units: number;
  peak_units: number;
  max_drawdown_pct: number;
  total_bets: number;
  roi_percent: number;
  points: Point[];
};

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

async function fetchSim(
  name: string, season: string, threshold: number, starting: number, league?: string,
): Promise<Data | null> {
  const qs = new URLSearchParams({ name, season, threshold: String(threshold), starting: String(starting) });
  if (league) qs.set("league", league);
  const res = await fetch(`${BASE}/api/stats/strategy-sim?${qs}`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export default async function StrategyChart({
  name,
  title,
  explainer,
  warning,
  season,
  threshold = 0.05,
  starting = 100,
  league,
  lang,
}: {
  name: string;
  title: string;
  explainer: string;
  warning?: string;             // rendered in amber/error when strategy is pedagogical
  season: string;
  threshold?: number;
  starting?: number;
  league?: string;
  lang: Lang;
}) {
  const t = tFor(lang);
  const d = await fetchSim(name, season, threshold, starting, league);
  if (!d || d.points.length < 2) {
    return (
      <section className="card space-y-2">
        <h2 className="font-display font-semibold uppercase tracking-tight">{title}</h2>
        <p className="text-muted text-sm">{t("roi.empty")}</p>
      </section>
    );
  }

  const W = 720, H = 180, PAD = 8;
  const xs = d.points.map((_, i) => i);
  const ys = d.points.map((p) => p.bankroll);
  const minY = Math.min(d.starting_units, ...ys);
  const maxY = Math.max(d.starting_units, d.peak_units, ...ys);
  const rangeY = maxY - minY || 1;
  const rangeX = xs[xs.length - 1] || 1;

  const project = (i: number, y: number) => ({
    x: PAD + (i / rangeX) * (W - 2 * PAD),
    y: H - PAD - ((y - minY) / rangeY) * (H - 2 * PAD),
  });
  const coords = d.points.map((p, i) => ({ ...project(i, p.bankroll), b: p.bankroll }));
  const path = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ");
  const startY = project(0, d.starting_units).y;
  const peakY = project(0, d.peak_units).y;

  const up = d.final_units >= d.starting_units;
  const lineColor = up ? "#E0FF32" : "#FF4D4F";

  return (
    <section className="card space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="font-display font-semibold uppercase tracking-tight">{title}</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 md:gap-6 font-mono text-sm tabular-nums w-full md:w-auto">
          <div>
            <p className="text-xs text-muted">{lang === "vi" ? "Khởi đầu" : "Start"}</p>
            <p className="stat text-base">{d.starting_units.toFixed(0)}u</p>
          </div>
          <div>
            <p className="text-xs text-muted">{lang === "vi" ? "Đỉnh" : "Peak"}</p>
            <p className="stat text-base text-neon">{d.peak_units.toFixed(1)}u</p>
          </div>
          <div>
            <p className="text-xs text-muted">{lang === "vi" ? "Cuối" : "Final"}</p>
            <p className="stat text-base" style={{ color: lineColor }}>{d.final_units.toFixed(1)}u</p>
          </div>
          <div>
            <p className="text-xs text-muted">ROI</p>
            <p className="stat text-base" style={{ color: lineColor }}>
              {d.roi_percent >= 0 ? "+" : ""}{d.roi_percent.toFixed(1)}%
            </p>
          </div>
          <div>
            <p className="text-xs text-muted">{lang === "vi" ? "Drawdown" : "Max DD"}</p>
            <p className="stat text-base text-error">−{d.max_drawdown_pct.toFixed(1)}%</p>
          </div>
        </div>
      </div>

      <p className="text-muted text-sm">{explainer}</p>

      <div className="overflow-x-auto">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full min-w-[360px]" preserveAspectRatio="none">
          <line x1={PAD} x2={W - PAD} y1={startY} y2={startY} stroke="#242424" strokeDasharray="4 4" />
          <line x1={PAD} x2={W - PAD} y1={peakY} y2={peakY} stroke="#3a4a10" strokeDasharray="2 6" />
          <path d={path} fill="none" stroke={lineColor} strokeWidth="2" strokeLinejoin="round" />
          {coords.length > 0 && (
            <circle cx={coords[coords.length - 1].x} cy={coords[coords.length - 1].y} r="4" fill={lineColor} />
          )}
        </svg>
      </div>

      <div className="flex justify-between font-mono text-[10px] text-muted">
        <span>{d.points[0].date}</span>
        <span>{d.total_bets} {lang === "vi" ? "kèo" : "bets"}</span>
        <span>{d.points[d.points.length - 1].date}</span>
      </div>

      {warning && (
        <div className="rounded-xl border border-error/40 bg-high p-4">
          <p className="text-secondary text-sm leading-relaxed">{warning}</p>
        </div>
      )}
    </section>
  );
}
