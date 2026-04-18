import Link from "next/link";

import TeamLogo from "@/components/TeamLogo";
import { getLang, tFor } from "@/lib/i18n-server";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type TableRow = {
  rank: number;
  slug: string;
  name: string;
  short_name: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  points: number;
  goals_for: number;
  goals_against: number;
  goal_diff: number;
  xg_for: number;
  xg_against: number;
  xg_diff: number;
};

async function fetchTable(season: string): Promise<TableRow[]> {
  const res = await fetch(`${BASE}/api/table?season=${encodeURIComponent(season)}`, {
    cache: "no-store",
  });
  if (!res.ok) return [];
  return res.json();
}

function deltaClass(diff: number) {
  if (diff > 0.5) return "text-neon";
  if (diff < -0.5) return "text-error";
  return "text-muted";
}

export default async function TablePage() {
  const season = "2025-26";
  const rows = await fetchTable(season);
  const lang = await getLang();
  const t = tFor(lang);

  const columns = [
    t("table.col.rank"),
    t("table.col.team"),
    t("table.col.played"),
    t("table.col.wins"),
    t("table.col.draws"),
    t("table.col.losses"),
    t("table.col.gf"),
    t("table.col.ga"),
    t("table.col.gd"),
    t("table.col.xgf"),
    t("table.col.xga"),
    t("table.col.xgd"),
  ];

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">{t("common.season")} {season}</p>
        <h1 className="headline-section">{t("table.title")}</h1>
        <p className="text-secondary max-w-2xl">{t("table.subhead")}</p>
      </header>

      {rows.length === 0 ? (
        <div className="card text-muted">{t("table.empty", { season })}</div>
      ) : (
        <div className="card p-0 overflow-x-auto">
          <table className="w-full font-mono text-sm">
            <thead className="text-muted">
              <tr className="border-b border-border">
                {columns.map((h) => (
                  <th key={h} className="label px-3 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.slug} className="border-b border-border-muted hover:bg-high">
                  <td className="px-3 py-2 text-muted tabular-nums">{r.rank}</td>
                  <td className="px-3 py-2 text-primary">
                    <Link href={`/teams/${r.slug}`} className="inline-flex items-center gap-2 hover:text-neon">
                      <TeamLogo slug={r.slug} name={r.name} size={20} />
                      {r.name}
                    </Link>
                  </td>
                  <td className="px-3 py-2 tabular-nums">{r.played}</td>
                  <td className="px-3 py-2 tabular-nums">{r.wins}</td>
                  <td className="px-3 py-2 tabular-nums">{r.draws}</td>
                  <td className="px-3 py-2 tabular-nums">{r.losses}</td>
                  <td className="px-3 py-2 tabular-nums">{r.goals_for}</td>
                  <td className="px-3 py-2 tabular-nums">{r.goals_against}</td>
                  <td className={`px-3 py-2 tabular-nums ${deltaClass(r.goal_diff)}`}>
                    {r.goal_diff > 0 ? `+${r.goal_diff}` : r.goal_diff}
                  </td>
                  <td className="px-3 py-2 tabular-nums text-secondary">{r.xg_for.toFixed(1)}</td>
                  <td className="px-3 py-2 tabular-nums text-secondary">{r.xg_against.toFixed(1)}</td>
                  <td className={`px-3 py-2 tabular-nums ${deltaClass(r.xg_diff)}`}>
                    {r.xg_diff > 0 ? `+${r.xg_diff.toFixed(1)}` : r.xg_diff.toFixed(1)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
