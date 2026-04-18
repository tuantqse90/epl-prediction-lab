import { tFor } from "@/lib/i18n-server";
import type { Lang } from "@/lib/i18n";

type RoiPoint = { date: string; bets: number; cumulative_pnl: number };
type RoiData = {
  season: string;
  threshold: number;
  total_bets: number;
  total_pnl: number;
  roi_percent: number;
  points: RoiPoint[];
};

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

async function fetchRoi(season: string, threshold: number): Promise<RoiData | null> {
  const res = await fetch(
    `${BASE}/api/stats/roi?season=${encodeURIComponent(season)}&threshold=${threshold}`,
    { cache: "no-store" },
  );
  if (!res.ok) return null;
  return res.json();
}

export default async function RoiChart({
  season,
  threshold = 0.05,
  lang,
}: {
  season: string;
  threshold?: number;
  lang: Lang;
}) {
  const t = tFor(lang);
  const d = await fetchRoi(season, threshold);
  if (!d || d.points.length < 2) {
    return (
      <section className="card space-y-2">
        <h2 className="font-display font-semibold uppercase tracking-tight">{t("roi.title")}</h2>
        <p className="text-muted text-sm">{t("roi.empty")}</p>
      </section>
    );
  }

  const W = 720;
  const H = 160;
  const PAD = 8;
  const xs = d.points.map((_, i) => i);
  const ys = d.points.map((p) => p.cumulative_pnl);
  const minY = Math.min(0, ...ys);
  const maxY = Math.max(0, ...ys);
  const rangeY = maxY - minY || 1;
  const rangeX = xs[xs.length - 1] || 1;

  const coords = d.points.map((p, i) => ({
    x: PAD + (i / rangeX) * (W - 2 * PAD),
    y: H - PAD - ((p.cumulative_pnl - minY) / rangeY) * (H - 2 * PAD),
    pnl: p.cumulative_pnl,
    bets: p.bets,
    date: p.date,
  }));

  const path = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ");
  const zeroY = H - PAD - ((0 - minY) / rangeY) * (H - 2 * PAD);
  const lastPnl = d.total_pnl;
  const pnlColor = lastPnl >= 0 ? "#E0FF32" : "#FF4D4F";

  const thresholdPP = `${Math.round(threshold * 100)}`;
  return (
    <section className="card space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="font-display font-semibold uppercase tracking-tight">{t("roi.title")}</h2>
        <div className="flex gap-6 font-mono text-sm tabular-nums">
          <div>
            <p className="text-xs text-muted">{t("roi.totalBets")}</p>
            <p className="stat text-base">{d.total_bets}</p>
          </div>
          <div>
            <p className="text-xs text-muted">{t("roi.totalPnl")}</p>
            <p className="stat text-base" style={{ color: pnlColor }}>
              {lastPnl >= 0 ? "+" : ""}
              {lastPnl.toFixed(2)}u
            </p>
          </div>
          <div>
            <p className="text-xs text-muted">{t("roi.roi")}</p>
            <p className="stat text-base" style={{ color: pnlColor }}>
              {d.roi_percent >= 0 ? "+" : ""}
              {d.roi_percent.toFixed(1)}%
            </p>
          </div>
        </div>
      </div>
      <p className="text-muted text-sm">{t("roi.subhead", { threshold: thresholdPP })}</p>

      <div className="overflow-x-auto">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full min-w-[360px]" preserveAspectRatio="none">
          <line
            x1={PAD}
            x2={W - PAD}
            y1={zeroY}
            y2={zeroY}
            stroke="#242424"
            strokeDasharray="4 4"
          />
          <path d={path} fill="none" stroke={pnlColor} strokeWidth="2" strokeLinejoin="round" />
          {coords.length > 0 && (
            <circle cx={coords[coords.length - 1].x} cy={coords[coords.length - 1].y} r="4" fill={pnlColor} />
          )}
        </svg>
      </div>

      <div className="flex justify-between font-mono text-[10px] text-muted">
        <span>{d.points[0].date}</span>
        <span>{d.points[d.points.length - 1].date}</span>
      </div>
    </section>
  );
}
