import type { Lang } from "@/lib/i18n";
import { tLang } from "@/lib/i18n-fallback";

type Radar = {
  player_name: string;
  position: string;
  axes: {
    goals_p90: number;
    xg_p90: number;
    assists_p90: number;
    xa_p90: number;
    key_passes_p90: number;
    g_minus_xg: number;
  };
  raw: Record<string, number>;
};

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

async function fetchRadar(slug: string): Promise<Radar | null> {
  try {
    const res = await fetch(`${BASE}/api/players/${slug}/radar`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return (await res.json()) as Radar;
  } catch {
    return null;
  }
}

export default async function PlayerRadar({ slug, lang }: { slug: string; lang: Lang }) {
  const r = await fetchRadar(slug);
  if (!r) return null;

  // Polygon coordinates on a unit circle, 6 axes. Start at top, clockwise.
  const AXES: Array<{ key: keyof Radar["axes"]; label: string }> = [
    { key: "goals_p90",      label: "G/90" },
    { key: "xg_p90",         label: "xG/90" },
    { key: "assists_p90",    label: "A/90" },
    { key: "xa_p90",         label: "xA/90" },
    { key: "key_passes_p90", label: "KP/90" },
    { key: "g_minus_xg",     label: "G-xG" },
  ];
  const W = 320, H = 320, CX = W / 2, CY = H / 2, R = 100;

  function angleFor(i: number): number {
    return -Math.PI / 2 + (i / AXES.length) * 2 * Math.PI;
  }
  function point(v: number, i: number): [number, number] {
    const a = angleFor(i);
    const rv = R * Math.max(0, Math.min(1, v));
    return [CX + rv * Math.cos(a), CY + rv * Math.sin(a)];
  }
  function axisEnd(i: number): [number, number] {
    const a = angleFor(i);
    return [CX + R * Math.cos(a), CY + R * Math.sin(a)];
  }

  const poly = AXES.map((ax, i) => point(r.axes[ax.key], i).join(",")).join(" ");
  const outerPoly = AXES.map((_, i) => axisEnd(i).join(",")).join(" ");

  return (
    <section className="card space-y-3">
      <div className="flex items-baseline justify-between">
        <h2 className="label">
          {tLang(lang, {
            en: `Player radar · ${r.position}`,
            vi: `Radar cầu thủ · ${r.position}`,
            th: `เรดาร์ผู้เล่น · ${r.position}`,
            zh: `球员雷达 · ${r.position}`,
            ko: `선수 레이더 · ${r.position}`,
          })}
        </h2>
        <p className="font-mono text-[10px] text-muted">vs position 90th percentile</p>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-sm mx-auto">
        {/* Concentric guides at 25/50/75/100 */}
        {[0.25, 0.5, 0.75, 1.0].map((p) => (
          <polygon
            key={p}
            points={AXES.map((_, i) => {
              const a = angleFor(i);
              const rv = R * p;
              return [CX + rv * Math.cos(a), CY + rv * Math.sin(a)].join(",");
            }).join(" ")}
            fill="none"
            stroke="rgba(255,255,255,0.07)"
          />
        ))}
        {/* Axis lines */}
        {AXES.map((_, i) => {
          const [x2, y2] = axisEnd(i);
          return <line key={i} x1={CX} y1={CY} x2={x2} y2={y2} stroke="rgba(255,255,255,0.08)" />;
        })}
        {/* Player polygon */}
        <polygon points={poly} fill="rgba(224,255,50,0.25)" stroke="#E0FF32" strokeWidth="2" />
        {/* Labels */}
        {AXES.map((ax, i) => {
          const a = angleFor(i);
          const lx = CX + (R + 20) * Math.cos(a);
          const ly = CY + (R + 20) * Math.sin(a);
          return (
            <text
              key={ax.key}
              x={lx}
              y={ly}
              fill="#999"
              fontSize="10"
              textAnchor="middle"
              dominantBaseline="middle"
            >
              {ax.label}
            </text>
          );
        })}
      </svg>
      <p className="font-mono text-[11px] text-muted text-center">
        {r.raw.goals} G · {r.raw.xg.toFixed(1)} xG · {r.raw.assists} A · {r.raw.games} games
      </p>
    </section>
  );
}
