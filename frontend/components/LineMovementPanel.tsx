import type { Lang } from "@/lib/i18n";
import { tLang } from "@/lib/i18n-fallback";

type Snapshot = {
  captured_at: string;
  source: string;
  odds_home: number;
  odds_draw: number;
  odds_away: number;
};

type DivergenceFlag = {
  outcome: "HOME" | "DRAW" | "AWAY";
  sharp_prob: number;
  square_prob: number;
  divergence_pp: number;
};

type LineMovement = {
  match_id: number;
  total_snapshots: number;
  series: Snapshot[];
  sharp_divergence: DivergenceFlag[];
};

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

async function fetchData(matchId: number): Promise<LineMovement | null> {
  try {
    const res = await fetch(`${BASE}/api/matches/${matchId}/line-movement`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) return null;
    return (await res.json()) as LineMovement;
  } catch {
    return null;
  }
}

function devig(o: Snapshot): [number, number, number] {
  const ih = 1 / o.odds_home, id = 1 / o.odds_draw, ia = 1 / o.odds_away;
  const total = ih + id + ia;
  return [ih / total, id / total, ia / total];
}

export default async function LineMovementPanel({
  matchId,
  lang,
  homeShort,
  awayShort,
}: {
  matchId: number;
  lang: Lang;
  homeShort: string;
  awayShort: string;
}) {
  const data = await fetchData(matchId);
  if (!data || data.total_snapshots < 2) return null;

  // Group by source, keep only the most-sampled 6 sources to avoid visual
  // noise; include Pinnacle if present.
  const bySource: Record<string, Snapshot[]> = {};
  for (const s of data.series) {
    bySource[s.source] ||= [];
    bySource[s.source].push(s);
  }
  const ranked = Object.entries(bySource)
    .sort((a, b) => b[1].length - a[1].length);
  const chosen: [string, Snapshot[]][] = [];
  const pin = ranked.find(([k]) => k.toLowerCase().includes("pinnacle"));
  if (pin) chosen.push(pin);
  for (const [k, arr] of ranked) {
    if (k === pin?.[0]) continue;
    if (chosen.length >= 6) break;
    chosen.push([k, arr]);
  }

  const allTimes = data.series.map((s) => new Date(s.captured_at).getTime());
  const minT = Math.min(...allTimes);
  const maxT = Math.max(...allTimes);
  const range = maxT - minT || 1;

  const W = 640, H = 240, PAD = 30;
  const toX = (t: number) =>
    PAD + ((t - minT) / range) * (W - 2 * PAD);
  // Plot home-win devigged prob for each source.
  const toY = (p: number) => H - PAD - p * (H - 2 * PAD);

  const palette = [
    "#E0FF32", "#4ea0ff", "#ff72a6", "#ffc247",
    "#9cff9c", "#b888ff", "#ff9c72", "#72e0ff",
  ];

  return (
    <section className="card space-y-4">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <h2 className="label">
          {tLang(lang, {
            en: "Line movement · home-win devigged",
            vi: "Biến động dòng · Home win devigged",
            th: "การเคลื่อนไหวราคา · Home win devigged",
            zh: "赔率走势 · 主胜 devigged",
            ko: "라인 무브먼트 · Home win devigged",
          })}
        </h2>
        <p className="font-mono text-[11px] text-muted">
          {data.total_snapshots} {tLang(lang, { en: "snapshots", vi: "bản chụp", th: "สแน็ปช็อต", zh: "快照", ko: "스냅샷" })}
        </p>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
        {/* Horizontal gridlines at 25/50/75 */}
        {[0.25, 0.5, 0.75].map((p) => (
          <g key={p}>
            <line x1={PAD} x2={W - PAD} y1={toY(p)} y2={toY(p)} stroke="rgba(255,255,255,0.05)" />
            <text x={6} y={toY(p) + 3} fill="#777" fontSize="10">{Math.round(p * 100)}%</text>
          </g>
        ))}
        {chosen.map(([src, arr], i) => {
          const points = arr
            .map((s) => `${toX(new Date(s.captured_at).getTime())},${toY(devig(s)[0])}`)
            .join(" ");
          return (
            <g key={src}>
              <polyline
                fill="none"
                stroke={palette[i % palette.length]}
                strokeWidth={src.toLowerCase().includes("pinnacle") ? 2.5 : 1.5}
                points={points}
                opacity={src.toLowerCase().includes("pinnacle") ? 1 : 0.75}
              />
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="flex flex-wrap gap-3">
        {chosen.map(([src], i) => (
          <span key={src} className="inline-flex items-center gap-1.5 font-mono text-[11px]">
            <span
              aria-hidden
              className="h-2 w-4 rounded"
              style={{ background: palette[i % palette.length] }}
            />
            {src.replace(/^(af:|odds-api:)/, "")}
          </span>
        ))}
      </div>

      {/* Sharp vs square divergence callout */}
      {data.sharp_divergence.length > 0 && (
        <div className="rounded bg-warning/10 border border-warning/30 p-3 space-y-2">
          <p className="font-mono text-[10px] uppercase tracking-wide text-warning">
            {tLang(lang, {
              en: "Sharp vs square divergence",
              vi: "Sharp vs square phân kỳ",
              th: "Sharp vs square แตกต่าง",
              zh: "Sharp vs Square 分歧",
              ko: "Sharp vs Square 차이",
            })}
          </p>
          {data.sharp_divergence.map((d) => {
            const label =
              d.outcome === "HOME" ? homeShort
              : d.outcome === "AWAY" ? awayShort
              : "Draw";
            return (
              <p key={d.outcome} className="text-sm">
                <span className="font-display font-semibold">{label}</span>{" "}
                <span className="text-muted">— </span>
                Pinnacle {(d.sharp_prob * 100).toFixed(1)}% · retail {(d.square_prob * 100).toFixed(1)}% ·
                <span className={d.divergence_pp > 0 ? " text-neon" : " text-error"}>
                  {" "}{d.divergence_pp > 0 ? "+" : ""}{d.divergence_pp.toFixed(1)}pp
                </span>
              </p>
            );
          })}
          <p className="font-mono text-[10px] text-muted">
            {tLang(lang, {
              en: "Sharp side often = where 'smart money' is landing; retail = public perception",
              vi: "Sharp = nơi 'tiền thông minh' đang vào; retail = public",
              th: "Sharp = เงินของเซียน, retail = เงินประชาชน",
              zh: "Sharp = 专业资金, retail = 大众资金",
              ko: "Sharp = 스마트 머니, retail = 대중",
            })}
          </p>
        </div>
      )}
    </section>
  );
}
