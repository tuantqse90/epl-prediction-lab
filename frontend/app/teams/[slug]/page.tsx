import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import SeasonTrajectoryChart from "@/components/SeasonTrajectoryChart";
import TeamLogo from "@/components/TeamLogo";
import { formatShortDate } from "@/lib/date";
import { getLang, tFor } from "@/lib/i18n-server";
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
  const title = p.name;
  const s = p.stats;
  const desc = `EPL ${p.season}: ${s.played}P · ${s.wins}W-${s.draws}D-${s.losses}L · ${s.points} pts · xG diff ${(s.xg_for - s.xg_against).toFixed(1)}.`;
  return { title, description: desc, openGraph: { title, description: desc, url: `/teams/${slug}` } };
}


async function fetchProfile(slug: string): Promise<TeamProfile | null> {
  const res = await fetch(`${BASE}/api/teams/${slug}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`profile: ${res.status}`);
  return res.json();
}

function formColor(r: string) {
  if (r === "W") return "text-neon";
  if (r === "L") return "text-error";
  return "text-muted";
}

function fixtureLine(f: FixtureBrief, lang: "vi" | "en") {
  const date = formatShortDate(f.kickoff_time, lang);
  const score =
    f.home_goals !== null && f.away_goals !== null
      ? `${f.home_goals}-${f.away_goals}`
      : "vs";
  return { date, home: f.home_short, away: f.away_short, score };
}

export default async function TeamPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const lang = await getLang();
  const t = tFor(lang);
  const p = await fetchProfile(slug);
  if (!p) notFound();

  const s = p.stats;
  const xgDiff = s.xg_for - s.xg_against;
  const color = colorFor(p.slug);

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>

      <header className="relative -mx-6 overflow-hidden rounded-xl p-6 space-y-3">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-25"
          style={{ background: `radial-gradient(closest-side at 20% 50%, ${color}, transparent 60%)` }}
        />
        <div className="relative space-y-3">
          <p className="font-mono text-xs text-muted">{t("common.season")} {p.season}</p>
          <h1 className="flex flex-wrap items-center gap-4">
            <TeamLogo slug={p.slug} name={p.name} size={72} />
            <span className="headline-hero">{p.name}</span>
          </h1>
        </div>
      </header>

      <SeasonTrajectoryChart slug={p.slug} season={p.season} lang={lang} />

      <section className="card grid grid-cols-2 md:grid-cols-5 gap-5">
        <div>
          <p className="text-xs text-muted">{t("team.played")}</p>
          <p className="stat">{s.played}</p>
        </div>
        <div>
          <p className="text-xs text-muted">{t("team.record")}</p>
          <p className="stat">{s.wins}-{s.draws}-{s.losses}</p>
        </div>
        <div>
          <p className="text-xs text-muted">{t("team.points")}</p>
          <p className="stat text-neon">{s.points}</p>
        </div>
        <div>
          <p className="text-xs text-muted">{t("team.goals")}</p>
          <p className="stat">{s.goals_for}–{s.goals_against}</p>
        </div>
        <div>
          <p className="text-xs text-muted">{t("team.xgDiff")}</p>
          <p className={`stat ${xgDiff > 0.5 ? "text-neon" : xgDiff < -0.5 ? "text-error" : ""}`}>
            {xgDiff > 0 ? "+" : ""}
            {xgDiff.toFixed(1)}
          </p>
        </div>
      </section>

      <section className="card space-y-3">
        <p className="text-sm text-muted">{t("team.form")}</p>
        <div className="flex gap-2 font-mono text-2xl">
          {p.form.length === 0 && <span className="text-muted text-sm">{t("team.form.none")}</span>}
          {p.form.map((r, i) => (
            <span key={i} className={formColor(r)}>{r}</span>
          ))}
        </div>
      </section>

      <section className="card">
        <h2 className="font-display font-semibold uppercase tracking-tight mb-3">
          {t("team.topScorers")}
        </h2>
        {p.top_scorers.length === 0 ? (
          <p className="text-muted text-sm">{t("team.topScorers.empty", { season: p.season })}</p>
        ) : (
          <table className="w-full font-mono text-sm">
            <thead className="text-muted">
              <tr className="border-b border-border">
                {["#", "player", "pos", "G", "xG", "A", "xA", "Δ"].map((h) => (
                  <th key={h} className="label px-2 py-2 text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {p.top_scorers.map((sc, i) => {
                const delta = sc.goals - sc.xg;
                return (
                  <tr key={sc.player_name} className="border-b border-border-muted">
                    <td className="px-2 py-2 text-muted">{i + 1}</td>
                    <td className="px-2 py-2 text-primary">{sc.player_name}</td>
                    <td className="px-2 py-2 text-muted">{sc.position ?? "-"}</td>
                    <td className="px-2 py-2 tabular-nums">{sc.goals}</td>
                    <td className="px-2 py-2 tabular-nums text-secondary">{sc.xg.toFixed(1)}</td>
                    <td className="px-2 py-2 tabular-nums">{sc.assists}</td>
                    <td className="px-2 py-2 tabular-nums text-secondary">{sc.xa.toFixed(1)}</td>
                    <td
                      className={`px-2 py-2 tabular-nums ${
                        delta > 0.5 ? "text-neon" : delta < -0.5 ? "text-error" : "text-muted"
                      }`}
                    >
                      {delta > 0 ? "+" : ""}
                      {delta.toFixed(1)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>

      <section className="grid md:grid-cols-2 gap-6">
        <div className="card space-y-3">
          <p className="text-sm text-muted">{t("team.recent")}</p>
          {p.recent.length === 0 ? (
            <p className="text-muted text-sm">{t("team.none")}</p>
          ) : (
            <ul className="space-y-1 font-mono text-sm">
              {p.recent.map((f) => {
                const l = fixtureLine(f, lang);
                return (
                  <li key={f.id}>
                    <Link href={`/match/${f.id}`} className="hover:text-neon">
                      <span className="text-muted mr-3">{l.date}</span>
                      <span>{l.home}</span>{" "}
                      <span className="text-neon">{l.score}</span>{" "}
                      <span>{l.away}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
        <div className="card space-y-3">
          <p className="text-sm text-muted">{t("team.upcoming")}</p>
          {p.upcoming.length === 0 ? (
            <p className="text-muted text-sm">{t("team.none")}</p>
          ) : (
            <ul className="space-y-1 font-mono text-sm">
              {p.upcoming.map((f) => {
                const l = fixtureLine(f, lang);
                return (
                  <li key={f.id}>
                    <Link href={`/match/${f.id}`} className="hover:text-neon">
                      <span className="text-muted mr-3">{l.date}</span>
                      <span>{l.home}</span>{" "}
                      <span className="text-muted">{l.score}</span>{" "}
                      <span>{l.away}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </section>
    </main>
  );
}
