import type { Lang } from "@/lib/i18n";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type Point = {
  kickoff_time: string;
  xg_for: number;
  xg_against: number;
  goals_for: number;
  goals_against: number;
  is_home: boolean;
  opponent_short: string;
};

async function fetchLast5(slug: string, season: string): Promise<Point[]> {
  try {
    const res = await fetch(`${BASE}/api/teams/${slug}/trajectory?season=${season}`, { cache: "no-store" });
    if (!res.ok) return [];
    const body: { points: Point[] } = await res.json();
    return body.points.slice(-5);
  } catch {
    return [];
  }
}

function Bar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <span className="flex-1 h-2 rounded bg-high overflow-hidden">
      <span className="block h-full" style={{ width: `${pct}%`, backgroundColor: color }} />
    </span>
  );
}

function TeamCol({
  label,
  points,
}: {
  label: string;
  points: Point[];
}) {
  if (points.length === 0) {
    return (
      <div>
        <h3 className="label mb-2">{label}</h3>
        <p className="text-muted text-sm">No recent xG data.</p>
      </div>
    );
  }
  const maxXg = Math.max(
    1.0,
    ...points.flatMap((p) => [p.xg_for, p.xg_against]),
  );
  return (
    <div className="space-y-2 min-w-0">
      <h3 className="label">{label}</h3>
      <div className="space-y-1.5">
        {points.map((p) => {
          const delta = p.xg_for - p.xg_against;
          return (
            <div key={p.kickoff_time} className="flex items-center gap-2 font-mono text-xs">
              <span className="w-10 shrink-0 text-muted truncate">
                {p.is_home ? "vs" : "@"} {p.opponent_short}
              </span>
              <Bar value={p.xg_for} max={maxXg} color="#E0FF32" />
              <span className="w-10 text-right tabular-nums text-neon">{p.xg_for.toFixed(1)}</span>
              <Bar value={p.xg_against} max={maxXg} color="#FF4D4F" />
              <span className="w-10 text-right tabular-nums text-error">{p.xg_against.toFixed(1)}</span>
              <span
                className={
                  "w-10 text-right tabular-nums " +
                  (delta > 0.5 ? "text-neon" : delta < -0.5 ? "text-error" : "text-muted")
                }
              >
                {delta > 0 ? "+" : ""}{delta.toFixed(1)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default async function XgMomentum({
  homeSlug,
  homeShort,
  awaySlug,
  awayShort,
  season,
  lang,
}: {
  homeSlug: string;
  homeShort: string;
  awaySlug: string;
  awayShort: string;
  season: string;
  lang: Lang;
}) {
  const [hp, ap] = await Promise.all([
    fetchLast5(homeSlug, season),
    fetchLast5(awaySlug, season),
  ]);
  if (hp.length === 0 && ap.length === 0) return null;

  const title = lang === "vi" ? "Phong độ xG (5 trận gần nhất)" : "xG momentum (last 5)";
  const sub =
    lang === "vi"
      ? "Neon = xG tạo ra · Đỏ = xG cho phép · Δ = chênh lệch"
      : "Neon = xG for · Red = xG against · Δ = delta";

  return (
    <section className="card space-y-4">
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <h2 className="label">{title}</h2>
        <p className="text-[11px] text-muted">{sub}</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <TeamCol label={homeShort} points={hp} />
        <TeamCol label={awayShort} points={ap} />
      </div>
    </section>
  );
}
