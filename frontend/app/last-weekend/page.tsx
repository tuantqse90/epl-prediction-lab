import Link from "next/link";

import TeamLogo from "@/components/TeamLogo";
import { formatDateOnly } from "@/lib/date";
import { getLang, getLeagueSlug, tFor } from "@/lib/i18n-server";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type RecentMatch = {
  match_id: number;
  kickoff_time: string;
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

function outcomeLetter(lang: "en" | "vi", o: "H" | "D" | "A") {
  if (lang === "en") return o === "H" ? "Home" : o === "D" ? "Draw" : "Away";
  return o === "H" ? "Chủ" : o === "D" ? "Hòa" : "Khách";
}

function pct(x: number) {
  return `${Math.round(x * 100)}%`;
}

export default async function LastWeekendPage() {
  const days = 7;
  const lang = await getLang();
  const league = await getLeagueSlug();
  const t = tFor(lang);
  const w = await fetchRecent(days, league);

  if (!w) {
    return (
      <main className="mx-auto max-w-5xl px-6 py-12">
        <div className="card text-error">{t("dash.apiError")}</div>
      </main>
    );
  }

  const matches = w.matches;

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-10">
      <Link href="/" className="btn-ghost text-sm">
        {t("common.back")}
      </Link>

      <header className="space-y-3">
        <h1 className="headline-section">{t("recent.title")}</h1>
        <p className="max-w-2xl text-secondary">
          {t("recent.subhead", { days })}
        </p>
      </header>

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
            const actual = outcomeLetter(lang, m.actual_outcome);
            return (
              <Link
                key={m.match_id}
                href={`/match/${m.match_id}`}
                className="card flex flex-col gap-3 hover:border-neon transition-colors"
              >
                <div className="flex items-baseline justify-between">
                  <span className="font-mono text-xs text-muted">{dateStr}</span>
                  <span
                    className={
                      "rounded-full px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide " +
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
              </Link>
            );
          })}
        </section>
      )}
    </main>
  );
}
