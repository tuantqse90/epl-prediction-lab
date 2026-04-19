import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import ChatWidget from "@/components/ChatWidget";
import CommitmentBadge from "@/components/CommitmentBadge";
import H2HPanel from "@/components/H2HPanel";
import InjuriesPanel from "@/components/InjuriesPanel";
import InjuryImpactBadge from "@/components/InjuryImpactBadge";
import HalfTimePanel from "@/components/HalfTimePanel";
import TipsterSubmit from "@/components/TipsterSubmit";
import XgMomentum from "@/components/XgMomentum";
import LineupsPanel from "@/components/LineupsPanel";
import LiveStatsPanel from "@/components/LiveStatsPanel";
import OddsComparisonPanel from "@/components/OddsComparisonPanel";
import MatchTabs from "@/components/MatchTabs";
import LiveBadge from "@/components/LiveBadge";
import LivePoller from "@/components/LivePoller";
import MatchEventsList from "@/components/MatchEventsList";
import MarketsPanel from "@/components/MarketsPanel";
import MatchJsonLd from "@/components/MatchJsonLd";
import ScorerOddsPanel from "@/components/ScorerOddsPanel";
import WeatherPanel from "@/components/WeatherPanel";
import PredictionBar from "@/components/PredictionBar";
import ScoreMatrix from "@/components/ScoreMatrix";
import ShareButtons from "@/components/ShareButtons";
import TeamLogo from "@/components/TeamLogo";
import TerminalBlock from "@/components/TerminalBlock";
import { OddsPanel } from "@/components/ValueBetBadge";
import { getH2H, getHalfTime, getInjuries, getInjuryImpact, getLineups, getMarkets, getMatch, getScorerOdds, getWeather } from "@/lib/api";
import ConfidenceBand from "@/components/ConfidenceBand";
import { formatKickoff } from "@/lib/date";
import { getLang, tFor } from "@/lib/i18n-server";
import { leagueByCode } from "@/lib/leagues";
import { colorFor } from "@/lib/team-colors";

export const dynamic = "force-dynamic";

function pct(x: number) {
  return `${Math.round(x * 100)}%`;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  try {
    const match = await getMatch(Number(id));
    const p = match.prediction;
    const title = `${match.home.name} vs ${match.away.name}`;
    const desc = p
      ? `Model: home ${pct(p.p_home_win)} · draw ${pct(p.p_draw)} · away ${pct(
          p.p_away_win,
        )}. Top scoreline ${p.top_scorelines[0]?.home}–${p.top_scorelines[0]?.away}.`
      : "Prediction pending.";
    return {
      title,
      description: desc,
      openGraph: { title, description: desc, url: `/match/${id}`, type: "article" },
      twitter: { card: "summary_large_image", title, description: desc },
    };
  } catch {
    return { title: "Match" };
  }
}

export default async function MatchDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const matchId = Number(id);
  if (!Number.isFinite(matchId)) notFound();

  const lang = await getLang();
  const t = tFor(lang);

  let match;
  try {
    match = await getMatch(matchId);
  } catch {
    notFound();
  }
  const h2h = await getH2H(matchId, 5).catch(() => []);
  const injuries = await getInjuries(matchId).catch(() => ({ home: [], away: [] }));
  const lineups = await getLineups(matchId).catch(() => ({ home: null, away: null }));
  const scorerOdds = await getScorerOdds(matchId, 12).catch(() => []);
  const injuryImpact = await getInjuryImpact(matchId).catch(() => null);
  const weather = await getWeather(matchId).catch(() => null);
  const markets = await getMarkets(matchId).catch(() => null);
  const halfTime = await getHalfTime(matchId).catch(() => null);
  // Bootstrap CI is fetched client-side so the match-detail render path
  // doesn't block on the 1.8-s cold bootstrap. See <ConfidenceBand/>.
  const showCI = match.status === "scheduled";

  const p = match.prediction;
  const isLive = match.status === "live" && !!match.live;
  const isFinal = match.status === "final"
    && match.home_goals !== null
    && match.away_goals !== null;
  const displayPred = isLive && match.live && p
    ? { ...p, p_home_win: match.live.p_home_win, p_draw: match.live.p_draw, p_away_win: match.live.p_away_win }
    : p;
  const top = p?.top_scorelines?.[0];

  // Determine model's pick + whether it matched the actual final outcome.
  const actualOutcome = isFinal
    ? match.home_goals! > match.away_goals!
      ? "H"
      : match.home_goals! < match.away_goals!
      ? "A"
      : "D"
    : null;
  const modelPick = p
    ? p.p_home_win >= p.p_draw && p.p_home_win >= p.p_away_win
      ? "H"
      : p.p_away_win >= p.p_draw
      ? "A"
      : "D"
    : null;
  const isHit = actualOutcome !== null && modelPick !== null && actualOutcome === modelPick;
  const modelPickLabel =
    modelPick === "H" ? match.home.short_name
    : modelPick === "A" ? match.away.short_name
    : (lang === "vi" ? "Hòa" : "Draw");
  const kickoff = formatKickoff(match.kickoff_time, lang);
  const statusLabel = t(`status.${match.status.toLowerCase()}`);
  const homeColor = colorFor(match.home.slug);
  const awayColor = colorFor(match.away.slug);
  const leagueInfo = leagueByCode(match.league_code);
  const leagueLabel = leagueInfo
    ? `${leagueInfo.emoji} ${lang === "vi" ? leagueInfo.name_vi : leagueInfo.name_en}`
    : null;

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-10">
      <MatchJsonLd match={match} url={`https://predictor.nullshift.sh/match/${match.id}`} />
      {isLive && <LivePoller />}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <Link href="/" className="btn-ghost text-sm">
          {t("common.back")}
        </Link>
        <ShareButtons
          url={`https://predictor.nullshift.sh/match/${match.id}`}
          title={`${match.home.name} vs ${match.away.name}`}
        />
      </div>

      <header className="relative -mx-6 overflow-hidden rounded-xl p-6 space-y-3">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-25"
          style={{
            background: `linear-gradient(110deg, ${homeColor} 0%, transparent 45%, transparent 55%, ${awayColor} 100%)`,
          }}
        />
        <div className="relative space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            {leagueLabel && (
              <span className="rounded-full bg-high px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-secondary">
                {leagueLabel}
              </span>
            )}
            <p className="font-mono text-xs text-muted">
              {t("detail.breadcrumb", { id: match.id, date: kickoff, status: statusLabel })}
            </p>
            {match.referee && (
              <span className="font-mono text-xs text-muted">
                · {lang === "vi" ? "TT" : "Ref"}: {match.referee}
              </span>
            )}
          </div>
          <h1 className="flex flex-wrap items-center gap-4 md:gap-6">
            <span className="flex items-center gap-3">
              <TeamLogo slug={match.home.slug} name={match.home.name} size={56} />
              <span className="headline-hero">{match.home.name}</span>
            </span>
            <span className="text-muted font-body normal-case text-2xl">vs</span>
            <span className="flex items-center gap-3">
              <TeamLogo slug={match.away.slug} name={match.away.name} size={56} />
              <span className="headline-hero">{match.away.name}</span>
            </span>
          </h1>
        </div>
      </header>

      {p ? (
        <section className="card space-y-6 relative overflow-hidden">
          <div
            className="pointer-events-none absolute inset-0 opacity-60"
            style={{
              background:
                "radial-gradient(closest-side at 50% 30%, rgba(224,255,50,0.25), transparent 60%)",
            }}
          />
          <div className="relative space-y-6">
            {isLive && match.live && match.home_goals !== null && match.away_goals !== null && (
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-error/40 bg-error/10 p-4">
                <div className="flex items-center gap-3">
                  <LiveBadge minute={match.live.minute} period={match.live.live_period} lang={lang} />
                  <span className="font-mono text-xs uppercase tracking-[0.12em] text-error">
                    {t("match.liveScore")}
                  </span>
                </div>
                <p className="stat text-6xl md:text-7xl text-neon">
                  {match.home_goals}–{match.away_goals}
                </p>
              </div>
            )}
            {isFinal && (
              <div className={
                "flex flex-wrap items-center justify-between gap-3 rounded-lg p-4 " +
                (isHit
                  ? "border border-neon/50 bg-neon/10"
                  : "border border-border bg-high/60")
              }>
                <div className="flex items-center gap-3 flex-wrap">
                  <span className={
                    "rounded-full px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] font-semibold " +
                    (isHit ? "bg-neon text-on-neon" : "bg-high text-secondary")
                  }>
                    {lang === "vi" ? "Kết thúc" : "Full time"}
                  </span>
                  {modelPick !== null && (
                    <span className="font-mono text-xs text-muted uppercase tracking-wide">
                      {lang === "vi" ? "Model chọn" : "Model picked"}{" "}
                      <span className={isHit ? "text-neon font-semibold" : "text-secondary"}>
                        {modelPickLabel}
                      </span>
                      {" · "}
                      <span className={isHit ? "text-neon" : "text-error"}>
                        {isHit ? (lang === "vi" ? "đúng" : "hit") : (lang === "vi" ? "sai" : "miss")}
                      </span>
                    </span>
                  )}
                </div>
                <p className="stat text-6xl md:text-7xl text-neon">
                  {match.home_goals}–{match.away_goals}
                </p>
              </div>
            )}
            <div className="flex flex-wrap items-end justify-between gap-6">
              <div>
                <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
                  {t("match.predictedLabel")} · {t("match.topScore")}
                </p>
                <p className={`stat ${isLive || isFinal ? "text-3xl text-secondary" : "text-5xl md:text-7xl text-neon"}`}>
                  {top?.home}–{top?.away}
                </p>
              </div>
              <div className="text-right">
                <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
                  {t("detail.expectedGoals")}
                </p>
                <p className="stat">
                  {p.expected_home_goals.toFixed(2)} — {p.expected_away_goals.toFixed(2)}
                </p>
              </div>
            </div>
            <PredictionBar prediction={displayPred!} lang={lang} />
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-xs text-muted">{t("detail.home")}</p>
                <p className="stat">{pct(displayPred!.p_home_win)}</p>
              </div>
              <div>
                <p className="text-xs text-muted">{t("detail.draw")}</p>
                <p className="stat">{pct(displayPred!.p_draw)}</p>
              </div>
              <div>
                <p className="text-xs text-muted">{t("detail.away")}</p>
                <p className="stat">{pct(displayPred!.p_away_win)}</p>
              </div>
            </div>
            {showCI && <ConfidenceBand matchId={match.id} lang={lang} />}
          </div>
        </section>
      ) : (
        <section className="card text-muted">{t("detail.pendingPost", { id: match.id })}</section>
      )}

      <MatchTabs
        defaultTab="preview"
        tabs={[
          {
            id: "preview",
            label: lang === "vi" ? "Tổng quan" : "Preview",
            node: (
              <>
                {isLive && match.live?.stats && (
                  <LiveStatsPanel
                    stats={match.live.stats}
                    homeShort={match.home.short_name}
                    awayShort={match.away.short_name}
                    lang={lang}
                  />
                )}
                {match.events && match.events.length > 0 && (
                  <MatchEventsList events={match.events} lang={lang} homeSlug={match.home.slug} />
                )}
                <LineupsPanel
                  lineups={lineups}
                  homeName={match.home.name}
                  awayName={match.away.name}
                  lang={lang}
                />
                {injuryImpact && (
                  <InjuryImpactBadge
                    impact={injuryImpact}
                    lang={lang}
                    homeShort={match.home.short_name}
                    awayShort={match.away.short_name}
                  />
                )}
                <InjuriesPanel
                  injuries={injuries}
                  homeShort={match.home.short_name}
                  awayShort={match.away.short_name}
                  lang={lang}
                />
                {weather && <WeatherPanel weather={weather} lang={lang} />}
                <XgMomentum
                  homeSlug={match.home.slug}
                  homeShort={match.home.short_name}
                  awaySlug={match.away.slug}
                  awayShort={match.away.short_name}
                  season={match.season}
                  lang={lang}
                />
                <ScorerOddsPanel rows={scorerOdds} lang={lang} />
              </>
            ),
          },
          {
            id: "markets",
            label: lang === "vi" ? "Thị trường" : "Markets",
            node: (
              <>
                {halfTime && (
                  <HalfTimePanel
                    data={halfTime}
                    homeShort={match.home.short_name}
                    awayShort={match.away.short_name}
                    lang={lang}
                  />
                )}
                {markets && <MarketsPanel markets={markets} lang={lang} />}
                {match.odds && (
                  <OddsPanel
                    odds={match.odds}
                    lang={lang}
                    matchId={match.id}
                    prediction={match.prediction}
                  />
                )}
                <OddsComparisonPanel
                  matchId={match.id}
                  homeShort={match.home.short_name}
                  awayShort={match.away.short_name}
                  lang={lang}
                />
                {p && (
                  <ScoreMatrix
                    prediction={p}
                    lang={lang}
                    homeShort={match.home.short_name}
                    awayShort={match.away.short_name}
                  />
                )}
              </>
            ),
          },
          {
            id: "analysis",
            label: lang === "vi" ? "Phân tích" : "Analysis",
            node: (
              <>
                {p?.reasoning && <TerminalBlock title={t("detail.analysis")}>{p.reasoning}</TerminalBlock>}
                <H2HPanel
                  rows={h2h}
                  homeShort={match.home.short_name}
                  awayShort={match.away.short_name}
                  homeSlug={match.home.slug}
                  lang={lang}
                />
                {p && <CommitmentBadge prediction={p} lang={lang} />}
              </>
            ),
          },
          {
            id: "community",
            label: lang === "vi" ? "Cộng đồng" : "Community",
            node: (
              <>
                {match.status === "scheduled" && (
                  <TipsterSubmit
                    matchId={match.id}
                    homeShort={match.home.short_name}
                    awayShort={match.away.short_name}
                  />
                )}
                <ChatWidget matchId={match.id} />
              </>
            ),
          },
        ]}
      />
    </main>
  );
}
