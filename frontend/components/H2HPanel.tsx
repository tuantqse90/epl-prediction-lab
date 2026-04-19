import Link from "next/link";

import type { H2HMatch } from "@/lib/api";
import type { Lang } from "@/lib/i18n";
import { t } from "@/lib/i18n";
import { leagueByCode } from "@/lib/leagues";
import TeamLogo from "./TeamLogo";

export default function H2HPanel({
  rows,
  homeShort,
  awayShort,
  homeSlug,
  lang,
}: {
  rows: H2HMatch[];
  homeShort: string;
  awayShort: string;
  homeSlug: string;
  lang: Lang;
}) {
  if (rows.length === 0) {
    return (
      <section className="card">
        <h2 className="label mb-3">{t(lang, "h2h.title", { n: 5 })}</h2>
        <p className="text-muted text-sm">{t(lang, "h2h.empty")}</p>
      </section>
    );
  }

  // Summary: how the current home-team fared in these meetings.
  let homeWins = 0;
  let draws = 0;
  let awayWins = 0;
  for (const r of rows) {
    const currentHomeWasHome = r.home_slug === homeSlug;
    if (r.home_goals === r.away_goals) draws++;
    else {
      const currentHomeWon = currentHomeWasHome
        ? r.home_goals > r.away_goals
        : r.away_goals > r.home_goals;
      if (currentHomeWon) homeWins++;
      else awayWins++;
    }
  }

  return (
    <section className="card space-y-4">
      <h2 className="label">{t(lang, "h2h.title", { n: rows.length })}</h2>

      <div className="flex items-center gap-4 text-sm font-mono">
        <span>
          <span className="text-neon">{homeWins}</span>{" "}
          <span className="text-muted">{t(lang, "h2h.homeWins", { team: homeShort })}</span>
        </span>
        <span className="text-muted">·</span>
        <span>
          <span className="text-secondary">{draws}</span>{" "}
          <span className="text-muted">{t(lang, "h2h.draws")}</span>
        </span>
        <span className="text-muted">·</span>
        <span>
          <span className="text-error">{awayWins}</span>{" "}
          <span className="text-muted">{t(lang, "h2h.awayWins", { team: awayShort })}</span>
        </span>
      </div>

      <ul className="divide-y divide-border/60">
        {rows.map((r) => {
          const league = leagueByCode(r.league_code);
          const isDraw = r.home_goals === r.away_goals;
          const currentHomeWon = r.home_slug === homeSlug
            ? r.home_goals > r.away_goals
            : r.away_goals > r.home_goals;
          const dotColor = isDraw ? "bg-secondary" : currentHomeWon ? "bg-neon" : "bg-error";
          return (
            <li key={r.match_id}>
              <Link
                href={`/match/${r.match_id}`}
                className="flex items-center gap-3 py-2 text-sm hover:text-neon transition-colors"
              >
                <span
                  aria-hidden
                  className={`h-2 w-2 rounded-full shrink-0 ${dotColor}`}
                />
                <span className="font-mono text-xs text-muted w-24 shrink-0">
                  {r.kickoff_date}
                </span>
                {league && (
                  <span className="font-mono text-[10px] text-muted w-12 shrink-0">
                    {league.emoji}
                  </span>
                )}
                <span className="flex items-center gap-2 flex-1 min-w-0">
                  <TeamLogo slug={r.home_slug} name={r.home_short} size={16} />
                  <span className="truncate">{r.home_short}</span>
                  <span className="stat text-base tabular-nums text-primary shrink-0">
                    {r.home_goals}–{r.away_goals}
                  </span>
                  <span className="truncate text-right">{r.away_short}</span>
                  <TeamLogo slug={r.away_slug} name={r.away_short} size={16} />
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
