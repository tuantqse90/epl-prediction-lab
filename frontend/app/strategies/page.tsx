import type { Metadata } from "next";
import Link from "next/link";

import StrategyChart from "@/components/StrategyChart";
import { getLang, getLeagueSlug, leagueForApi, tFor } from "@/lib/i18n-server";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Strategy simulator — sharp vs silly bankroll sims · predictor.nullshift.sh",
  description:
    "Retrospective bankroll simulator across named betting strategies. " +
    "Value ladder, Kelly, Martingale, contrarian — same bets, same season, " +
    "different sizing rules. Watch what would have happened.",
  alternates: { canonical: "/strategies" },
};

const STRATEGIES = [
  {
    slug: "value-ladder",
    label_en: "Value ladder",
    label_vi: "Bậc thang giá trị",
    explainer_en: "Stake = 1u × (edge_pp / 5), capped at 5u. Bigger edge → bigger stake; no compounding.",
    explainer_vi: "Stake = 1u × (edge_pp / 5), cap 5u. Edge càng lớn → stake càng lớn; không compound.",
  },
  {
    slug: "high-confidence",
    label_en: "High-confidence filter",
    label_vi: "Lọc tự tin cao",
    explainer_en: "Flat 1u, but only when model_prob ≥ 60% AND edge ≥ threshold. Cuts low-conviction spray bets.",
    explainer_vi: "Stake cố định 1u, chỉ đặt khi model_prob ≥ 60% VÀ edge ≥ ngưỡng. Lọc kèo ít tự tin.",
  },
  {
    slug: "martingale",
    label_en: "Martingale (do not try)",
    label_vi: "Martingale (đừng thử)",
    explainer_en: "Double stake after every loss, reset on win. Pedagogical — runs to ruin on real data.",
    explainer_vi: "Double stake sau mỗi lần thua, reset khi thắng. Minh họa — sẽ cháy tài khoản trên data thật.",
    warning_en: "Never attempt live. Bankroll runs out before the eventual win lands — the textbook Martingale failure mode.",
    warning_vi: "KHÔNG làm thật. Bankroll cháy trước khi trận thắng tiếp theo về — thất bại điển hình của Martingale.",
  },
  // 15.4 slots in here as it ships
] as const;

const THRESHOLDS = [0.03, 0.05, 0.07, 0.10] as const;

export default async function StrategiesPage({
  searchParams,
}: {
  searchParams: Promise<{ name?: string; threshold?: string; season?: string }>;
}) {
  const sp = await searchParams;
  const name = STRATEGIES.find((s) => s.slug === sp.name)?.slug ?? "value-ladder";
  const season = sp.season ?? "2025-26";
  const rawThreshold = Number(sp.threshold ?? "0.05");
  const threshold = (THRESHOLDS as readonly number[]).includes(rawThreshold) ? rawThreshold : 0.05;

  const lang = await getLang();
  const t = tFor(lang);
  const league = await getLeagueSlug();
  const current = STRATEGIES.find((s) => s.slug === name)!;

  const title = lang === "vi" ? current.label_vi : current.label_en;
  const explainer = lang === "vi" ? current.explainer_vi : current.explainer_en;
  const warning = (current as { warning_en?: string; warning_vi?: string }).warning_en
    ? (lang === "vi" ? (current as { warning_vi: string }).warning_vi : (current as { warning_en: string }).warning_en)
    : undefined;

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-8">
      <Link href="/roi" className="btn-ghost text-sm">{t("common.back")}</Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">
          {lang === "vi" ? "Mô phỏng chiến thuật · dữ liệu lịch sử" : "Strategy simulator · historical data"}
        </p>
        <h1 className="headline-section">
          {lang === "vi" ? "Chọn chiến thuật, xem bankroll trên thực tế" : "Pick a strategy, watch the bankroll on real data"}
        </h1>
        <p className="max-w-2xl text-secondary">
          {lang === "vi"
            ? "Cùng 1 tập kèo lịch sử, mỗi chiến thuật stake-sizing cho ra một đường bankroll khác nhau. Không stake thật — chỉ mô phỏng trên 2025-26 để hiểu chiến thuật nào work, chiến thuật nào là bẫy."
            : "Same bet universe, different sizing rules. No real stakes — a retrospective sim on 2025-26 finals that shows which strategy grows, which bleeds, and why."}
        </p>
      </header>

      <nav className="flex flex-wrap gap-2">
        <span className="font-mono text-[10px] uppercase tracking-wide text-muted self-center mr-1">
          {lang === "vi" ? "Chiến thuật" : "Strategy"}
        </span>
        {STRATEGIES.map((s) => (
          <Link
            key={s.slug}
            href={`/strategies?name=${s.slug}&threshold=${threshold}`}
            className={
              "rounded-full px-3 py-1 font-mono text-xs uppercase tracking-wide border " +
              (s.slug === name
                ? "border-neon bg-neon text-on-neon"
                : "border-border text-secondary hover:border-neon hover:text-neon")
            }
          >
            {lang === "vi" ? s.label_vi : s.label_en}
          </Link>
        ))}
        <span className="text-muted mx-2 self-center">·</span>
        <Link
          href="/roi"
          className="rounded-full px-3 py-1 font-mono text-xs uppercase tracking-wide border border-border text-secondary hover:border-neon hover:text-neon"
        >
          {lang === "vi" ? "Flat / Kelly →" : "Flat / Kelly →"}
        </Link>
      </nav>

      <nav className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[10px] uppercase tracking-wide text-muted mr-1">edge</span>
        {THRESHOLDS.map((thr) => (
          <Link
            key={thr}
            href={`/strategies?name=${name}&threshold=${thr}`}
            className={
              "rounded-full px-3 py-1 font-mono text-xs uppercase tracking-wide border " +
              (Math.abs(thr - threshold) < 0.0001
                ? "border-neon bg-neon text-on-neon"
                : "border-border text-secondary hover:border-neon hover:text-neon")
            }
          >
            ≥ {Math.round(thr * 100)}%
          </Link>
        ))}
      </nav>

      <StrategyChart
        name={name}
        title={title}
        explainer={explainer}
        warning={warning}
        season={season}
        threshold={threshold}
        starting={100}
        league={leagueForApi(league)}
        lang={lang}
      />

      <p className="font-mono text-[10px] uppercase tracking-wide text-muted">
        {lang === "vi"
          ? "Mô phỏng trên kèo lịch sử ở ngưỡng edge đã chọn. Không phải stake thật; không custody."
          : "Simulated on historical value bets at the selected edge threshold. No real stakes; no custody."}
      </p>
    </main>
  );
}
