import Link from "next/link";

import { formatKickoff } from "@/lib/date";
import type { Lang } from "@/lib/i18n";
import { t } from "@/lib/i18n";
import { colorFor } from "@/lib/team-colors";
import type { MatchOut } from "@/lib/types";
import CommitmentBadge from "./CommitmentBadge";
import KickoffCountdown from "./KickoffCountdown";
import PredictionBar from "./PredictionBar";
import TeamLogo from "./TeamLogo";
import ValueBetBadge from "./ValueBetBadge";

export default function MatchCard({ match, lang }: { match: MatchOut; lang: Lang }) {
  const topScore = match.prediction?.top_scorelines?.[0];
  const statusLabel = t(lang, `status.${match.status.toLowerCase()}`);
  const homeColor = colorFor(match.home.slug);
  const awayColor = colorFor(match.away.slug);
  const isUpcoming = match.status === "scheduled";

  return (
    <Link
      href={`/match/${match.id}`}
      className="relative card flex flex-col gap-4 hover:border-neon transition-colors overflow-hidden"
    >
      {/* team-color identity strip at top */}
      <div
        aria-hidden
        className="pointer-events-none absolute top-0 left-0 right-0 h-[3px]"
        style={{
          background: `linear-gradient(to right, ${homeColor} 0%, ${homeColor} 50%, ${awayColor} 50%, ${awayColor} 100%)`,
        }}
      />

      <div className="flex items-baseline justify-between">
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-xs text-muted">
            {formatKickoff(match.kickoff_time, lang)}
          </span>
          {isUpcoming && <KickoffCountdown iso={match.kickoff_time} lang={lang} />}
        </div>
        <span className="rounded-full bg-high px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-secondary">
          {statusLabel}
        </span>
      </div>

      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <TeamLogo slug={match.home.slug} name={match.home.name} size={28} />
          <span className="font-display text-xl md:text-2xl font-semibold uppercase tracking-tighter truncate">
            {match.home.short_name}
          </span>
        </div>
        <span className="font-mono text-muted text-sm">{t(lang, "match.vs")}</span>
        <div className="flex items-center gap-2 min-w-0 justify-end">
          <span className="font-display text-xl md:text-2xl font-semibold uppercase tracking-tighter truncate text-right">
            {match.away.short_name}
          </span>
          <TeamLogo slug={match.away.slug} name={match.away.name} size={28} />
        </div>
      </div>

      {match.prediction ? (
        <>
          <PredictionBar prediction={match.prediction} lang={lang} />
          {topScore && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted">{t(lang, "match.topScore")}</span>
              <span className="stat">
                {topScore.home}–{topScore.away}
              </span>
            </div>
          )}
          <div className="flex items-center justify-between gap-2 flex-wrap">
            {match.odds && <ValueBetBadge odds={match.odds} lang={lang} />}
            {match.prediction && <CommitmentBadge prediction={match.prediction} lang={lang} compact />}
          </div>
        </>
      ) : (
        <div className="text-sm text-muted">{t(lang, "match.pending")}</div>
      )}
    </Link>
  );
}
