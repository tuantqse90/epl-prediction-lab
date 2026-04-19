import Link from "next/link";

import TeamLogo from "@/components/TeamLogo";
import { formatDateOnly } from "@/lib/date";
import type { Lang } from "@/lib/i18n";
import { leagueByCode } from "@/lib/leagues";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type RecentMatch = {
  match_id: number;
  kickoff_time: string;
  league_code: string | null;
  home_slug: string;
  home_short: string;
  away_slug: string;
  away_short: string;
  home_goals: number;
  away_goals: number;
  predicted_outcome: "H" | "D" | "A";
  actual_outcome: "H" | "D" | "A";
  hit: boolean;
  confidence: number;
};

type RecentWindow = {
  days: number;
  scored: number;
  correct: number;
  accuracy: number;
  mean_log_loss: number;
  matches: RecentMatch[];
};

async function fetchRecent(league?: string, days = 7): Promise<RecentWindow | null> {
  const qs = new URLSearchParams({ days: String(days) });
  if (league) qs.set("league", league);
  try {
    const res = await fetch(`${BASE}/api/stats/recent?${qs}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

function pct(x: number) {
  return `${Math.round(x * 100)}%`;
}

// Recently-finished matches strip on the homepage — gives users proof that
// the model was scoring matches before they arrived, not just making
// predictions into the void. Hit/miss badge per card, links to match detail.
export default async function RecentResults({
  league,
  lang,
}: {
  league?: string;
  lang: Lang;
}) {
  const w = await fetchRecent(league, 7);
  if (!w || w.matches.length === 0) return null;

  const top = w.matches.slice(0, 6);

  return (
    <section className="space-y-4">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <h2 className="headline-section text-2xl md:text-3xl">
          {lang === "vi" ? "Kết quả gần nhất" : "Just finished"}
        </h2>
        <div className="flex items-baseline gap-3 font-mono text-xs">
          <span className="text-neon font-semibold">
            {w.correct}/{w.scored}
          </span>
          <span className="text-muted">
            {pct(w.accuracy)} {lang === "vi" ? "chính xác · 7 ngày" : "accuracy · last 7d"}
          </span>
          <Link
            href="/last-weekend"
            className="text-secondary hover:text-neon transition-colors uppercase tracking-wide"
          >
            {lang === "vi" ? "Xem đầy đủ →" : "View all →"}
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {top.map((m) => {
          const matchLeague = leagueByCode(m.league_code);
          const dateStr = formatDateOnly(m.kickoff_time, lang);
          return (
            <Link
              key={m.match_id}
              href={`/match/${m.match_id}`}
              className={
                "card flex flex-col gap-2 hover:border-neon transition-colors " +
                (m.hit ? "border-neon/40" : "border-error/30")
              }
            >
              <div className="flex items-baseline justify-between gap-2 text-[10px] font-mono">
                <div className="flex items-baseline gap-2 min-w-0">
                  {matchLeague && (
                    <span className="rounded-full bg-high px-1.5 py-0.5 uppercase tracking-wide text-secondary shrink-0">
                      {matchLeague.emoji} {matchLeague.short}
                    </span>
                  )}
                  <span className="text-muted">{dateStr}</span>
                </div>
                <span
                  className={
                    "rounded-full px-2 py-0.5 uppercase tracking-wide shrink-0 " +
                    (m.hit ? "bg-neon text-on-neon font-semibold" : "bg-high text-error")
                  }
                >
                  {m.hit ? (lang === "vi" ? "đúng" : "hit") : (lang === "vi" ? "sai" : "miss")}
                </span>
              </div>

              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <TeamLogo slug={m.home_slug} name={m.home_short} size={22} />
                  <span className="font-display text-base md:text-lg font-semibold uppercase tracking-tight truncate">
                    {m.home_short}
                  </span>
                </div>
                <span className="stat text-xl text-neon tabular-nums shrink-0">
                  {m.home_goals}–{m.away_goals}
                </span>
                <div className="flex items-center gap-2 min-w-0 flex-1 justify-end">
                  <span className="font-display text-base md:text-lg font-semibold uppercase tracking-tight truncate">
                    {m.away_short}
                  </span>
                  <TeamLogo slug={m.away_slug} name={m.away_short} size={22} />
                </div>
              </div>

              <div className="flex items-center justify-between gap-2 text-[10px] font-mono pt-1 border-t border-border-muted">
                <span className="text-muted uppercase tracking-wide">
                  {lang === "vi" ? "model chọn" : "model picked"}
                </span>
                <span className={m.hit ? "text-neon" : "text-secondary"}>
                  {m.predicted_outcome === "H"
                    ? m.home_short
                    : m.predicted_outcome === "A"
                    ? m.away_short
                    : (lang === "vi" ? "Hòa" : "Draw")}
                  {" · "}
                  {pct(m.confidence)}
                </span>
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
