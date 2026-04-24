import Link from "next/link";

import TeamLogo from "./TeamLogo";
import type { MatchOut } from "@/lib/types";
import type { Lang } from "@/lib/i18n";
import { leagueByCode } from "@/lib/leagues";

function pickFeatured(matches: MatchOut[]): MatchOut | null {
  // 1) Any live match wins — it's the most-immediate thing to watch.
  const live = matches.find((m) => m.status === "live");
  if (live) return live;
  // 2) Else the most-imminent scheduled match inside 48h.
  const now = Date.now();
  const upcoming = matches
    .filter((m) => m.status === "scheduled")
    .sort(
      (a, b) =>
        new Date(a.kickoff_time).getTime() - new Date(b.kickoff_time).getTime(),
    );
  const first = upcoming[0];
  if (!first) return null;
  const hours = (new Date(first.kickoff_time).getTime() - now) / 3_600_000;
  return hours <= 48 ? first : null;
}

function countdownLabel(isoKickoff: string, lang: Lang): string {
  const ms = new Date(isoKickoff).getTime() - Date.now();
  if (ms < 0) return lang === "vi" ? "Sắp đá" : "Starting";
  const hours = Math.floor(ms / 3_600_000);
  const mins = Math.floor((ms % 3_600_000) / 60_000);
  if (hours >= 24) {
    const days = Math.floor(hours / 24);
    const remH = hours % 24;
    return lang === "vi"
      ? `còn ${days}d ${remH}h`
      : `in ${days}d ${remH}h`;
  }
  if (hours > 0) {
    return lang === "vi" ? `còn ${hours}h ${mins}m` : `in ${hours}h ${mins}m`;
  }
  return lang === "vi" ? `còn ${mins} phút` : `in ${mins} min`;
}

export default function FeaturedMatch({
  matches,
  lang,
}: {
  matches: MatchOut[];
  lang: Lang;
}) {
  const m = pickFeatured(matches);
  if (!m) return null;

  const league = leagueByCode(m.league_code);
  const p = m.prediction;
  const isLive = m.status === "live";
  const displayPred =
    isLive && m.live && p
      ? {
          p_home_win: m.live.p_home_win,
          p_draw: m.live.p_draw,
          p_away_win: m.live.p_away_win,
        }
      : p;

  const pick = displayPred
    ? displayPred.p_home_win >= displayPred.p_draw &&
      displayPred.p_home_win >= displayPred.p_away_win
      ? "H"
      : displayPred.p_away_win >= displayPred.p_draw
      ? "A"
      : "D"
    : null;

  const pickLabel =
    pick === "H"
      ? m.home.short_name
      : pick === "A"
      ? m.away.short_name
      : lang === "vi"
      ? "Hoà"
      : "Draw";

  const pickConf = displayPred
    ? pick === "H"
      ? displayPred.p_home_win
      : pick === "A"
      ? displayPred.p_away_win
      : displayPred.p_draw
    : 0;

  return (
    <Link
      href={`/match/${m.id}`}
      className="relative block overflow-hidden rounded-2xl border border-border/70 bg-raised hover:border-neon transition-colors"
    >
      {/* Neon gradient halo — subtle, echoes the ping-dot identity. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-60"
        style={{
          background:
            "radial-gradient(600px 260px at 50% -20%, rgba(224,255,50,0.14), transparent 70%)",
        }}
      />

      <div className="relative px-6 py-8 md:px-10 md:py-10 space-y-7">
        {/* Top strip: league + live/countdown badge */}
        <div className="flex items-center justify-between gap-3 text-xs font-mono uppercase tracking-[0.18em]">
          <span className="text-muted flex items-center gap-2">
            {league && <span aria-hidden>{league.emoji}</span>}
            <span>{league ? (lang === "vi" ? league.name_vi : league.name_en) : m.league_code}</span>
            <span className="text-muted/60">· featured</span>
          </span>
          {isLive ? (
            <span className="inline-flex items-center gap-1.5 text-neon">
              <span className="relative inline-flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full rounded-full bg-neon opacity-70 animate-ping" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-neon" />
              </span>
              <span>live · {m.live?.minute ?? "?"}&apos;</span>
            </span>
          ) : (
            <span className="text-secondary">{countdownLabel(m.kickoff_time, lang)}</span>
          )}
        </div>

        {/* Teams — big logos front and center */}
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4 md:gap-8">
          <div className="flex flex-col items-center gap-3 text-center">
            <TeamLogo slug={m.home.slug} name={m.home.name} size={96} />
            <span className="font-display text-xl md:text-3xl font-bold uppercase tracking-tight leading-tight">
              {m.home.name}
            </span>
          </div>
          <div className="flex flex-col items-center gap-1">
            {isLive && m.home_goals !== null && m.away_goals !== null ? (
              <span className="font-display text-5xl md:text-7xl font-bold text-neon tabular-nums">
                {m.home_goals} <span className="text-muted mx-1">–</span> {m.away_goals}
              </span>
            ) : (
              <span className="font-body text-2xl md:text-3xl text-muted normal-case">vs</span>
            )}
          </div>
          <div className="flex flex-col items-center gap-3 text-center">
            <TeamLogo slug={m.away.slug} name={m.away.name} size={96} />
            <span className="font-display text-xl md:text-3xl font-bold uppercase tracking-tight leading-tight">
              {m.away.name}
            </span>
          </div>
        </div>

        {/* Prediction bar */}
        {displayPred && (
          <div className="space-y-3">
            <div className="flex h-2 overflow-hidden rounded-full bg-high">
              <div
                className="bg-neon"
                style={{ width: `${displayPred.p_home_win * 100}%` }}
              />
              <div
                className="bg-border"
                style={{ width: `${displayPred.p_draw * 100}%` }}
              />
              <div
                className="bg-secondary/70"
                style={{ width: `${displayPred.p_away_win * 100}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-secondary tabular-nums">
                <span className="text-neon">{Math.round(displayPred.p_home_win * 100)}%</span> · H
              </span>
              <span className="text-secondary tabular-nums">
                D · <span className="text-primary">{Math.round(displayPred.p_draw * 100)}%</span>
              </span>
              <span className="text-secondary tabular-nums">
                A · <span className="text-primary">{Math.round(displayPred.p_away_win * 100)}%</span>
              </span>
            </div>
            {pick && (
              <p className="font-mono text-xs text-secondary">
                {lang === "vi" ? "Model nghiêng về" : "Model leans"}{" "}
                <span className="font-display text-base text-neon uppercase tracking-tight">
                  {pickLabel}
                </span>{" "}
                · {Math.round(pickConf * 100)}%
              </p>
            )}
          </div>
        )}

        {/* CTA */}
        <div className="flex items-center justify-between text-xs font-mono uppercase tracking-[0.18em]">
          <span className="text-muted">full analysis</span>
          <span className="text-neon">view match →</span>
        </div>
      </div>
    </Link>
  );
}
