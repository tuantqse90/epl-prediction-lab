import Link from "next/link";

import TeamLogo from "@/components/TeamLogo";
import { getLang, tFor } from "@/lib/i18n-server";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type FplPick = {
  fpl_id: number;
  web_name: string;
  full_name: string;
  position: string;
  team_slug: string;
  team_short: string;
  price_m: number;
  total_points: number;
  season_xg: number;
  season_games: number;
  value: number;
};

async function fetchPicks(position?: string, limit = 30): Promise<FplPick[]> {
  const qs = new URLSearchParams({ limit: String(limit), min_games: "3" });
  if (position) qs.set("position", position);
  const res = await fetch(`${BASE}/api/fpl/value?${qs}`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

const POSITIONS = ["ALL", "GK", "DEF", "MID", "FWD"] as const;

export default async function FplPage({
  searchParams,
}: {
  searchParams: Promise<{ pos?: string }>;
}) {
  const sp = await searchParams;
  const pos = POSITIONS.includes(sp.pos as (typeof POSITIONS)[number])
    ? (sp.pos as (typeof POSITIONS)[number])
    : "ALL";
  const lang = await getLang();
  const t = tFor(lang);
  const picks = await fetchPicks(pos === "ALL" ? undefined : pos);

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">FPL · 2025/26 · Value = xG / £m</p>
        <h1 className="headline-section">
          {lang === "vi" ? "FPL giá trị — xG rẻ nhất" : "FPL value — cheapest xG"}
        </h1>
        <p className="text-secondary max-w-2xl">
          {lang === "vi"
            ? "Ai đang sinh ra nhiều xG nhất mỗi £m giá FPL? Model gợi ý cầu thủ underpriced cho đội hình của bạn."
            : "Who generates the most xG per £m? Use this to spot underpriced FPL picks before the market catches on."}
        </p>
      </header>

      <nav className="flex flex-wrap gap-2">
        {POSITIONS.map((p) => (
          <Link
            key={p}
            href={p === "ALL" ? "/fpl" : `/fpl?pos=${p}`}
            className={
              "rounded-full px-3 py-1 font-mono text-xs uppercase tracking-wide border " +
              (pos === p
                ? "border-neon bg-neon text-on-neon"
                : "border-border text-secondary hover:border-neon hover:text-neon")
            }
          >
            {p}
          </Link>
        ))}
      </nav>

      {picks.length === 0 ? (
        <div className="card text-muted">No data yet. Run ingest_players to seed xG.</div>
      ) : (
        <div className="card p-0 overflow-x-auto">
          <table className="w-full font-mono text-sm">
            <thead className="text-muted">
              <tr className="border-b border-border">
                {["#", "Player", "Team", "Pos", "Price", "xG", "GP", "xG/£m", "FPL pts"].map((h) => (
                  <th key={h} className="label px-3 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {picks.map((p, i) => (
                <tr key={p.fpl_id} className="border-b border-border-muted hover:bg-high">
                  <td className="px-3 py-2 text-muted tabular-nums">{i + 1}</td>
                  <td className="px-3 py-2 text-primary">{p.web_name}</td>
                  <td className="px-3 py-2">
                    <Link href={`/teams/${p.team_slug}`} className="inline-flex items-center gap-2 hover:text-neon">
                      <TeamLogo slug={p.team_slug} name={p.team_short} size={18} />
                      <span className="text-secondary">{p.team_short}</span>
                    </Link>
                  </td>
                  <td className="px-3 py-2 text-muted">{p.position}</td>
                  <td className="px-3 py-2 tabular-nums">£{p.price_m.toFixed(1)}</td>
                  <td className="px-3 py-2 tabular-nums text-secondary">{p.season_xg.toFixed(1)}</td>
                  <td className="px-3 py-2 tabular-nums text-muted">{p.season_games}</td>
                  <td className="px-3 py-2 tabular-nums text-neon">{p.value.toFixed(2)}</td>
                  <td className="px-3 py-2 tabular-nums">{p.total_points}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-[11px] text-muted">
        Value = season xG ÷ FPL price in £m. FPL data cached 30 min.
      </p>
    </main>
  );
}
