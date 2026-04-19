import Link from "next/link";

import { getLang, getLeagueSlug, leagueForApi, tFor } from "@/lib/i18n-server";
import { getLeague, leagueByCode } from "@/lib/leagues";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type NewsItem = {
  source: string;
  url: string;
  title: string;
  summary: string | null;
  published_at: string;
  teams: string[];
  league_code: string | null;
};

async function fetchNews(league?: string): Promise<NewsItem[]> {
  const qs = new URLSearchParams({ limit: "40" });
  if (league) qs.set("league", league);
  const res = await fetch(`${BASE}/api/news?${qs}`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

const SOURCE_LABEL: Record<string, string> = {
  bbc: "BBC Sport",
  guardian: "Guardian",
  espn: "ESPN",
  goal: "Goal",
};

function formatAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const h = Math.floor(mins / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export default async function NewsPage() {
  const lang = await getLang();
  const t = tFor(lang);
  const league = await getLeagueSlug();
  const leagueInfo = getLeague(league);
  const items = await fetchNews(leagueForApi(league));
  const leagueLabel = lang === "vi" ? leagueInfo.name_vi : leagueInfo.name_en;

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>

      <header className="space-y-2">
        <p className="font-mono text-xs text-muted">
          {leagueInfo.emoji} {leagueLabel}
        </p>
        <h1 className="headline-section">
          {lang === "vi" ? "Tin bóng đá" : "Football news"}
        </h1>
        <p className="text-secondary max-w-2xl">
          {lang === "vi"
            ? "Tổng hợp headline từ BBC Sport, Guardian, ESPN, Goal. Cập nhật hàng ngày."
            : "Headlines aggregated from BBC Sport, Guardian, ESPN, Goal. Refreshed daily."}
        </p>
      </header>

      {items.length === 0 ? (
        <div className="card text-muted">
          {lang === "vi" ? "Chưa có tin nào. Chạy ingest_news.py." : "No items yet. Run ingest_news.py."}
        </div>
      ) : (
        <ul className="space-y-3">
          {items.map((n) => {
            const lg = leagueByCode(n.league_code);
            return (
              <li key={n.url}>
                <a
                  href={n.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="card flex flex-col gap-2 hover:border-neon transition-colors"
                >
                  <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wide text-muted">
                    <span className="rounded bg-high px-1.5 py-0.5 text-secondary">
                      {SOURCE_LABEL[n.source] ?? n.source}
                    </span>
                    {lg && <span>{lg.emoji} {lg.short}</span>}
                    <span>·</span>
                    <span>{formatAgo(n.published_at)}</span>
                  </div>
                  <p className="font-display font-semibold text-lg leading-snug">
                    {n.title}
                  </p>
                  {n.summary && (
                    <p className="text-secondary text-sm line-clamp-2">{n.summary}</p>
                  )}
                  {n.teams.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-1 font-mono text-[10px] uppercase tracking-wide text-secondary">
                      {n.teams.slice(0, 4).map((slug) => (
                        <span
                          key={slug}
                          className="rounded-full bg-high px-2 py-0.5"
                        >
                          {slug}
                        </span>
                      ))}
                    </div>
                  )}
                </a>
              </li>
            );
          })}
        </ul>
      )}
    </main>
  );
}
