import Link from "next/link";

import TeamLogo from "@/components/TeamLogo";
import type { Lang } from "@/lib/i18n";
import { leagueByCode } from "@/lib/leagues";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type Scorer = {
  rank: number;
  player_name: string;
  position: string | null;
  team_slug: string;
  team_name: string;
  team_short: string;
  goals: number;
  xg: number;
  assists: number;
  photo_url: string | null;
  league_code: string | null;
};

async function fetchTopScorers(league?: string, limit = 12): Promise<Scorer[]> {
  const qs = new URLSearchParams({ season: "2025-26", sort: "goals", limit: String(limit) });
  if (league) qs.set("league", league);
  try {
    const res = await fetch(`${BASE}/api/stats/scorers?${qs}`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

// Dominant-team initials as a fallback avatar when photo_url is null.
// Keeps layout consistent (same circle) even for scorers whose photo
// didn't come back from API-Football.
function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export default async function StarPlayersStrip({
  league,
  lang,
}: {
  league?: string;
  lang: Lang;
}) {
  const scorers = await fetchTopScorers(league, 12);
  if (scorers.length === 0) return null;

  return (
    <section className="space-y-4">
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <h2 className="headline-section text-2xl md:text-3xl">
          {lang === "vi" ? "Vua phá lưới" : "Top scorers"}
        </h2>
        <Link
          href="/scorers"
          className="font-mono text-xs uppercase tracking-wide text-secondary hover:text-neon transition-colors"
        >
          {lang === "vi" ? "Xem tất cả →" : "See all →"}
        </Link>
      </div>

      <div
        className="flex gap-3 overflow-x-auto pb-3 -mx-6 px-6 snap-x"
        style={{ scrollbarWidth: "thin" }}
      >
        {scorers.map((s) => {
          const lg = leagueByCode(s.league_code);
          return (
            <Link
              key={`${s.player_name}-${s.team_slug}`}
              href={`/teams/${s.team_slug}`}
              className="relative shrink-0 w-[152px] snap-start card hover:border-neon transition-colors p-3 flex flex-col items-center gap-2"
            >
              <span className="absolute top-2 left-2 font-mono text-[10px] text-muted">
                #{s.rank}
              </span>
              {lg && (
                <span
                  className="absolute top-2 right-2 rounded-full bg-high px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wide text-secondary"
                  aria-hidden
                >
                  {lg.emoji}
                </span>
              )}
              {/* Photo — API-Football CDN. On miss, fall back to initials. */}
              {s.photo_url ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  src={s.photo_url}
                  alt={s.player_name}
                  loading="lazy"
                  className="h-20 w-20 rounded-full object-cover border-2 border-neon/30"
                />
              ) : (
                <div className="h-20 w-20 rounded-full bg-high border-2 border-border flex items-center justify-center font-display text-xl text-secondary">
                  {initials(s.player_name)}
                </div>
              )}
              <p className="font-display text-sm font-semibold text-primary text-center leading-tight line-clamp-2 min-h-[2.2em]">
                {s.player_name}
              </p>
              <div className="flex items-center gap-1 text-[10px] font-mono text-muted">
                <TeamLogo slug={s.team_slug} name={s.team_name} size={14} />
                <span className="uppercase tracking-wide">{s.team_short}</span>
              </div>
              <div className="flex items-baseline gap-1 pt-1 border-t border-border-muted w-full justify-center">
                <span className="stat text-neon text-xl leading-none">{s.goals}</span>
                <span className="font-mono text-[10px] text-muted uppercase">
                  {lang === "vi" ? "bàn" : "goals"}
                </span>
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
