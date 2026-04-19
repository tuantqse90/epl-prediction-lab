import Link from "next/link";

import TeamLogo from "@/components/TeamLogo";
import { formatDateOnly } from "@/lib/date";
import { getLang, getLeagueSlug, leagueForApi, tFor } from "@/lib/i18n-server";
import type { Lang } from "@/lib/i18n";
import { getLeague, leagueByCode } from "@/lib/leagues";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type RecentMatch = {
  match_id: number;
  kickoff_time: string;
  league_code: string | null;
  home_slug: string;
  home_short: string;
  away_slug: string;
  away_short: string;
  home_goals: number;
  away_goals: number;
  home_xg: number | null;
  away_xg: number | null;
  p_home_win: number;
  p_draw: number;
  p_away_win: number;
  predicted_outcome: "H" | "D" | "A";
  actual_outcome: "H" | "D" | "A";
  hit: boolean;
  confidence: number;
  recap: string | null;
};

type RecentWindow = {
  days: number;
  scored: number;
  correct: number;
  accuracy: number;
  mean_log_loss: number;
  matches: RecentMatch[];
};

async function fetchRecent(days: number, league?: string): Promise<RecentWindow | null> {
  const qs = new URLSearchParams({ days: String(days) });
  if (league) qs.set("league", league);
  const res = await fetch(`${BASE}/api/stats/recent?${qs}`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

const OUTCOME_LABELS: Record<Lang, { H: string; D: string; A: string }> = {
  en: { H: "Home", D: "Draw", A: "Away" },
  vi: { H: "Chủ", D: "Hòa", A: "Khách" },
  th: { H: "เจ้าบ้าน", D: "เสมอ", A: "ทีมเยือน" },
  zh: { H: "主队", D: "平", A: "客队" },
  ko: { H: "홈", D: "무", A: "원정" },
};

function outcomeLetter(lang: Lang, o: "H" | "D" | "A") {
  return OUTCOME_LABELS[lang][o];
}

function pct(x: number) {
  return `${Math.round(x * 100)}%`;
}

const WINDOWS = [7, 14, 30] as const;

export default async function LastWeekendPage({
  searchParams,
}: {
  searchParams: Promise<{ days?: string }>;
}) {
  const sp = await searchParams;
  const rawDays = Number(sp.days ?? "7");
  const days = (WINDOWS as readonly number[]).includes(rawDays) ? rawDays : 7;

  const lang = await getLang();
  const league = await getLeagueSlug();
  const leagueInfo = getLeague(league);
  const leagueParam = leagueForApi(league);
  const t = tFor(lang);
  const w = await fetchRecent(days, leagueParam);

  if (!w) {
    return (
      <main className="mx-auto max-w-5xl px-6 py-12">
        <div className="card text-error">{t("dash.apiError")}</div>
      </main>
    );
  }

  const matches = w.matches;
  const leagueLabel = lang === "vi" ? leagueInfo.name_vi : leagueInfo.name_en;

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-10">
      <Link href="/" className="btn-ghost text-sm">
        {t("common.back")}
      </Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">
          {leagueInfo.emoji} {leagueLabel}
        </p>
        <h1 className="headline-section">{t("recent.title")}</h1>
        <p className="max-w-2xl text-secondary">
          {t("recent.subhead", { days })}
        </p>
      </header>

      {/* Day-window selector */}
      <nav className="flex gap-2">
        {WINDOWS.map((d) => (
          <Link
            key={d}
            href={d === 7 ? "/last-weekend" : `/last-weekend?days=${d}`}
            className={
              "rounded-full px-3 py-1 font-mono text-xs uppercase tracking-wide border " +
              (days === d
                ? "border-neon bg-neon text-on-neon"
                : "border-border text-secondary hover:border-neon hover:text-neon")
            }
          >
            last {d}d
          </Link>
        ))}
      </nav>

      <section className="card grid grid-cols-2 md:grid-cols-4 gap-6">
        <div>
          <p className="text-xs text-muted">{t("recent.summary.scored")}</p>
          <p className="stat">{w.scored}</p>
        </div>
        <div>
          <p className="text-xs text-muted">{t("recent.summary.correct")}</p>
          <p className="stat">{w.correct}</p>
        </div>
        <div>
          <p className="text-xs text-muted">{t("recent.summary.accuracy")}</p>
          <p className="stat text-neon">{w.scored ? pct(w.accuracy) : "—"}</p>
        </div>
        <div>
          <p className="text-xs text-muted">{t("recent.summary.logloss")}</p>
          <p className="stat">{w.scored ? w.mean_log_loss.toFixed(3) : "—"}</p>
        </div>
      </section>

      {matches.length === 0 ? (
        <div className="card text-muted">{t("recent.empty", { days })}</div>
      ) : (
        <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {matches.map((m) => {
            const dateStr = formatDateOnly(m.kickoff_time, lang);
            const predicted = outcomeLetter(lang, m.predicted_outcome);
            const matchLeague = leagueByCode(m.league_code);
            return (
              <Link
                key={m.match_id}
                href={`/match/${m.match_id}`}
                className="card flex flex-col gap-3 hover:border-neon transition-colors"
              >
                <div className="flex items-baseline justify-between gap-2">
                  <div className="flex items-baseline gap-2 min-w-0">
                    {matchLeague && (
                      <span className="rounded-full bg-high px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-secondary shrink-0">
                        {matchLeague.emoji} {matchLeague.short}
                      </span>
                    )}
                    <span className="font-mono text-xs text-muted">{dateStr}</span>
                  </div>
                  <span
                    className={
                      "shrink-0 rounded-full px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide " +
                      (m.hit ? "bg-neon text-on-neon" : "bg-high text-error")
                    }
                  >
                    {m.hit ? t("recent.hit") : t("recent.miss")}
                  </span>
                </div>

                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2 min-w-0">
                    <TeamLogo slug={m.home_slug} name={m.home_short} size={24} />
                    <span className="font-display text-xl font-semibold uppercase tracking-tighter truncate">
                      {m.home_short}
                    </span>
                  </div>
                  <div className="flex flex-col items-center">
                    <span className="font-mono text-[9px] uppercase tracking-[0.12em] text-muted">
                      {t("match.finalScore")}
                    </span>
                    <span className="stat text-2xl text-neon">
                      {m.home_goals}–{m.away_goals}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 min-w-0 justify-end">
                    <span className="font-display text-xl font-semibold uppercase tracking-tighter truncate">
                      {m.away_short}
                    </span>
                    <TeamLogo slug={m.away_slug} name={m.away_short} size={24} />
                  </div>
                </div>

                <div className="flex items-center justify-between text-sm">
                  <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted">
                    {t("match.predictedLabel")} · {t("recent.predicted")}
                  </span>
                  <span className={m.hit ? "text-neon" : "text-secondary"}>
                    {predicted} · {pct(m.confidence)}
                  </span>
                </div>
                {m.recap && (
                  <p className="border-t border-border-muted pt-3 text-sm text-secondary leading-relaxed">
                    <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted mb-1 block">
                      {lang === "vi" ? "Mô hình nói" : "Model says"}
                    </span>
                    {m.recap}
                  </p>
                )}
              </Link>
            );
          })}
        </section>
      )}
    </main>
  );
}
