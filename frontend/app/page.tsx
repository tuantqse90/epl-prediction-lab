import Link from "next/link";

import FavoritesSection from "@/components/FavoritesSection";
import LivePoller from "@/components/LivePoller";
import MatchCard from "@/components/MatchCard";
import ProofStrip from "@/components/ProofStrip";
import PushButton from "@/components/PushButton";
import QuickPicks from "@/components/QuickPicks";
import RecentResults from "@/components/RecentResults";
import StarPlayersStrip from "@/components/StarPlayersStrip";
import TelegramCTA from "@/components/TelegramCTA";
import WorldCupCountdown from "@/components/WorldCupCountdown";
import { listMatches } from "@/lib/api";
import { getLang, getLeagueSlug, leagueForApi, tFor } from "@/lib/i18n-server";
import type { MatchOut } from "@/lib/types";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type Accuracy = {
  season: string;
  scored: number;
  correct: number;
  accuracy: number;
  baseline_home_accuracy: number;
  mean_log_loss: number;
  uniform_log_loss: number;
};

async function fetchAccuracy(league?: string): Promise<Accuracy | null> {
  try {
    const qs = new URLSearchParams({ season: "2025-26" });
    if (league) qs.set("league", league);
    const res = await fetch(`${BASE}/api/stats/accuracy?${qs}`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as Accuracy;
  } catch {
    return null;
  }
}

export const dynamic = "force-dynamic";

const PAGE_SIZE = 24;

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<{ p?: string }>;
}) {
  const lang = await getLang();
  const league = await getLeagueSlug();
  const t = tFor(lang);
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.p ?? "1") || 1);
  const offset = (page - 1) * PAGE_SIZE;

  const leagueParam = leagueForApi(league);
  let matches: MatchOut[] = [];
  let hasNext = false;
  let error: string | null = null;
  try {
    // Fetch PAGE_SIZE + 1 to cheaply detect whether a next page exists
    // without a separate COUNT(*) round-trip.
    const res = await listMatches({
      upcomingOnly: true,
      limit: PAGE_SIZE + 1,
      offset,
      league: leagueParam,
    });
    hasNext = res.length > PAGE_SIZE;
    matches = res.slice(0, PAGE_SIZE);
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }
  const acc = await fetchAccuracy(leagueParam);
  const hasLive = matches.some((m) => m.status === "live");

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-10">
      {hasLive && <LivePoller />}
      <WorldCupCountdown lang={lang} />
      <header className="space-y-4">
        <h1 className="headline-hero">{t("dash.headline")}</h1>
        <p className="max-w-2xl text-secondary text-base md:text-lg">{t("dash.subhead")}</p>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          {acc && acc.scored > 0 && (
            <span className="inline-flex items-center gap-1 font-mono">
              <span className="stat text-base text-neon">{Math.round(acc.accuracy * 100)}%</span>
              <span className="text-muted">
                {lang === "vi" ? `chính xác · ${acc.scored} trận` : `accuracy · ${acc.scored} matches`}
              </span>
            </span>
          )}
          <span className="text-muted">·</span>
          <Link href="/docs/model" className="text-secondary hover:text-neon transition-colors font-mono text-xs uppercase tracking-wide">
            {lang === "vi" ? "Mô hình hoạt động thế nào →" : "How the model works →"}
          </Link>
          <span className="text-muted">·</span>
          <Link href="/proof" className="text-neon hover:opacity-80 transition-opacity font-mono text-xs uppercase tracking-wide">
            {lang === "vi" ? "Chứng minh →" : "Proof →"}
          </Link>
          <span className="text-muted">·</span>
          <Link href="/blog" className="text-secondary hover:text-neon transition-colors font-mono text-xs uppercase tracking-wide">
            blog →
          </Link>
          <span className="text-muted">·</span>
          <Link href="/faq" className="text-secondary hover:text-neon transition-colors font-mono text-xs uppercase tracking-wide">
            faq →
          </Link>
          <span className="text-muted">·</span>
          <PushButton />
        </div>
      </header>

      {error && (
        <div className="card text-error font-mono text-sm">
          <span className="label block mb-1">{t("dash.apiError")}</span>
          {error}
        </div>
      )}

      {!error && matches.length === 0 && (
        <div className="card text-secondary">{t("dash.empty")}</div>
      )}

      <ProofStrip league={leagueParam} lang={lang} />

      <StarPlayersStrip league={leagueParam} lang={lang} />

      <RecentResults league={leagueParam} lang={lang} />

      {matches.length > 0 && <FavoritesSection matches={matches} />}
      {matches.length > 0 && <QuickPicks matches={matches} lang={lang} />}
      <TelegramCTA lang={lang} />

      {acc && acc.scored > 0 && (
        <section className="card grid grid-cols-2 md:grid-cols-4 gap-6">
          <div>
            <p className="label">{t("dash.stat.accuracy")}</p>
            <p className="stat text-neon">{Math.round(acc.accuracy * 100)}%</p>
          </div>
          <div>
            <p className="label">{t("dash.stat.baseline")}</p>
            <p className="stat">{Math.round(acc.baseline_home_accuracy * 100)}%</p>
          </div>
          <div>
            <p className="label">{t("dash.stat.logloss")}</p>
            <p className="stat">{acc.mean_log_loss.toFixed(3)}</p>
          </div>
          <div>
            <p className="label">{t("dash.stat.matches")}</p>
            <p className="stat">{acc.scored}</p>
          </div>
        </section>
      )}

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {matches.map((m) => (
          <MatchCard key={m.id} match={m} lang={lang} />
        ))}
      </section>

      {(page > 1 || hasNext) && (
        <nav
          aria-label="Match pagination"
          className="flex items-center justify-between gap-3 font-mono text-xs"
        >
          <div>
            {page > 1 ? (
              <Link
                href={page === 2 ? "/" : `/?p=${page - 1}`}
                className="inline-flex items-center gap-2 rounded-full border border-border px-4 py-2 uppercase tracking-wide text-secondary hover:border-neon hover:text-neon transition-colors"
              >
                ← {lang === "vi" ? "Trang trước" : "Previous"}
              </Link>
            ) : (
              <span />
            )}
          </div>
          <span className="text-muted tabular-nums">
            {lang === "vi" ? "Trang" : "Page"} {page}
            {" · "}
            {matches.length} {lang === "vi" ? "trận" : "matches"}
          </span>
          <div>
            {hasNext && (
              <Link
                href={`/?p=${page + 1}`}
                className="inline-flex items-center gap-2 rounded-full bg-neon px-4 py-2 uppercase tracking-wide text-on-neon font-semibold hover:opacity-90 transition-opacity"
              >
                {lang === "vi" ? "Trang sau" : "Next"} →
              </Link>
            )}
          </div>
        </nav>
      )}
    </main>
  );
}
