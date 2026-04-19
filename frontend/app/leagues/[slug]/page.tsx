import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import MatchCard from "@/components/MatchCard";
import TeamLogo from "@/components/TeamLogo";
import { listMatches } from "@/lib/api";
import { formatDateOnly } from "@/lib/date";
import { getLang, tFor } from "@/lib/i18n-server";
import { REAL_LEAGUES, getLeague } from "@/lib/leagues";
import type { Lang } from "@/lib/i18n";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type HistorySeason = {
  season: string;
  scored: number;
  correct: number;
  accuracy: number;
  mean_log_loss: number;
  baseline_home_accuracy: number;
};

type Comparison = {
  days: number;
  scored: number;
  model_accuracy: number;
  bookmaker_accuracy: number;
  home_baseline_accuracy: number;
  model_log_loss: number;
};

type RecentMatch = {
  match_id: number;
  kickoff_time: string;
  home_short: string;
  home_slug: string;
  away_short: string;
  away_slug: string;
  home_goals: number;
  away_goals: number;
  predicted_outcome: string;
  actual_outcome: string;
  hit: boolean;
  confidence: number;
};

type RecentOut = {
  days: number;
  scored: number;
  correct: number;
  accuracy: number;
  matches: RecentMatch[];
};

async function fetchHistory(league: string): Promise<HistorySeason[]> {
  try {
    const res = await fetch(`${BASE}/api/stats/history?league=${encodeURIComponent(league)}`, { cache: "no-store" });
    return res.ok ? res.json() : [];
  } catch { return []; }
}

async function fetchComparison(league: string): Promise<Comparison | null> {
  try {
    const res = await fetch(`${BASE}/api/stats/comparison?days=30&league=${encodeURIComponent(league)}`, { cache: "no-store" });
    return res.ok ? res.json() : null;
  } catch { return null; }
}

async function fetchRecent(league: string): Promise<RecentOut | null> {
  try {
    const res = await fetch(`${BASE}/api/stats/recent?days=14&league=${encodeURIComponent(league)}`, { cache: "no-store" });
    return res.ok ? res.json() : null;
  } catch { return null; }
}

export async function generateStaticParams() {
  return REAL_LEAGUES.map((l) => ({ slug: l.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const lg = getLeague(slug);
  if (!lg || lg.slug === "all") return { title: "League not found" };
  const title = `${lg.name_en} predictions · hash-committed model · predictor.nullshift.sh`;
  const description =
    `Every ${lg.name_en} fixture predicted by a 3-leg xG+Elo+XGBoost ensemble. ` +
    `Probabilities commit-hashed before kickoff. Accuracy + log-loss tracked live.`;
  return {
    title,
    description,
    openGraph: { title, description, url: `/leagues/${slug}` },
    twitter: { card: "summary_large_image", title, description },
    alternates: { canonical: `/leagues/${slug}` },
  };
}

function pct(x: number) {
  return `${Math.round(x * 100)}%`;
}

export default async function LeaguePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const lg = getLeague(slug);
  if (!lg || lg.slug === "all") notFound();

  const lang = await getLang();
  const t = tFor(lang);

  const [history, comparison, recent, upcoming] = await Promise.all([
    fetchHistory(slug),
    fetchComparison(slug),
    fetchRecent(slug),
    listMatches({ upcomingOnly: true, limit: 12, league: slug }).catch(() => []),
  ]);

  const label = lang === "vi" ? lg.name_vi : lg.name_en;
  const totalScored = history.reduce((s, r) => s + r.scored, 0);
  const weightedAcc = totalScored > 0
    ? history.reduce((s, r) => s + r.correct, 0) / totalScored : 0;
  const weightedLL = totalScored > 0
    ? history.reduce((s, r) => s + r.mean_log_loss * r.scored, 0) / totalScored : 0;
  const weightedBaseline = totalScored > 0
    ? history.reduce((s, r) => s + r.baseline_home_accuracy * r.scored, 0) / totalScored : 0;
  const bestSeason = history.length > 0
    ? [...history].sort((a, b) => b.accuracy - a.accuracy)[0] : null;

  const hits = recent?.matches.filter((m) => m.hit) ?? [];
  const misses = recent?.matches.filter((m) => !m.hit) ?? [];

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-10">
      <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>

      {/* Hero */}
      <header className="space-y-4">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-neon">
          {lg.emoji} {label}
        </p>
        <h1 className="headline-hero">{label}</h1>
        <p className="text-secondary text-base md:text-lg max-w-2xl">
          {lang === "vi"
            ? `Mọi trận ${label} được dự đoán bằng ensemble 3-leg xG + Elo + XGBoost. Xác suất mã hóa SHA-256 trước kickoff. Log-loss được đo liên tục.`
            : `Every ${label} fixture predicted by a 3-leg xG + Elo + XGBoost ensemble. Probabilities SHA-256 hashed before kickoff. Log-loss tracked live.`}
        </p>
      </header>

      {/* Trust numbers */}
      {totalScored > 0 && (
        <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="card">
            <p className="label">{lang === "vi" ? "Chính xác" : "Accuracy"}</p>
            <p className="stat text-neon text-3xl md:text-4xl">{pct(weightedAcc)}</p>
            <p className="font-mono text-[11px] text-muted mt-1">
              vs {pct(weightedBaseline)} baseline
            </p>
          </div>
          <div className="card">
            <p className="label">Log-loss</p>
            <p className="stat text-neon text-3xl md:text-4xl">{weightedLL.toFixed(3)}</p>
            <p className="font-mono text-[11px] text-muted mt-1">
              {lang === "vi" ? "thấp hơn" : "lower by"} {(1.0986 - weightedLL).toFixed(3)} {lang === "vi" ? "so với random" : "vs random"}
            </p>
          </div>
          <div className="card">
            <p className="label">{lang === "vi" ? "Trận đã chấm" : "Scored"}</p>
            <p className="stat text-3xl md:text-4xl">{totalScored.toLocaleString()}</p>
            <p className="font-mono text-[11px] text-muted mt-1">{history.length} {lang === "vi" ? "mùa" : history.length === 1 ? "season" : "seasons"}</p>
          </div>
          <div className="card">
            <p className="label">{lang === "vi" ? "Mùa đỉnh" : "Peak season"}</p>
            <p className="stat text-3xl md:text-4xl">
              {bestSeason ? pct(bestSeason.accuracy) : "—"}
            </p>
            <p className="font-mono text-[11px] text-muted mt-1">
              {bestSeason ? bestSeason.season : ""}
            </p>
          </div>
        </section>
      )}

      {/* 30d model vs market */}
      {comparison && comparison.scored >= 10 && (
        <section className="card space-y-3">
          <div className="flex items-baseline justify-between gap-2 flex-wrap">
            <h2 className="headline-section text-xl md:text-2xl">
              {lang === "vi" ? "Model vs nhà cái · 30 ngày" : "Model vs bookies · 30 days"}
            </h2>
            <span className="font-mono text-[11px] text-muted">{comparison.scored} {lang === "vi" ? "trận" : "matches"}</span>
          </div>
          <div className="space-y-2 font-mono text-xs">
            {(() => {
              const rows = [
                { label: "Model", value: comparison.model_accuracy, accent: true },
                { label: lang === "vi" ? "Nhà cái" : "Bookies", value: comparison.bookmaker_accuracy },
                { label: lang === "vi" ? "Luôn chủ nhà" : "Always home", value: comparison.home_baseline_accuracy },
              ];
              const max = Math.max(0.6, ...rows.map((r) => r.value));
              return rows.map((r) => {
                const w = Math.min(100, (r.value / max) * 100);
                return (
                  <div key={r.label} className="flex items-center gap-3">
                    <span className={`w-24 shrink-0 uppercase tracking-wide ${r.accent ? "text-neon" : "text-secondary"}`}>{r.label}</span>
                    <div className="flex-1 h-6 rounded bg-high overflow-hidden">
                      <div className={`h-full ${r.accent ? "bg-neon" : "bg-secondary/40"} transition-all`} style={{ width: `${w}%` }} />
                    </div>
                    <span className={`w-14 text-right tabular-nums ${r.accent ? "text-neon font-semibold" : "text-primary"}`}>{pct(r.value)}</span>
                  </div>
                );
              });
            })()}
          </div>
        </section>
      )}

      {/* Upcoming matches */}
      {upcoming.length > 0 && (
        <section className="space-y-4">
          <h2 className="headline-section text-xl md:text-2xl">
            {lang === "vi" ? "Trận sắp tới" : "Upcoming fixtures"}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {upcoming.slice(0, 6).map((m) => (
              <MatchCard key={m.id} match={m} lang={lang as Lang} />
            ))}
          </div>
        </section>
      )}

      {/* Recent hits / misses */}
      {recent && recent.matches.length > 0 && (
        <section className="space-y-4">
          <div className="flex items-baseline justify-between flex-wrap gap-2">
            <h2 className="headline-section text-xl md:text-2xl">
              {lang === "vi" ? "Hit / miss gần nhất" : "Recent hits / misses"}
            </h2>
            <span className="font-mono text-[11px] text-muted">
              {recent.correct}/{recent.scored} ({pct(recent.accuracy)}) · last 14d
            </span>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div className="card space-y-2">
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-neon">
                ✓ {lang === "vi" ? "Đoán đúng" : "Hits"} ({hits.length})
              </p>
              <ul className="space-y-1 font-mono text-xs">
                {hits.slice(0, 6).map((m) => (
                  <li key={m.match_id}>
                    <Link href={`/match/${m.match_id}`} className="flex items-center justify-between gap-2 hover:text-neon transition-colors">
                      <span className="flex items-center gap-2">
                        <TeamLogo slug={m.home_slug} name={m.home_short} size={16} />
                        <span className="text-primary">{m.home_short}</span>
                        <span className="text-neon">{m.home_goals}-{m.away_goals}</span>
                        <span className="text-primary">{m.away_short}</span>
                        <TeamLogo slug={m.away_slug} name={m.away_short} size={16} />
                      </span>
                      <span className="text-muted text-[10px]">{formatDateOnly(m.kickoff_time, lang)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
            <div className="card space-y-2">
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-error">
                ✗ {lang === "vi" ? "Đoán sai" : "Misses"} ({misses.length})
              </p>
              <ul className="space-y-1 font-mono text-xs">
                {misses.slice(0, 6).map((m) => (
                  <li key={m.match_id}>
                    <Link href={`/match/${m.match_id}`} className="flex items-center justify-between gap-2 hover:text-neon transition-colors">
                      <span className="flex items-center gap-2">
                        <TeamLogo slug={m.home_slug} name={m.home_short} size={16} />
                        <span className="text-primary">{m.home_short}</span>
                        <span className="text-error">{m.home_goals}-{m.away_goals}</span>
                        <span className="text-primary">{m.away_short}</span>
                        <TeamLogo slug={m.away_slug} name={m.away_short} size={16} />
                      </span>
                      <span className="text-muted text-[10px]">{formatDateOnly(m.kickoff_time, lang)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      )}

      {/* Per-season bars */}
      {history.length > 1 && (
        <section className="card space-y-3">
          <h2 className="headline-section text-xl md:text-2xl">
            {lang === "vi" ? "Chính xác theo mùa" : "Per-season accuracy"}
          </h2>
          <div className="space-y-2">
            {history.map((r) => {
              const maxA = Math.max(...history.map((x) => x.accuracy), 0.55);
              const w = (r.accuracy / maxA) * 100;
              const beats = r.accuracy > r.baseline_home_accuracy;
              return (
                <div key={r.season} className="flex items-center gap-3 font-mono text-xs">
                  <span className="w-20 shrink-0 text-muted">{r.season}</span>
                  <div className="flex-1 h-6 rounded bg-high overflow-hidden">
                    <div className={`h-full transition-all ${beats ? "bg-neon" : "bg-error"}`} style={{ width: `${w}%` }} />
                  </div>
                  <span className={`w-12 shrink-0 text-right tabular-nums ${beats ? "text-neon" : "text-error"}`}>{pct(r.accuracy)}</span>
                  <span className="w-16 shrink-0 text-right tabular-nums text-muted">{r.scored}m</span>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Cross-links */}
      <nav className="flex flex-wrap gap-2">
        {REAL_LEAGUES.filter((l) => l.slug !== lg.slug).map((l) => (
          <Link
            key={l.slug}
            href={`/leagues/${l.slug}`}
            className="inline-flex items-center gap-2 rounded-full border border-border px-4 py-1 font-mono text-xs uppercase tracking-wide text-secondary hover:border-neon hover:text-neon transition-colors"
          >
            <span>{l.emoji}</span>
            <span>{lang === "vi" ? l.name_vi : l.name_en}</span>
          </Link>
        ))}
      </nav>
    </main>
  );
}
