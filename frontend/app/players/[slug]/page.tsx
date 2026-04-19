import Link from "next/link";
import { notFound } from "next/navigation";

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
  seasons: Season[];
  career_goals: number;
  career_xg: number;
  career_assists: number;
  career_games: number;
};

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

  return (
    <main className="mx-auto max-w-4xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">
          {latest?.position ?? ""}{latest?.position ? " · " : ""}
          <Link href={`/teams/${latest?.team_slug}`} className="hover:text-neon">
            {latest?.team_short}
          </Link>
        </p>
        <h1 className="headline-section">{p.player_name}</h1>
      </header>

      <section className="card grid grid-cols-2 md:grid-cols-4 gap-6">
        <div>
          <p className="label">Career goals</p>
          <p className="stat text-neon">{p.career_goals}</p>
        </div>
        <div>
          <p className="label">Career xG</p>
          <p className="stat">{p.career_xg.toFixed(1)}</p>
        </div>
        <div>
          <p className="label">Assists</p>
          <p className="stat">{p.career_assists}</p>
        </div>
        <div>
          <p className="label">Apps</p>
          <p className="stat">{p.career_games}</p>
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
