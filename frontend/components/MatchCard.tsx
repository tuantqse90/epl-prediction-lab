import Link from "next/link";

import { formatKickoff } from "@/lib/date";
import type { Lang } from "@/lib/i18n";
import { t } from "@/lib/i18n";
import { colorFor } from "@/lib/team-colors";
import type { MatchOut } from "@/lib/types";
import CommitmentBadge from "./CommitmentBadge";
import FormDots from "./FormDots";
import KickoffCountdown from "./KickoffCountdown";
import LiveBadge from "./LiveBadge";
import PredictionBar from "./PredictionBar";
import TeamLogo from "./TeamLogo";
import ValueBetBadge from "./ValueBetBadge";

export default function MatchCard({ match, lang }: { match: MatchOut; lang: Lang }) {
  const topScore = match.prediction?.top_scorelines?.[0];
  const statusLabel = t(lang, `status.${match.status.toLowerCase()}`);
  const homeColor = colorFor(match.home.slug);
  const awayColor = colorFor(match.away.slug);
  const isUpcoming = match.status === "scheduled";
  const isLive = match.status === "live" && match.live;
  const displayPrediction = isLive && match.live
    ? {
        ...match.prediction!,
        p_home_win: match.live.p_home_win,
        p_draw: match.live.p_draw,
        p_away_win: match.live.p_away_win,
      }
    : match.prediction;

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
        {isLive && match.live ? (
          <LiveBadge minute={match.live.minute} period={match.live.live_period} lang={lang} />
        ) : (
          <span className="rounded-full bg-high px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-secondary">
            {statusLabel}
          </span>
        )}
      </div>

      <div className="flex items-center justify-between gap-3">
        <div className="flex flex-col gap-1 min-w-0">
          <div className="flex items-center gap-2">
            <TeamLogo slug={match.home.slug} name={match.home.name} size={28} />
            <span className="font-display text-xl md:text-2xl font-semibold uppercase tracking-tighter truncate">
              {match.home.short_name}
            </span>
          </div>
          {match.home.form && match.home.form.length > 0 && <FormDots form={match.home.form} />}
        </div>
        <span className="font-mono text-muted text-sm">{t(lang, "match.vs")}</span>
        <div className="flex flex-col gap-1 min-w-0 items-end">
          <div className="flex items-center gap-2">
            <span className="font-display text-xl md:text-2xl font-semibold uppercase tracking-tighter truncate text-right">
              {match.away.short_name}
            </span>
            <TeamLogo slug={match.away.slug} name={match.away.name} size={28} />
          </div>
          {match.away.form && match.away.form.length > 0 && <FormDots form={match.away.form} />}
        </div>
      </div>

      {isLive && match.live && match.home_goals !== null && match.away_goals !== null && (
        <div className="flex flex-col items-center gap-1">
          <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-error">
            {t(lang, "match.liveScore")}
          </span>
          <span className="stat text-5xl text-neon">
            {match.home_goals}–{match.away_goals}
          </span>
        </div>
      )}

      {displayPrediction ? (
        <>
          {(() => {
            // Model's argmax pick — the single line users actually need to
            // act on. Shown BEFORE the 3-way bar so the eye lands on it first.
            const probs = {
              H: displayPrediction.p_home_win,
              D: displayPrediction.p_draw,
              A: displayPrediction.p_away_win,
            } as const;
            const pick = (Object.entries(probs) as Array<["H" | "D" | "A", number]>)
              .reduce((a, b) => (b[1] > a[1] ? b : a));
            const [side, conf] = pick;
            const pickLabel =
              side === "H" ? match.home.short_name
              : side === "A" ? match.away.short_name
              : t(lang, "detail.draw");
            const edge = match.odds?.best_edge;
            const edgeHit = typeof edge === "number" && match.odds?.best_outcome === side && edge >= 0.05;
            return (
              <div className="flex items-center justify-between gap-2">
                <span className="inline-flex items-center gap-2 rounded-full bg-neon/15 px-3 py-1 font-mono text-xs uppercase tracking-wide text-neon">
                  <span aria-hidden>✓</span>
                  <span>{lang === "vi" ? "Model chọn" : "Model picks"}</span>
                  <span className="font-semibold">{pickLabel}</span>
                  <span className="text-neon/70">· {Math.round(conf * 100)}%</span>
                </span>
                {edgeHit && (
                  <span className="font-mono text-[10px] uppercase tracking-wide text-neon">
                    +{Math.round(edge * 100)}% vs market
                  </span>
                )}
              </div>
            );
          })()}
          <PredictionBar prediction={displayPrediction} lang={lang} />
          {topScore && !isLive && (
            <div className="flex items-center justify-between">
              <span className="inline-flex items-center gap-1 text-xs text-muted">
                <span className="font-mono uppercase tracking-[0.1em]">{t(lang, "match.predictedLabel")}</span>
                <span>·</span>
                <span>{t(lang, "match.topScore")}</span>
              </span>
              <span className="stat text-secondary">
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
