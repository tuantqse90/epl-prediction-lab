import Link from "next/link";

import TeamLogo from "@/components/TeamLogo";
import type { Lang } from "@/lib/i18n";
import { tLang } from "@/lib/i18n-fallback";

type MatchOfWeek = {
  match_id: number;
  league_code: string | null;
  kickoff_time: string;
  home_short: string;
  away_short: string;
  home_slug: string;
  away_slug: string;
  pick: "H" | "D" | "A";
  confidence: number;
  best_odds: number;
  edge_pp: number;
};

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

async function fetchData(): Promise<MatchOfWeek | null> {
  try {
    const res = await fetch(`${BASE}/api/stats/match-of-week`, { next: { revalidate: 1800 } });
    if (!res.ok) return null;
    const body = await res.json();
    return body as MatchOfWeek | null;
  } catch {
    return null;
  }
}

export default async function MatchOfWeekCard({ lang }: { lang: Lang }) {
  const m = await fetchData();
  if (!m) return null;
  const pickLabel =
    m.pick === "H" ? m.home_short : m.pick === "A" ? m.away_short : "Draw";

  return (
    <Link
      href={`/match/${m.match_id}`}
      className="card relative overflow-hidden flex flex-col gap-3 hover:border-neon transition-colors"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-30"
        style={{
          background:
            "radial-gradient(circle at 20% 30%, rgba(224,255,50,0.25), transparent 60%)",
        }}
      />
      <div className="relative flex items-baseline justify-between">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-neon">
          ★ {tLang(lang, {
            en: "Match of the week",
            vi: "Trận của tuần",
            th: "แมตช์ประจำสัปดาห์",
            zh: "本周焦点赛事",
            ko: "주간 추천 경기",
          })}
        </p>
        <p className="font-mono text-[10px] text-muted">{m.league_code}</p>
      </div>
      <div className="relative flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <TeamLogo slug={m.home_slug} name={m.home_short} size={40} />
          <span className="font-display text-2xl font-semibold uppercase tracking-tighter truncate">
            {m.home_short}
          </span>
        </div>
        <span className="font-mono text-muted text-sm">vs</span>
        <div className="flex items-center gap-2 min-w-0 justify-end">
          <span className="font-display text-2xl font-semibold uppercase tracking-tighter truncate text-right">
            {m.away_short}
          </span>
          <TeamLogo slug={m.away_slug} name={m.away_short} size={40} />
        </div>
      </div>
      <div className="relative flex items-center justify-between gap-3">
        <span className="inline-flex items-center gap-2 rounded-full bg-neon/20 px-3 py-1 font-mono text-xs uppercase tracking-wider text-neon">
          <span aria-hidden>✓</span> {pickLabel} · {Math.round(m.confidence * 100)}%
        </span>
        <span className="font-mono text-xs text-neon">
          @ {m.best_odds.toFixed(2)} · +{m.edge_pp.toFixed(1)}% edge
        </span>
      </div>
    </Link>
  );
}
