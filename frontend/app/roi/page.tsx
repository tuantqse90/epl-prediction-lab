import Link from "next/link";

import KellyChart from "@/components/KellyChart";
import RoiChart from "@/components/RoiChart";
import TaxToggle from "@/components/TaxToggle";
import { getLang, getLeagueSlug, leagueForApi, tFor } from "@/lib/i18n-server";
import { getLeague } from "@/lib/leagues";

export const dynamic = "force-dynamic";

const THRESHOLDS = [0.03, 0.05, 0.07, 0.1] as const;
const STAKING_MODES = ["flat", "kelly"] as const;
type StakingMode = (typeof STAKING_MODES)[number];

export default async function RoiPage({
  searchParams,
}: {
  searchParams: Promise<{ threshold?: string; season?: string; staking?: string }>;
}) {
  const sp = await searchParams;
  const season = sp.season ?? "2025-26";
  const threshold = Number(sp.threshold ?? "0.05");
  const active = THRESHOLDS.includes(threshold as (typeof THRESHOLDS)[number])
    ? threshold
    : 0.05;
  const staking: StakingMode = (STAKING_MODES as readonly string[]).includes(sp.staking ?? "")
    ? (sp.staking as StakingMode)
    : "flat";
  const lang = await getLang();
  const league = await getLeagueSlug();
  const leagueInfo = getLeague(league);
  const t = tFor(lang);
  const leagueLabel = lang === "vi" ? leagueInfo.name_vi : leagueInfo.name_en;

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">
          {leagueInfo.emoji} {leagueLabel} · {season}
        </p>
        <h1 className="headline-section">{t("roi.title")}</h1>
        <p className="text-secondary max-w-2xl">
          {t("roi.subhead", { threshold: `${Math.round(active * 100)}` })}
        </p>
      </header>

      <nav className="flex flex-wrap items-center gap-2">
        {THRESHOLDS.map((thr) => (
          <Link
            key={thr}
            href={`/roi?threshold=${thr}&staking=${staking}`}
            className={
              "rounded-full px-3 py-1 font-mono text-xs uppercase tracking-wide border " +
              (Math.abs(thr - active) < 0.0001
                ? "border-neon bg-neon text-on-neon"
                : "border-border text-secondary hover:border-neon hover:text-neon")
            }
          >
            edge ≥ {Math.round(thr * 100)}%
          </Link>
        ))}
        <span className="text-muted mx-2">·</span>
        <Link
          href="/roi/by-league"
          className="rounded-full px-3 py-1 font-mono text-xs uppercase tracking-wide border border-border text-secondary hover:border-neon hover:text-neon"
        >
          {lang === "vi" ? "Tách theo giải →" : "By league →"}
        </Link>
      </nav>

      <nav className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[10px] uppercase tracking-wide text-muted mr-1">
          {lang === "vi" ? "Staking" : "Staking"}
        </span>
        {STAKING_MODES.map((m) => (
          <Link
            key={m}
            href={`/roi?threshold=${active}&staking=${m}`}
            className={
              "rounded-full px-3 py-1 font-mono text-xs uppercase tracking-wide border " +
              (staking === m
                ? "border-neon bg-neon text-on-neon"
                : "border-border text-secondary hover:border-neon hover:text-neon")
            }
          >
            {m === "flat" ? (lang === "vi" ? "1u cố định" : "Flat 1u") : "Kelly"}
          </Link>
        ))}
      </nav>

      {staking === "kelly" ? (
        <KellyChart
          season={season}
          threshold={active}
          cap={0.25}
          starting={100}
          league={leagueForApi(league)}
          lang={lang}
        />
      ) : (
        <RoiChart season={season} threshold={active} league={leagueForApi(league)} lang={lang} />
      )}

      <TaxToggle threshold={active} season={season} />
    </main>
  );
}
