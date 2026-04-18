import type { Lang } from "@/lib/i18n";
import { tFor } from "@/lib/i18n-server";
import { colorFor } from "@/lib/team-colors";

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

type Trajectory = {
  slug: string;
  season: string;
  points: Point[];
};

async function fetchTrajectory(slug: string, season: string): Promise<Trajectory | null> {
  const res = await fetch(`${BASE}/api/teams/${slug}/trajectory?season=${season}`, {
    cache: "no-store",
  });
  if (!res.ok) return null;
  return res.json();
}

// Rolling mean over a trailing window (first k-1 points use shorter windows).
function rolling(xs: number[], window: number): number[] {
  const out: number[] = [];
  for (let i = 0; i < xs.length; i++) {
    const lo = Math.max(0, i - window + 1);
    const slice = xs.slice(lo, i + 1);
    out.push(slice.reduce((a, b) => a + b, 0) / slice.length);
  }
  return out;
}

export default async function SeasonTrajectoryChart({
  slug,
  season,
  lang,
}: {
  slug: string;
  season: string;
  lang: Lang;
}) {
  const t = tFor(lang);
  const d = await fetchTrajectory(slug, season);
  if (!d || d.points.length < 3) return null;

  const forRaw = d.points.map((p) => p.xg_for);
  const agaRaw = d.points.map((p) => p.xg_against);
  const forRoll = rolling(forRaw, 5);
  const agaRoll = rolling(agaRaw, 5);

  const W = 720;
  const H = 180;
  const PAD = 12;
  const maxY = Math.max(3, ...forRaw, ...agaRaw) * 1.05;
  const toX = (i: number) =>
    PAD + (i / Math.max(1, d.points.length - 1)) * (W - 2 * PAD);
  const toY = (v: number) => H - PAD - (v / maxY) * (H - 2 * PAD);

  const pathFor = forRoll.map((v, i) => `${i === 0 ? "M" : "L"}${toX(i).toFixed(1)},${toY(v).toFixed(1)}`).join(" ");
  const pathAga = agaRoll.map((v, i) => `${i === 0 ? "M" : "L"}${toX(i).toFixed(1)},${toY(v).toFixed(1)}`).join(" ");

  const teamColor = colorFor(slug);

  const forAvg = forRoll[forRoll.length - 1];
  const agaAvg = agaRoll[agaRoll.length - 1];

  return (
    <section className="card space-y-3">
      <div className="flex items-baseline justify-between">
        <h2 className="font-display font-semibold uppercase tracking-tight">
          {t("team.trajectoryTitle")}
        </h2>
        <span className="font-mono text-xs text-muted">{d.points.length} {t("team.trajectoryMatches")}</span>
      </div>

      <div className="overflow-x-auto">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full min-w-[420px]" preserveAspectRatio="none">
          {[1, 2].map((tick) => (
            <line
              key={tick}
              x1={PAD}
              x2={W - PAD}
              y1={toY(tick)}
              y2={toY(tick)}
              stroke="#242424"
              strokeDasharray="3 4"
            />
          ))}
          <path d={pathAga} fill="none" stroke="#FF4D4F" strokeWidth="1.5" strokeOpacity="0.75" />
          <path d={pathFor} fill="none" stroke="#E0FF32" strokeWidth="2.5" />
          {/* Latest-value dots */}
          {forRoll.length > 0 && (
            <circle
              cx={toX(forRoll.length - 1)}
              cy={toY(forRoll[forRoll.length - 1])}
              r="4"
              fill="#E0FF32"
            />
          )}
          {agaRoll.length > 0 && (
            <circle
              cx={toX(agaRoll.length - 1)}
              cy={toY(agaRoll[agaRoll.length - 1])}
              r="3"
              fill="#FF4D4F"
            />
          )}
        </svg>
      </div>

      <div className="flex items-center justify-between font-mono text-[11px] text-muted">
        <span className="flex items-center gap-2">
          <span className="inline-block w-3 h-[3px] bg-neon rounded-full" />
          {t("team.trajectoryXgFor", { value: forAvg.toFixed(2) })}
        </span>
        <span className="flex items-center gap-2" style={{ color: teamColor }}>
          {d.points.length > 0 &&
            `${d.points[0].kickoff_time.slice(0, 10)} → ${d.points[d.points.length - 1].kickoff_time.slice(0, 10)}`}
        </span>
        <span className="flex items-center gap-2">
          <span className="inline-block w-3 h-[3px] bg-error rounded-full" />
          {t("team.trajectoryXgAgainst", { value: agaAvg.toFixed(2) })}
        </span>
      </div>

      <p className="text-muted text-xs leading-relaxed">
        {t("team.trajectoryFooter")}
      </p>
    </section>
  );
}
