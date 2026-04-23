import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import FollowStar from "@/components/FollowStar";
import RadialGauge from "@/components/RadialGauge";
import SeasonTrajectoryChart from "@/components/SeasonTrajectoryChart";
import TeamLogo from "@/components/TeamLogo";
import { formatShortDate } from "@/lib/date";
import { getLang, tFor } from "@/lib/i18n-server";
import AnimatedNumber from "@/components/AnimatedNumber";
import { leagueByCode } from "@/lib/leagues";
import { colorFor } from "@/lib/team-colors";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type TopScorer = {
  player_name: string;
  position: string | null;
  goals: number;
  xg: number;
  assists: number;
  xa: number;
  photo_url: string | null;
};

type FixtureBrief = {
  id: number;
  kickoff_time: string;
  status: string;
  home_slug: string;
  home_short: string;
  away_slug: string;
  away_short: string;
  home_goals: number | null;
  away_goals: number | null;
  is_home: boolean;
};

type TeamProfile = {
  slug: string;
  name: string;
  short_name: string;
  season: string;
  league_code: string | null;
  league_rank: number | null;
  stats: {
    played: number;
    wins: number;
    draws: number;
    losses: number;
    points: number;
    goals_for: number;
    goals_against: number;
    xg_for: number;
    xg_against: number;
  };
  form: string[];
  top_scorers: TopScorer[];
  recent: FixtureBrief[];
  upcoming: FixtureBrief[];
};

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const res = await fetch(`${BASE}/api/teams/${slug}`, { cache: "no-store" });
  if (!res.ok) return { title: "Team" };
  const p: TeamProfile = await res.json();
  const s = p.stats;
  const desc = `${p.season}: ${s.played}P · ${s.wins}W-${s.draws}D-${s.losses}L · ${s.points} pts · xG Δ ${(s.xg_for - s.xg_against).toFixed(1)}.`;
  return {
    title: p.name,
    description: desc,
    openGraph: { title: p.name, description: desc, url: `/teams/${slug}` },
  };
}

async function fetchProfile(slug: string): Promise<TeamProfile | null> {
  const res = await fetch(`${BASE}/api/teams/${slug}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`profile: ${res.status}`);
  return res.json();
}

type TeamNarrative = {
  team_slug: string;
  season: string;
  lang: string;
  story: string;
  generated_at: string;
};

async function fetchNarrative(slug: string, season: string): Promise<TeamNarrative | null> {
  try {
    const res = await fetch(
      `${BASE}/api/teams/${slug}/narrative?season=${encodeURIComponent(season)}`,
      { next: { revalidate: 3600 } },
    );
    if (!res.ok) return null;
    const body = await res.json();
    return body as TeamNarrative | null;
  } catch {
    return null;
  }
}

export async function generateStaticParams() {
  // Prerender a stub for every team we know about so Google can index
  // all 100+ team pages without hitting the origin for each one. Pages
  // still revalidate through `dynamic = "force-dynamic"` for live stats.
  try {
    const res = await fetch(`${BASE}/api/teams`, { cache: "no-store" });
    if (!res.ok) return [];
    const teams = await res.json();
    return teams.map((t: { slug: string }) => ({ slug: t.slug }));
  } catch {
    return [];
  }
}

function playerSlug(name: string) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function formDot(r: string) {
  if (r === "W") return "bg-neon";
  if (r === "L") return "bg-error";
  return "bg-muted";
}

function fixtureResult(f: FixtureBrief) {
  const hg = f.home_goals;
  const ag = f.away_goals;
  if (hg == null || ag == null) return null;
  const ourScore = f.is_home ? hg : ag;
  const theirScore = f.is_home ? ag : hg;
  if (ourScore > theirScore) return "W" as const;
  if (ourScore < theirScore) return "L" as const;
  return "D" as const;
}

export default async function TeamPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const lang = await getLang();
  const t = tFor(lang);
  const p = await fetchProfile(slug);
  if (!p) notFound();
  const narrative = await fetchNarrative(slug, p.season);

  const SITE = "https://predictor.nullshift.sh";
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "SportsTeam",
    "name": p.name,
    "alternateName": p.short_name,
    "url": `${SITE}/teams/${p.slug}`,
    "sport": "Football",
    "memberOf": p.league_code
      ? { "@type": "SportsOrganization", name: p.league_code }
      : undefined,
    "description":
      `${p.season}: ${p.stats.played}P · ${p.stats.wins}W-${p.stats.draws}D-${p.stats.losses}L · ` +
      `${p.stats.points} pts · xG Δ ${(p.stats.xg_for - p.stats.xg_against).toFixed(1)}.`,
    "athlete": p.top_scorers.slice(0, 5).map((s) => ({
      "@type": "Person",
      "name": s.player_name,
      "jobTitle": s.position,
    })),
  };

  const s = p.stats;
  const xgDiff = s.xg_for - s.xg_against;
  const color = colorFor(p.slug);
  const ppg = s.played > 0 ? s.points / s.played : 0;

  // Coefficients relative to a ~1.45 goals-per-match baseline (top-5 avg).
  const attackCoef = s.played > 0 ? s.xg_for / s.played / 1.45 : 1;
  const defenseCoef = s.played > 0 ? s.xg_against / s.played / 1.45 : 1;

  const nextFixture = p.upcoming[0];
  const lastFixture = p.recent[0];
  const lastResult = lastFixture ? fixtureResult(lastFixture) : null;
  const topScorer = p.top_scorers[0];
  const leagueInfo = leagueByCode(p.league_code);
  const isElite = p.league_rank != null && p.league_rank <= 8;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10 space-y-10">
      {/* JSON-LD structured data — helps Google render rich results for the team */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <nav className="flex items-center gap-2 font-mono text-xs text-muted" aria-label="Breadcrumb">
        <Link href="/" className="hover:text-neon">Home</Link>
        {leagueInfo && (
          <>
            <span aria-hidden>/</span>
            <Link href={`/leagues/${leagueInfo.slug}`} className="hover:text-neon">
              {leagueInfo.emoji} {leagueInfo.short}
            </Link>
          </>
        )}
        <span aria-hidden>/</span>
        <span className="text-secondary truncate">{p.name}</span>
      </nav>

      {/* HERO — elite treatment if team is in top-8 of its league */}
      <header
        className={
          "relative -mx-6 overflow-hidden rounded-2xl p-8 md:p-12 border bg-surface " +
          (isElite ? "border-neon/50 shadow-[0_0_48px_rgba(224,255,50,0.15)]" : "border-border/30")
        }
      >
        {/* Animated team-color glow (subtle pulse, elite only). */}
        <div
          aria-hidden
          className={"pointer-events-none absolute inset-0 " + (isElite ? "team-hero-pulse" : "")}
          style={{
            background: `radial-gradient(closest-side at 30% 30%, ${color}55, transparent 65%),
                         radial-gradient(closest-side at 90% 80%, ${color}22, transparent 70%)`,
          }}
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -top-16 -right-10 opacity-[0.07]"
        >
          <TeamLogo slug={p.slug} name={p.name} size={360} />
        </div>
        <div className="relative space-y-6">
          <div className="flex items-center gap-3 flex-wrap">
            <p className="font-mono text-xs text-muted">
              {t("common.season")} {p.season}
            </p>
            {leagueInfo && p.league_rank != null && (
              <span
                className={
                  "font-mono text-[10px] uppercase tracking-[0.18em] rounded-full px-2 py-0.5 " +
                  (isElite
                    ? "bg-neon text-on-neon font-semibold"
                    : "bg-high text-secondary")
                }
              >
                {isElite ? "⭐ TOP 8 · " : ""}#{p.league_rank} {leagueInfo.emoji} {leagueInfo.short}
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-4 md:gap-6">
            <div className={isElite ? "team-crest-pulse rounded-full" : ""}>
              <TeamLogo slug={p.slug} name={p.name} size={88} />
            </div>
            <div className="flex flex-col gap-2 min-w-0">
              <h1 className="headline-hero">{p.name}</h1>
              <div className="flex items-center gap-3 flex-wrap">
                <span className="rounded-full bg-high px-2.5 py-0.5 font-mono text-[11px] uppercase tracking-wider text-secondary">
                  {s.wins}W · {s.draws}D · {s.losses}L
                </span>
                <FollowStar slug={p.slug} label={p.name} />
              </div>
            </div>
          </div>

          {/* Hero stat row — numbers count up on mount (client component). */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pt-4">
            <div>
              <p className="label">{t("team.points")}</p>
              <AnimatedNumber
                value={s.points}
                className="font-display text-5xl font-bold tabular-nums text-neon leading-none"
              />
              <p className="font-mono text-[11px] text-muted mt-1">{ppg.toFixed(2)} pts/game</p>
            </div>
            <div>
              <p className="label">{t("team.goals")}</p>
              <p className="font-display text-5xl font-bold tabular-nums leading-none">
                <AnimatedNumber value={s.goals_for} />
                <span className="text-muted text-3xl">–</span>
                <AnimatedNumber value={s.goals_against} />
              </p>
              <p className="font-mono text-[11px] text-muted mt-1">
                GD {s.goals_for - s.goals_against > 0 ? "+" : ""}
                {s.goals_for - s.goals_against}
              </p>
            </div>
            <div>
              <p className="label">{t("team.xgDiff")}</p>
              <AnimatedNumber
                value={xgDiff}
                decimals={1}
                prefix={xgDiff > 0 ? "+" : ""}
                className={
                  "font-display text-5xl font-bold tabular-nums leading-none " +
                  (xgDiff > 0.5 ? "text-neon" : xgDiff < -0.5 ? "text-error" : "")
                }
              />
              <p className="font-mono text-[11px] text-muted mt-1">
                xG {s.xg_for.toFixed(1)} / {s.xg_against.toFixed(1)}
              </p>
            </div>
            <div>
              <p className="label">{t("team.form")}</p>
              <div className="flex items-center gap-1.5 h-[48px]">
                {p.form.length === 0 && (
                  <span className="text-muted text-sm">{t("team.form.none")}</span>
                )}
                {p.form.slice(0, 10).map((r, i) => (
                  <span
                    key={i}
                    title={r}
                    className={`h-3 w-3 rounded-full ${formDot(r)}`}
                  />
                ))}
              </div>
              <p className="font-mono text-[11px] text-muted mt-1">last 10 results</p>
            </div>
          </div>
        </div>
      </header>

      {/* Next fixture + last result spotlight */}
      {(nextFixture || (lastFixture && lastResult)) && (
        <section className="grid md:grid-cols-2 gap-4">
          {nextFixture && (
            <Link
              href={`/match/${nextFixture.id}`}
              className="card flex items-center gap-4 hover:border-neon transition-colors"
            >
              <span className="label text-neon shrink-0">Next</span>
              <div className="flex-1 min-w-0">
                <p className="font-display font-semibold text-lg truncate">
                  {nextFixture.is_home
                    ? `vs ${nextFixture.away_short}`
                    : `@ ${nextFixture.home_short}`}
                </p>
                <p className="font-mono text-xs text-muted">
                  {formatShortDate(nextFixture.kickoff_time, lang)}
                </p>
              </div>
              <TeamLogo
                slug={nextFixture.is_home ? nextFixture.away_slug : nextFixture.home_slug}
                name={nextFixture.is_home ? nextFixture.away_short : nextFixture.home_short}
                size={40}
              />
            </Link>
          )}
          {lastFixture && lastResult && (
            <Link
              href={`/match/${lastFixture.id}`}
              className="card flex items-center gap-4 hover:border-neon transition-colors"
            >
              <span
                className={
                  "label shrink-0 " +
                  (lastResult === "W" ? "text-neon" : lastResult === "L" ? "text-error" : "text-secondary")
                }
              >
                Last {lastResult}
              </span>
              <div className="flex-1 min-w-0">
                <p className="font-display font-semibold text-lg tabular-nums">
                  {lastFixture.home_short} {lastFixture.home_goals}–{lastFixture.away_goals} {lastFixture.away_short}
                </p>
                <p className="font-mono text-xs text-muted">
                  {formatShortDate(lastFixture.kickoff_time, lang)}
                </p>
              </div>
            </Link>
          )}
        </section>
      )}

      {/* Attack / defense gauges */}
      <section className="card space-y-6">
        <div className="flex items-baseline justify-between gap-2 flex-wrap">
          <h2 className="label">Attack / defense vs league</h2>
          <p className="text-[11px] text-muted">1.00 = league average xG per match</p>
        </div>
        <div className="flex flex-wrap justify-center gap-10">
          <RadialGauge value={attackCoef} label="Attack" higherIsBetter />
          <RadialGauge value={defenseCoef} label="Defense" higherIsBetter={false} />
        </div>
      </section>

      <SeasonTrajectoryChart slug={p.slug} season={p.season} lang={lang} />

      {narrative && narrative.story && (
        <section className="card space-y-3">
          <div className="flex items-baseline justify-between">
            <h2 className="label">
              {lang === "vi" ? "Câu chuyện mùa giải" : "Season story"}
            </h2>
            <p className="font-mono text-[10px] text-muted">
              {new Date(narrative.generated_at).toISOString().slice(0, 10)} · Qwen-Plus
            </p>
          </div>
          <div className="prose prose-invert max-w-none text-secondary leading-relaxed space-y-3">
            {narrative.story.split(/\n\n+/).map((para, i) => (
              <p key={i} className="text-[15px]">{para}</p>
            ))}
          </div>
        </section>
      )}

      {/* Top scorer spotlight */}
      {topScorer && (
        <section className="card relative overflow-hidden">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 opacity-40"
            style={{
              background: `radial-gradient(closest-side at 15% 50%, ${color}44, transparent 55%)`,
            }}
          />
          <div className="relative flex items-center gap-6 flex-wrap">
            {topScorer.photo_url ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={topScorer.photo_url}
                alt={topScorer.player_name}
                loading="lazy"
                className="h-28 w-28 rounded-full object-cover border-4 border-neon/40 shadow-[0_0_24px_rgba(224,255,50,0.25)] shrink-0"
              />
            ) : (
              <div className="h-28 w-28 rounded-full bg-high border-4 border-border flex items-center justify-center font-display text-3xl text-secondary shrink-0">
                {topScorer.player_name
                  .split(/\s+/)
                  .slice(0, 2)
                  .map((p) => p[0]?.toUpperCase() ?? "")
                  .join("")}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="label mb-2">Top scorer</p>
              <Link
                href={`/players/${playerSlug(topScorer.player_name)}`}
                className="hover:text-neon"
              >
                <p className="font-display text-3xl font-semibold truncate">
                  {topScorer.player_name}
                </p>
              </Link>
              <p className="font-mono text-xs text-muted mt-1">
                {topScorer.position ?? "—"}
              </p>
            </div>
            <div className="flex gap-6">
              <div>
                <p className="label">Goals</p>
                <p className="stat text-neon text-4xl">{topScorer.goals}</p>
              </div>
              <div>
                <p className="label">xG</p>
                <p className="stat text-4xl">{topScorer.xg.toFixed(1)}</p>
              </div>
              <div>
                <p className="label">G − xG</p>
                <p
                  className={`stat text-4xl ${
                    topScorer.goals - topScorer.xg > 1
                      ? "text-neon"
                      : topScorer.goals - topScorer.xg < -1
                      ? "text-error"
                      : ""
                  }`}
                >
                  {topScorer.goals - topScorer.xg > 0 ? "+" : ""}
                  {(topScorer.goals - topScorer.xg).toFixed(1)}
                </p>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Full scorers table */}
      {p.top_scorers.length > 1 && (
        <section className="card p-0 overflow-x-auto">
          <div className="flex items-baseline justify-between p-5 pb-3">
            <h2 className="label">{t("team.topScorers")}</h2>
            <p className="text-[11px] text-muted">Top {p.top_scorers.length} by goals</p>
          </div>
          <table className="w-full font-mono text-sm">
            <thead className="text-muted">
              <tr className="border-b border-border">
                {["#", "player", "pos", "G", "xG", "A", "xA", "Δ"].map((h) => (
                  <th key={h} className="label px-3 py-2 text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {p.top_scorers.slice(1).map((sc, i) => {
                const delta = sc.goals - sc.xg;
                return (
                  <tr key={sc.player_name} className="border-b border-border-muted hover:bg-high">
                    <td className="px-3 py-2 text-muted">{i + 2}</td>
                    <td className="px-3 py-2 text-primary">
                      <Link
                        href={`/players/${playerSlug(sc.player_name)}`}
                        className="inline-flex items-center gap-2 hover:text-neon"
                      >
                        {sc.photo_url ? (
                          /* eslint-disable-next-line @next/next/no-img-element */
                          <img
                            src={sc.photo_url}
                            alt=""
                            loading="lazy"
                            className="h-7 w-7 rounded-full object-cover border border-border"
                          />
                        ) : (
                          <span className="h-7 w-7 rounded-full bg-high border border-border inline-flex items-center justify-center text-[10px] text-secondary">
                            {sc.player_name[0]?.toUpperCase() ?? "?"}
                          </span>
                        )}
                        {sc.player_name}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-muted">{sc.position ?? "-"}</td>
                    <td className="px-3 py-2 tabular-nums">{sc.goals}</td>
                    <td className="px-3 py-2 tabular-nums text-secondary">{sc.xg.toFixed(1)}</td>
                    <td className="px-3 py-2 tabular-nums">{sc.assists}</td>
                    <td className="px-3 py-2 tabular-nums text-secondary">{sc.xa.toFixed(1)}</td>
                    <td
                      className={
                        "px-3 py-2 tabular-nums " +
                        (delta > 0.5 ? "text-neon" : delta < -0.5 ? "text-error" : "text-muted")
                      }
                    >
                      {delta > 0 ? "+" : ""}
                      {delta.toFixed(1)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      )}

      {/* Fixtures grid */}
      <section className="grid md:grid-cols-2 gap-4">
        <div className="card space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="label">{t("team.recent")}</h2>
            <span className="font-mono text-[10px] text-muted">{p.recent.length}</span>
          </div>
          {p.recent.length === 0 ? (
            <p className="text-muted text-sm">{t("team.none")}</p>
          ) : (
            <ul className="divide-y divide-border/60">
              {p.recent.map((f) => {
                const res = fixtureResult(f);
                return (
                  <li key={f.id}>
                    <Link href={`/match/${f.id}`} className="flex items-center gap-3 py-2 hover:text-neon">
                      <span
                        className={
                          "h-2 w-2 rounded-full shrink-0 " +
                          (res === "W" ? "bg-neon" : res === "L" ? "bg-error" : "bg-muted")
                        }
                      />
                      <span className="font-mono text-xs text-muted w-20 shrink-0">
                        {formatShortDate(f.kickoff_time, lang)}
                      </span>
                      <span className="flex-1 truncate font-mono text-sm">
                        {f.home_short}{" "}
                        <span className="text-neon tabular-nums">
                          {f.home_goals ?? "-"}–{f.away_goals ?? "-"}
                        </span>{" "}
                        {f.away_short}
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
        <div className="card space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="label">{t("team.upcoming")}</h2>
            <span className="font-mono text-[10px] text-muted">{p.upcoming.length}</span>
          </div>
          {p.upcoming.length === 0 ? (
            <p className="text-muted text-sm">{t("team.none")}</p>
          ) : (
            <ul className="divide-y divide-border/60">
              {p.upcoming.map((f) => (
                <li key={f.id}>
                  <Link href={`/match/${f.id}`} className="flex items-center gap-3 py-2 hover:text-neon">
                    <span className="h-2 w-2 rounded-full bg-secondary shrink-0" />
                    <span className="font-mono text-xs text-muted w-20 shrink-0">
                      {formatShortDate(f.kickoff_time, lang)}
                    </span>
                    <span className="flex-1 truncate font-mono text-sm">
                      {f.home_short} <span className="text-muted">vs</span> {f.away_short}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </main>
  );
}
