import type { Metadata } from "next";
import Link from "next/link";

import { getLang, tFor } from "@/lib/i18n-server";
import { REAL_LEAGUES } from "@/lib/leagues";

export const metadata: Metadata = {
  title: "Leagues · predictor.nullshift.sh",
  description: "Per-league prediction dashboards for EPL, La Liga, Serie A, Bundesliga, and Ligue 1.",
};

export default async function LeaguesIndex() {
  const lang = await getLang();
  const t = tFor(lang);

  return (
    <main className="mx-auto max-w-4xl px-6 py-12 space-y-10">
      <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>
      <header className="space-y-3">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-neon">leagues</p>
        <h1 className="headline-hero">Top 5 Europe</h1>
        <p className="text-secondary text-base md:text-lg max-w-xl">
          {lang === "vi"
            ? "Mỗi giải có dashboard riêng với độ chính xác, so sánh với nhà cái, và trận sắp tới."
            : "Each league gets its own dashboard with accuracy, vs-bookies delta, and upcoming fixtures."}
        </p>
      </header>

      <section className="grid gap-4 md:grid-cols-2">
        {REAL_LEAGUES.map((lg) => (
          <Link
            key={lg.slug}
            href={`/leagues/${lg.slug}`}
            className="card block hover:border-neon transition-colors"
          >
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-2xl">{lg.emoji}</span>
              <span className="font-mono text-[10px] uppercase tracking-wide text-muted">
                {lg.code}
              </span>
            </div>
            <h2 className="font-display text-xl md:text-2xl font-semibold uppercase tracking-tight mt-3">
              {lang === "vi" ? lg.name_vi : lg.name_en}
            </h2>
            <p className="font-mono text-[11px] text-muted mt-2">
              {lang === "vi" ? "Xem predictions + hit rate →" : "See predictions + hit rate →"}
            </p>
          </Link>
        ))}
      </section>
    </main>
  );
}
