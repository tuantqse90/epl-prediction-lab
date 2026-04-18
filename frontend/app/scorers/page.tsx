import Link from "next/link";

import TeamLogo from "@/components/TeamLogo";
import { getLang, getLeagueSlug, tFor } from "@/lib/i18n-server";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type ScorerOut = {
  rank: number;
  player_name: string;
  position: string | null;
  team_slug: string;
  team_name: string;
  team_short: string;
  games: number;
  goals: number;
  xg: number;
  npxg: number;
  assists: number;
  xa: number;
  key_passes: number;
  goals_minus_xg: number;
};

async function fetchScorers(season: string, sort: string, league?: string): Promise<ScorerOut[]> {
  const qs = new URLSearchParams({ season, sort, limit: "25" });
  if (league) qs.set("league", league);
  const res = await fetch(`${BASE}/api/stats/scorers?${qs}`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

function deltaClass(d: number) {
  if (d > 1) return "text-neon";
  if (d < -1) return "text-error";
  return "text-muted";
}

export default async function ScorersPage({
  searchParams,
}: {
  searchParams: Promise<{ sort?: string; season?: string }>;
}) {
  const sp = await searchParams;
  const season = sp.season ?? "2025-26";
  const sort = sp.sort ?? "goals";
  const lang = await getLang();
  const league = await getLeagueSlug();
  const t = tFor(lang);

  const rows = await fetchScorers(season, sort, league);

  const sorts: Array<{ key: string; label: string }> = [
    { key: "goals", label: t("scorers.sortGoals") },
    { key: "xg", label: t("scorers.sortXg") },
    { key: "assists", label: t("scorers.sortAssists") },
    { key: "goals_minus_xg", label: t("scorers.sortDelta") },
  ];

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">{t("common.season")} {season}</p>
        <h1 className="headline-section">{t("scorers.title", { season })}</h1>
        <p className="text-secondary max-w-2xl">{t("scorers.subhead", { season })}</p>
      </header>

      <nav className="flex flex-wrap gap-2">
        {sorts.map((s) => (
          <Link
            key={s.key}
            href={`/scorers?sort=${s.key}`}
            className={
              "rounded-full px-3 py-1 font-mono text-xs uppercase tracking-wide border " +
              (sort === s.key
                ? "border-neon bg-neon text-on-neon"
                : "border-border text-secondary hover:border-neon hover:text-neon")
            }
          >
            {s.label}
          </Link>
        ))}
      </nav>

      {rows.length === 0 ? (
        <div className="card text-muted">{t("scorers.empty", { season })}</div>
      ) : (
        <div className="card p-0 overflow-x-auto">
          <table className="w-full font-mono text-sm">
            <thead className="text-muted">
              <tr className="border-b border-border">
                {["#", "player", "team", "pos", "G", "xG", "npxG", "Δ", "A", "xA", "KP", "GP"].map((h) => (
                  <th key={h} className="label px-3 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={`${r.team_slug}-${r.player_name}`} className="border-b border-border-muted hover:bg-high">
                  <td className="px-3 py-2 text-muted tabular-nums">{r.rank}</td>
                  <td className="px-3 py-2 text-primary">{r.player_name}</td>
                  <td className="px-3 py-2">
                    <Link href={`/teams/${r.team_slug}`} className="inline-flex items-center gap-2 hover:text-neon">
                      <TeamLogo slug={r.team_slug} name={r.team_name} size={18} />
                      <span className="text-secondary">{r.team_short}</span>
                    </Link>
                  </td>
                  <td className="px-3 py-2 text-muted">{r.position ?? "-"}</td>
                  <td className="px-3 py-2 tabular-nums text-primary">{r.goals}</td>
                  <td className="px-3 py-2 tabular-nums text-secondary">{r.xg.toFixed(1)}</td>
                  <td className="px-3 py-2 tabular-nums text-muted">{r.npxg.toFixed(1)}</td>
                  <td className={`px-3 py-2 tabular-nums ${deltaClass(r.goals_minus_xg)}`}>
                    {r.goals_minus_xg > 0 ? "+" : ""}
                    {r.goals_minus_xg.toFixed(1)}
                  </td>
                  <td className="px-3 py-2 tabular-nums">{r.assists}</td>
                  <td className="px-3 py-2 tabular-nums text-secondary">{r.xa.toFixed(1)}</td>
                  <td className="px-3 py-2 tabular-nums text-muted">{r.key_passes}</td>
                  <td className="px-3 py-2 tabular-nums text-muted">{r.games}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
