import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import AnimatedNumber from "@/components/AnimatedNumber";
import TeamLogo from "@/components/TeamLogo";
import { getLang, tFor } from "@/lib/i18n-server";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type Season = {
  season: string;
  team_slug: string;
  team_short: string;
  games: number;
  goals: number;
  assists: number;
  xg: number;
  xa: number;
  npxg: number;
  key_passes: number;
  position: string | null;
};

type Profile = {
  slug: string;
  player_name: string;
  photo_url: string | null;
  seasons: Season[];
  career_goals: number;
  career_xg: number;
  career_assists: number;
  career_games: number;
};

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const p = await fetchPlayer(slug);
  if (!p) return { title: "Player" };
  const desc =
    `${p.player_name} — ${p.career_goals} goals, ${p.career_xg.toFixed(1)} xG, ` +
    `${p.career_assists} assists across ${p.career_games} appearances. Full season history.`;
  return {
    title: `${p.player_name} · predictor.nullshift.sh`,
    description: desc,
    openGraph: {
      title: p.player_name,
      description: desc,
      images: p.photo_url ? [p.photo_url] : undefined,
      type: "profile",
    },
    twitter: { card: "summary", title: p.player_name, description: desc },
  };
}

async function fetchPlayer(slug: string): Promise<Profile | null> {
  const res = await fetch(`${BASE}/api/players/${encodeURIComponent(slug)}`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export default async function PlayerPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const p = await fetchPlayer(slug);
  if (!p) notFound();

  const lang = await getLang();
  const t = tFor(lang);
  const latest = p.seasons[0];

  const careerDelta = p.career_goals - p.career_xg;

  return (
    <main className="mx-auto max-w-4xl px-6 py-12 space-y-8">
      <nav className="flex items-center gap-2 font-mono text-xs text-muted" aria-label="Breadcrumb">
        <Link href="/" className="hover:text-neon">Home</Link>
        <span aria-hidden>/</span>
        <Link href="/scorers" className="hover:text-neon">Scorers</Link>
        {latest && (
          <>
            <span aria-hidden>/</span>
            <Link href={`/teams/${latest.team_slug}`} className="hover:text-neon">{latest.team_short}</Link>
          </>
        )}
        <span aria-hidden>/</span>
        <span className="text-secondary truncate">{p.player_name}</span>
      </nav>

      {/* Hero: photo + name + current team */}
      <header className="card relative overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-30"
          style={{
            background:
              "radial-gradient(closest-side at 20% 30%, rgba(224,255,50,0.25), transparent 60%)",
          }}
        />
        <div className="relative flex items-center gap-6 flex-wrap">
          {p.photo_url ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={p.photo_url}
              alt={p.player_name}
              loading="eager"
              className="h-28 w-28 rounded-full object-cover border-4 border-neon/40 shadow-[0_0_28px_rgba(224,255,50,0.25)] shrink-0"
            />
          ) : (
            <div className="h-28 w-28 rounded-full bg-high border-4 border-border flex items-center justify-center font-display text-3xl text-secondary shrink-0">
              {p.player_name
                .split(/\s+/).slice(0, 2)
                .map((w) => w[0]?.toUpperCase() ?? "")
                .join("")}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <p className="font-mono text-xs text-muted">
              {latest?.position ?? ""}{latest?.position ? " · " : ""}
              {latest && (
                <Link href={`/teams/${latest.team_slug}`} className="inline-flex items-center gap-1 hover:text-neon">
                  <TeamLogo slug={latest.team_slug} name={latest.team_short} size={14} />
                  {latest.team_short}
                </Link>
              )}
            </p>
            <h1 className="headline-section mt-2">{p.player_name}</h1>
          </div>
        </div>
      </header>

      <section className="card grid grid-cols-2 md:grid-cols-4 gap-6">
        <div>
          <p className="label">Career goals</p>
          <AnimatedNumber value={p.career_goals} className="stat text-neon block" />
        </div>
        <div>
          <p className="label">Career xG</p>
          <AnimatedNumber value={p.career_xg} decimals={1} className="stat block" />
        </div>
        <div>
          <p className="label">G − xG</p>
          <AnimatedNumber
            value={careerDelta}
            decimals={1}
            prefix={careerDelta > 0 ? "+" : ""}
            className={
              "stat block " +
              (careerDelta > 2 ? "text-neon" : careerDelta < -2 ? "text-error" : "")
            }
          />
        </div>
        <div>
          <p className="label">Apps</p>
          <AnimatedNumber value={p.career_games} className="stat block" />
        </div>
      </section>

      <section className="card p-0 overflow-x-auto">
        <table className="w-full font-mono text-sm">
          <thead className="text-muted">
            <tr className="border-b border-border">
              {["Season", "Team", "Apps", "G", "xG", "G−xG", "A", "xA", "KP"].map((h) => (
                <th key={h} className="label px-3 py-3 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {p.seasons.map((s) => {
              const delta = s.goals - s.xg;
              return (
                <tr key={`${s.season}-${s.team_slug}`} className="border-b border-border-muted">
                  <td className="px-3 py-2 tabular-nums">{s.season}</td>
                  <td className="px-3 py-2">
                    <Link href={`/teams/${s.team_slug}`} className="inline-flex items-center gap-2 hover:text-neon">
                      <TeamLogo slug={s.team_slug} name={s.team_short} size={16} />
                      {s.team_short}
                    </Link>
                  </td>
                  <td className="px-3 py-2 tabular-nums text-muted">{s.games}</td>
                  <td className="px-3 py-2 tabular-nums text-primary">{s.goals}</td>
                  <td className="px-3 py-2 tabular-nums text-secondary">{s.xg.toFixed(1)}</td>
                  <td
                    className={
                      "px-3 py-2 tabular-nums " +
                      (delta > 1 ? "text-neon" : delta < -1 ? "text-error" : "text-muted")
                    }
                  >
                    {delta > 0 ? "+" : ""}{delta.toFixed(1)}
                  </td>
                  <td className="px-3 py-2 tabular-nums">{s.assists}</td>
                  <td className="px-3 py-2 tabular-nums text-secondary">{s.xa.toFixed(1)}</td>
                  <td className="px-3 py-2 tabular-nums text-muted">{s.key_passes}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </main>
  );
}
