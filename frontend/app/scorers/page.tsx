import Link from "next/link";

import TeamLogo from "@/components/TeamLogo";
import { getLang, getLeagueSlug, leagueForApi, tFor } from "@/lib/i18n-server";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";
const PAGE_SIZE = 50;
// Enough to cover every scorer with ≥ 1 goal in a top-5 season (max ~1,300
// rows against the cap means ~26 pages) without risking abusive deep pagination.
const MAX_PAGE = 20;

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
  photo_url: string | null;
};

async function fetchScorers(
  season: string, sort: string, page: number, league?: string,
): Promise<ScorerOut[]> {
  const offset = (page - 1) * PAGE_SIZE;
  const qs = new URLSearchParams({ season, sort, limit: String(PAGE_SIZE), offset: String(offset) });
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
  searchParams: Promise<{ sort?: string; season?: string; p?: string }>;
}) {
  const sp = await searchParams;
  const season = sp.season ?? "2025-26";
  const sort = sp.sort ?? "goals";
  const page = Math.max(1, Math.min(MAX_PAGE, Number(sp.p ?? "1") || 1));
  const lang = await getLang();
  const league = await getLeagueSlug();
  const t = tFor(lang);

  // Fetch current page + one extra row to detect whether a next page exists
  // without a separate COUNT(*) round-trip.
  const overfetchQs = new URLSearchParams({
    season, sort,
    limit: String(PAGE_SIZE + 1),
    offset: String((page - 1) * PAGE_SIZE),
  });
  const leagueApi = leagueForApi(league);
  if (leagueApi) overfetchQs.set("league", leagueApi);
  const overfetchRes = await fetch(`${BASE}/api/stats/scorers?${overfetchQs}`, { cache: "no-store" });
  const allRows: ScorerOut[] = overfetchRes.ok ? await overfetchRes.json() : [];
  const hasNext = allRows.length > PAGE_SIZE;
  const rows = allRows.slice(0, PAGE_SIZE);

  const sorts: Array<{ key: string; label: string }> = [
    { key: "goals", label: t("scorers.sortGoals") },
    { key: "xg", label: t("scorers.sortXg") },
    { key: "assists", label: t("scorers.sortAssists") },
    { key: "goals_minus_xg", label: t("scorers.sortDelta") },
  ];

  const qp = (next: { sort?: string; p?: number }) => {
    const out = new URLSearchParams();
    out.set("sort", next.sort ?? sort);
    if ((next.p ?? page) > 1) out.set("p", String(next.p ?? page));
    return out.toString();
  };

  // Compact page window: always show 1, always show last-known (current + next
  // if available), plus ±1 around current with ellipsis between.
  const lastVisiblePage = hasNext ? page + 1 : page;
  const pageWindow: (number | "…")[] = (() => {
    const pages: (number | "…")[] = [];
    for (let i = 1; i <= lastVisiblePage; i++) {
      if (i === 1 || i === lastVisiblePage || (i >= page - 1 && i <= page + 1)) {
        pages.push(i);
      } else if (pages[pages.length - 1] !== "…") {
        pages.push("…");
      }
    }
    return pages;
  })();

  const rangeStart = (page - 1) * PAGE_SIZE + 1;
  const rangeEnd = rangeStart + rows.length - 1;

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
            href={`/scorers?${qp({ sort: s.key, p: 1 })}`}
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
        <>
          <div className="flex items-baseline justify-between gap-2 font-mono text-[11px] text-muted">
            <span>
              {lang === "vi"
                ? `Hiển thị ${rangeStart}–${rangeEnd}`
                : `Showing ${rangeStart}–${rangeEnd}`}
            </span>
            <span>
              {lang === "vi" ? `Trang ${page}` : `Page ${page}`}
            </span>
          </div>

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
                  <tr key={`${r.team_slug}-${r.player_name}-${r.rank}`} className="border-b border-border-muted hover:bg-high">
                    <td className="px-3 py-2 text-muted tabular-nums">{r.rank}</td>
                    <td className="px-3 py-2 text-primary">
                      <div className="inline-flex items-center gap-2">
                        {r.photo_url ? (
                          /* eslint-disable-next-line @next/next/no-img-element */
                          <img
                            src={r.photo_url}
                            alt=""
                            loading="lazy"
                            className="h-7 w-7 rounded-full object-cover border border-border"
                          />
                        ) : (
                          <span className="h-7 w-7 rounded-full bg-high border border-border inline-flex items-center justify-center text-[10px] text-secondary">
                            {r.player_name[0]?.toUpperCase() ?? "?"}
                          </span>
                        )}
                        {r.player_name}
                      </div>
                    </td>
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

          {/* Pagination */}
          <nav className="flex items-center justify-center gap-1 flex-wrap font-mono text-xs">
            {page > 1 ? (
              <Link
                href={`/scorers?${qp({ p: page - 1 })}`}
                className="rounded-full px-3 py-1 border border-border text-secondary hover:border-neon hover:text-neon"
              >
                ← {lang === "vi" ? "Trước" : "Prev"}
              </Link>
            ) : (
              <span className="rounded-full px-3 py-1 border border-border-muted text-muted opacity-50">
                ← {lang === "vi" ? "Trước" : "Prev"}
              </span>
            )}

            {pageWindow.map((p, i) =>
              p === "…" ? (
                <span key={`gap-${i}`} className="px-2 text-muted">…</span>
              ) : (
                <Link
                  key={p}
                  href={`/scorers?${qp({ p })}`}
                  className={
                    "rounded-full px-3 py-1 border " +
                    (p === page
                      ? "border-neon bg-neon text-on-neon"
                      : "border-border text-secondary hover:border-neon hover:text-neon")
                  }
                >
                  {p}
                </Link>
              )
            )}

            {hasNext && page < MAX_PAGE ? (
              <Link
                href={`/scorers?${qp({ p: page + 1 })}`}
                className="rounded-full px-3 py-1 border border-border text-secondary hover:border-neon hover:text-neon"
              >
                {lang === "vi" ? "Tiếp" : "Next"} →
              </Link>
            ) : (
              <span className="rounded-full px-3 py-1 border border-border-muted text-muted opacity-50">
                {lang === "vi" ? "Tiếp" : "Next"} →
              </span>
            )}
          </nav>
        </>
      )}
    </main>
  );
}
