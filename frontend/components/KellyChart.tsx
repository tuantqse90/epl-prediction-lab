import { tFor } from "@/lib/i18n-server";
import type { Lang } from "@/lib/i18n";

type KellyPoint = { date: string; bets: number; bankroll: number };
type KellyData = {
  season: string;
  threshold: number;
  cap: number;
  starting_units: number;
  final_units: number;
  peak_units: number;
  max_drawdown_pct: number;
  total_bets: number;
  roi_percent: number;
  points: KellyPoint[];
};

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

async function fetchKelly(
  season: string,
  threshold: number,
  cap: number,
  starting: number,
  league?: string,
): Promise<KellyData | null> {
  const qs = new URLSearchParams({
    season,
    threshold: String(threshold),
    cap: String(cap),
    starting: String(starting),
  });
  if (league) qs.set("league", league);
  const res = await fetch(`${BASE}/api/stats/roi/kelly?${qs}`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export default async function KellyChart({
  season,
  threshold = 0.05,
  cap = 0.25,
  starting = 100,
  league,
  lang,
}: {
  season: string;
  threshold?: number;
  cap?: number;
  starting?: number;
  league?: string;
  lang: Lang;
}) {
  const t = tFor(lang);
  const d = await fetchKelly(season, threshold, cap, starting, league);

  if (!d || d.points.length < 2) {
    return (
      <section className="card space-y-2">
        <h2 className="font-display font-semibold uppercase tracking-tight">
          {lang === "vi" ? "Bankroll ảo · Kelly" : "Virtual bankroll · Kelly"}
        </h2>
        <p className="text-muted text-sm">{t("roi.empty")}</p>
      </section>
    );
  }

  const W = 720;
  const H = 180;
  const PAD = 8;

  // Bankroll curve (real line).
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

  const coords = d.points.map((p, i) => ({
    ...project(i, p.bankroll),
    bankroll: p.bankroll,
  }));

  const path = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ");
  const startY = project(0, d.starting_units).y;
  const peakY = project(0, d.peak_units).y;

  const up = d.final_units >= d.starting_units;
  const lineColor = up ? "#E0FF32" : "#FF4D4F";

  // Drawdown shade: from the peak line to the bankroll line at each point
  // where bankroll < peak_units. Render as a filled area in red/20%.
  const drawdownArea = [
    ...coords.filter((_, i) => d.points[i].bankroll < d.peak_units).map((c) => `${c.x.toFixed(1)},${c.y.toFixed(1)}`),
    ...coords
      .filter((_, i) => d.points[i].bankroll < d.peak_units)
      .reverse()
      .map((c) => `${c.x.toFixed(1)},${peakY.toFixed(1)}`),
  ];
  const drawdownPoly = drawdownArea.length > 0 ? drawdownArea.join(" ") : null;

  const thresholdPP = `${Math.round(threshold * 100)}`;

  return (
    <section className="card space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="font-display font-semibold uppercase tracking-tight">
          {lang === "vi" ? "Bankroll ảo · Kelly" : "Virtual bankroll · Kelly"}
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 md:gap-6 font-mono text-sm tabular-nums w-full md:w-auto">
          <div>
            <p className="text-xs text-muted">{lang === "vi" ? "Khởi đầu" : "Starting"}</p>
            <p className="stat text-base">{d.starting_units.toFixed(0)}u</p>
          </div>
          <div>
            <p className="text-xs text-muted">{lang === "vi" ? "Đỉnh" : "Peak"}</p>
            <p className="stat text-base text-neon">{d.peak_units.toFixed(1)}u</p>
          </div>
          <div>
            <p className="text-xs text-muted">{lang === "vi" ? "Cuối" : "Final"}</p>
            <p className="stat text-base" style={{ color: lineColor }}>
              {d.final_units.toFixed(1)}u
            </p>
          </div>
          <div>
            <p className="text-xs text-muted">ROI</p>
            <p className="stat text-base" style={{ color: lineColor }}>
              {d.roi_percent >= 0 ? "+" : ""}
              {d.roi_percent.toFixed(1)}%
            </p>
          </div>
          <div>
            <p className="text-xs text-muted">{lang === "vi" ? "Drawdown" : "Max DD"}</p>
            <p className="stat text-base text-error">−{d.max_drawdown_pct.toFixed(1)}%</p>
          </div>
        </div>
      </div>

      <p className="text-muted text-sm">
        {lang === "vi"
          ? `Mỗi kèo edge ≥ ${thresholdPP}pp được stake bằng fractional Kelly capped ${Math.round(d.cap * 100)}% bankroll, compounding theo thời gian. Bắt đầu với ${d.starting_units}u.`
          : `Each ≥${thresholdPP}pp-edge bet is staked via fractional Kelly capped at ${Math.round(d.cap * 100)}% of the current bankroll, compounding over time. Starting balance ${d.starting_units}u.`}
      </p>

      <div className="overflow-x-auto">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full min-w-[360px]" preserveAspectRatio="none">
          {/* starting-balance reference line */}
          <line
            x1={PAD}
            x2={W - PAD}
            y1={startY}
            y2={startY}
            stroke="#242424"
            strokeDasharray="4 4"
          />
          {/* peak reference line */}
          <line
            x1={PAD}
            x2={W - PAD}
            y1={peakY}
            y2={peakY}
            stroke="#3a4a10"
            strokeDasharray="2 6"
          />
          {/* drawdown shaded region (peak → bankroll where below peak) */}
          {drawdownPoly && (
            <polygon points={drawdownPoly} fill="rgba(255, 77, 79, 0.18)" />
          )}
          {/* bankroll curve */}
          <path d={path} fill="none" stroke={lineColor} strokeWidth="2" strokeLinejoin="round" />
          {/* current endpoint marker */}
          {coords.length > 0 && (
            <circle
              cx={coords[coords.length - 1].x}
              cy={coords[coords.length - 1].y}
              r="4"
              fill={lineColor}
            />
          )}
        </svg>
      </div>

      <div className="flex justify-between font-mono text-[10px] text-muted">
        <span>{d.points[0].date}</span>
        <span>
          {d.total_bets} {lang === "vi" ? "kèo" : "bets"}
        </span>
        <span>{d.points[d.points.length - 1].date}</span>
      </div>

      {d.max_drawdown_pct > 95 && (
        <div className="rounded-xl border border-error/40 bg-high p-4 space-y-2">
          <p className="font-mono text-[10px] uppercase tracking-wide text-error">
            {lang === "vi" ? "Bankroll bị sập" : "Bankroll wiped"}
          </p>
          <p className="text-secondary text-sm leading-relaxed">
            {lang === "vi"
              ? `Ở ngưỡng ${thresholdPP}pp, Kelly ${Math.round(d.cap * 100)}% làm bankroll về ~0 — nghĩa là cái "edge" model flag ở mức này không phải edge thật mà là noise + adverse selection. Flat 1u cũng lỗ (so trên page này), Kelly chỉ làm mất nhanh hơn theo cấp số nhân.`
              : `At a ${thresholdPP}pp threshold, ${Math.round(d.cap * 100)}% Kelly reduces the bankroll to ~0 — the "edges" flagged at this level are noise + adverse selection, not real edges. Flat 1u is also losing (compare mode on this page); Kelly just magnifies the loss exponentially.`}
          </p>
          <p className="text-secondary text-sm leading-relaxed">
            {lang === "vi"
              ? "Trong thực tế: raise threshold, dùng quarter-Kelly (cap ≤ 6%), hoặc chỉ đánh giải có ROI dương trong /roi/by-league."
              : "Fixes to try: raise the edge threshold, use quarter-Kelly (cap ≤ 6%), or bet only on leagues with positive recent ROI at /roi/by-league."}
          </p>
        </div>
      )}

      <p className="font-mono text-[10px] uppercase tracking-wide text-muted">
        {lang === "vi"
          ? "Không phải stake thật — mô phỏng trên kèo lịch sử. Không custody, không đặt cược hộ."
          : "Simulated on historical value bets only — no custody, no stakes placed."}
      </p>
    </section>
  );
}
