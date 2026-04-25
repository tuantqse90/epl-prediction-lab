import type { Metadata } from "next";
import Link from "next/link";

import TeamLogo from "@/components/TeamLogo";
import { getLang, getLeagueSlug, leagueForApi, tFor } from "@/lib/i18n-server";
import { alternatesFor } from "@/lib/seo";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Players — searchable browse · predictor.nullshift.sh",
  description:
    "Every tracked player this season, sortable by goals + searchable by name. " +
    "Click a card for full xG / xA / games history.",
  alternates: alternatesFor("/players"),
};

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";
const PAGE_SIZE = 48;
const MAX_PAGE = 25;

type BrowseRow = {
  slug: string;
  player_name: string;
  team_slug: string;
  team_short: string;
  team_name: string;
  position: string | null;
  goals: number;
  assists: number;
  xg: number;
  games: number;
  photo_url: string | null;
  league_code: string | null;
};

type BrowseOut = {
  players: BrowseRow[];
  total_returned: number;
  has_next: boolean;
};

async function fetchPlayers(page: number, q: string, league?: string): Promise<BrowseOut> {
  const qs = new URLSearchParams({
    season: "2025-26",
    limit: String(PAGE_SIZE),
    offset: String((page - 1) * PAGE_SIZE),
  });
  if (q.trim()) qs.set("q", q.trim());
  if (league) qs.set("league", league);
  const res = await fetch(`${BASE}/api/players?${qs}`, { cache: "no-store" });
  if (!res.ok) return { players: [], total_returned: 0, has_next: false };
  return res.json();
}

export default async function PlayersIndexPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; p?: string }>;
}) {
  const sp = await searchParams;
  const q = sp.q ?? "";
  const page = Math.max(1, Math.min(MAX_PAGE, Number(sp.p ?? "1") || 1));

  const lang = await getLang();
  const t = tFor(lang);
  const leagueSlug = await getLeagueSlug();
  const leagueApi = leagueForApi(leagueSlug);

  const data = await fetchPlayers(page, q, leagueApi);

  const qp = (next: { q?: string; p?: number }) => {
    const out = new URLSearchParams();
    const qv = (next.q ?? q).trim();
    if (qv) out.set("q", qv);
    if ((next.p ?? page) > 1) out.set("p", String(next.p ?? page));
    return out.toString();
  };

  const lastPage = data.has_next ? page + 1 : page;
  const pageWindow: (number | "…")[] = (() => {
    const pages: (number | "…")[] = [];
    for (let i = 1; i <= lastPage; i++) {
      if (i === 1 || i === lastPage || (i >= page - 1 && i <= page + 1)) {
        pages.push(i);
      } else if (pages[pages.length - 1] !== "…") {
        pages.push("…");
      }
    }
    return pages;
  })();

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">2025-26</p>
        <h1 className="headline-section">
          {lang === "vi" ? "Duyệt cầu thủ" : "Browse players"}
        </h1>
        <p className="text-secondary max-w-2xl">
          {lang === "vi"
            ? "Tất cả cầu thủ được theo dõi mùa này. Sắp xếp theo bàn thắng. Click card để xem lịch sử đầy đủ (xG/xA/đội từng đá)."
            : "Every player tracked this season, sorted by goals. Click a card for full xG / xA history."}
        </p>
      </header>

      {/* Search form — GET-based so URL is shareable */}
      <form action="/players" method="get" className="flex flex-wrap items-center gap-2">
        <input
          type="search"
          name="q"
          defaultValue={q}
          placeholder={lang === "vi" ? "Tìm cầu thủ…" : "Search player…"}
          className="flex-1 min-w-[200px] bg-high border border-border rounded-full px-4 py-2 font-mono text-sm text-primary placeholder:text-muted focus:outline-none focus:border-neon"
        />
        <button
          type="submit"
          className="rounded-full border border-neon bg-neon text-on-neon px-4 py-2 font-mono text-xs uppercase tracking-wide"
        >
          {lang === "vi" ? "Tìm" : "Search"}
        </button>
        {q && (
          <Link
            href="/players"
            className="rounded-full border border-border text-secondary hover:border-neon hover:text-neon px-4 py-2 font-mono text-xs uppercase tracking-wide"
          >
            {lang === "vi" ? "Xoá" : "Clear"}
          </Link>
        )}
      </form>

      {data.players.length === 0 ? (
        <div className="card text-muted">
          {q
            ? (lang === "vi" ? `Không có cầu thủ nào khớp "${q}".` : `No players match "${q}".`)
            : (lang === "vi" ? "Chưa có dữ liệu." : "No data.")}
        </div>
      ) : (
        <>
          <p className="font-mono text-[11px] text-muted">
            {lang === "vi"
              ? `Hiển thị ${data.players.length} cầu thủ · Trang ${page}`
              : `Showing ${data.players.length} players · Page ${page}`}
          </p>

          <section className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {data.players.map((p) => (
              <Link
                key={p.slug + p.team_slug}
                href={`/players/${p.slug}`}
                className="rounded-xl border border-border bg-raised p-4 hover:border-neon transition-colors flex flex-col gap-3"
              >
                <div className="flex items-center gap-3">
                  {p.photo_url ? (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img
                      src={p.photo_url}
                      alt=""
                      loading="lazy"
                      className="h-12 w-12 rounded-full object-cover border border-border"
                    />
                  ) : (
                    <span className="h-12 w-12 rounded-full bg-high border border-border inline-flex items-center justify-center text-[14px] font-display uppercase text-secondary">
                      {p.player_name[0]?.toUpperCase() ?? "?"}
                    </span>
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="font-display text-sm font-semibold text-primary truncate">{p.player_name}</p>
                    <p className="font-mono text-[10px] text-muted truncate">
                      {p.position ?? "—"} · {p.team_short}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-1 text-[10px] font-mono">
                  <TeamLogo slug={p.team_slug} name={p.team_name} size={14} />
                  <span className="text-muted uppercase tracking-wide">{p.team_short}</span>
                </div>

                <div className="flex items-baseline gap-3 pt-1 border-t border-border-muted font-mono">
                  <div>
                    <p className="text-[9px] uppercase tracking-wide text-muted">G</p>
                    <p className="stat text-lg leading-none text-neon">{p.goals}</p>
                  </div>
                  <div>
                    <p className="text-[9px] uppercase tracking-wide text-muted">xG</p>
                    <p className="stat text-lg leading-none text-secondary">{p.xg.toFixed(1)}</p>
                  </div>
                  <div>
                    <p className="text-[9px] uppercase tracking-wide text-muted">A</p>
                    <p className="stat text-lg leading-none">{p.assists}</p>
                  </div>
                  <div>
                    <p className="text-[9px] uppercase tracking-wide text-muted">GP</p>
                    <p className="stat text-lg leading-none text-muted">{p.games}</p>
                  </div>
                </div>
              </Link>
            ))}
          </section>

          {/* Pagination */}
          <nav className="flex items-center justify-center gap-1 flex-wrap font-mono text-xs">
            {page > 1 ? (
              <Link
                href={`/players?${qp({ p: page - 1 })}`}
                className="rounded-full px-3 py-1 border border-border text-secondary hover:border-neon hover:text-neon"
              >
                ← {lang === "vi" ? "Trước" : "Prev"}
              </Link>
            ) : (
              <span className="rounded-full px-3 py-1 border border-border-muted text-muted opacity-50">
                ← {lang === "vi" ? "Trước" : "Prev"}
              </span>
            )}

            {pageWindow.map((pp, i) =>
              pp === "…" ? (
                <span key={`gap-${i}`} className="px-2 text-muted">…</span>
              ) : (
                <Link
                  key={pp}
                  href={`/players?${qp({ p: pp })}`}
                  className={
                    "rounded-full px-3 py-1 border " +
                    (pp === page
                      ? "border-neon bg-neon text-on-neon"
                      : "border-border text-secondary hover:border-neon hover:text-neon")
                  }
                >
                  {pp}
                </Link>
              )
            )}

            {data.has_next && page < MAX_PAGE ? (
              <Link
                href={`/players?${qp({ p: page + 1 })}`}
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
