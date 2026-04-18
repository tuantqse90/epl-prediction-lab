import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import ChatWidget from "@/components/ChatWidget";
import CommitmentBadge from "@/components/CommitmentBadge";
import PredictionBar from "@/components/PredictionBar";
import ScoreMatrix from "@/components/ScoreMatrix";
import TeamLogo from "@/components/TeamLogo";
import TerminalBlock from "@/components/TerminalBlock";
import { OddsPanel } from "@/components/ValueBetBadge";
import { getMatch } from "@/lib/api";
import { formatKickoff } from "@/lib/date";
import { getLang, tFor } from "@/lib/i18n-server";
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

  const p = match.prediction;
  const top = p?.top_scorelines?.[0];
  const kickoff = formatKickoff(match.kickoff_time, lang);
  const statusLabel = t(`status.${match.status.toLowerCase()}`);
  const homeColor = colorFor(match.home.slug);
  const awayColor = colorFor(match.away.slug);

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-10">
      <Link href="/" className="btn-ghost text-sm">
        {t("common.back")}
      </Link>

      <header className="relative -mx-6 overflow-hidden rounded-xl p-6 space-y-3">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-25"
          style={{
            background: `linear-gradient(110deg, ${homeColor} 0%, transparent 45%, transparent 55%, ${awayColor} 100%)`,
          }}
        />
        <div className="relative space-y-3">
          <p className="font-mono text-xs text-muted">
            {t("detail.breadcrumb", { id: match.id, date: kickoff, status: statusLabel })}
          </p>
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
            <div className="flex flex-wrap items-end justify-between gap-6">
              <div>
                <p className="text-sm text-muted">{t("match.topScore")}</p>
                <p className="stat text-5xl md:text-7xl text-neon">
                  {top?.home}–{top?.away}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm text-muted">{t("detail.expectedGoals")}</p>
                <p className="stat">
                  {p.expected_home_goals.toFixed(2)} — {p.expected_away_goals.toFixed(2)}
                </p>
              </div>
            </div>
            <PredictionBar prediction={p} lang={lang} />
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-xs text-muted">{t("detail.home")}</p>
                <p className="stat">{pct(p.p_home_win)}</p>
              </div>
              <div>
                <p className="text-xs text-muted">{t("detail.draw")}</p>
                <p className="stat">{pct(p.p_draw)}</p>
              </div>
              <div>
                <p className="text-xs text-muted">{t("detail.away")}</p>
                <p className="stat">{pct(p.p_away_win)}</p>
              </div>
            </div>
          </div>
        </section>
      ) : (
        <section className="card text-muted">{t("detail.pendingPost", { id: match.id })}</section>
      )}

      {match.odds && <OddsPanel odds={match.odds} lang={lang} />}
      {p && (
        <ScoreMatrix
          prediction={p}
          lang={lang}
          homeShort={match.home.short_name}
          awayShort={match.away.short_name}
        />
      )}
      {p?.reasoning && <TerminalBlock title={t("detail.analysis")}>{p.reasoning}</TerminalBlock>}
      {p && <CommitmentBadge prediction={p} lang={lang} />}

      <ChatWidget matchId={match.id} />
    </main>
  );
}
