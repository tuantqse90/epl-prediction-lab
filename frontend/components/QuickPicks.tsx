import Link from "next/link";

import { t as tRaw } from "@/lib/i18n";
import type { Lang } from "@/lib/i18n";
import { tLang } from "@/lib/i18n-fallback";
import type { MatchOut } from "@/lib/types";
import TeamLogo from "./TeamLogo";

const THRESHOLD = 0.05;
const MAX = 3;

function outcomeLabel(lang: Lang, o: "H" | "D" | "A") {
  if (o === "H") return tRaw(lang, "detail.home");
  if (o === "D") return tRaw(lang, "detail.draw");
  return tRaw(lang, "detail.away");
}

function pp(x: number) {
  return `${x > 0 ? "+" : ""}${(x * 100).toFixed(1)}pp`;
}

export default function QuickPicks({
  matches,
  lang,
  positiveRoiLeagues,
}: {
  matches: MatchOut[];
  lang: Lang;
  // When provided, only matches whose league_code is in this set are
  // eligible — hides picks from leagues where 30d rolling ROI is negative.
  // Omit or pass null to keep all picks.
  positiveRoiLeagues?: Set<string> | null;
}) {
  const t = (k: string) => tRaw(lang, k);

  const picks = matches
    .filter((m) => m.odds && m.odds.best_edge != null && m.odds.best_edge >= THRESHOLD && m.odds.best_outcome)
    .filter((m) => !positiveRoiLeagues || positiveRoiLeagues.has(m.league_code))
    .sort((a, b) => (b.odds!.best_edge ?? 0) - (a.odds!.best_edge ?? 0))
    .slice(0, MAX);

  const filterApplied = !!positiveRoiLeagues;

  return (
    <section className="card space-y-4">
      <div className="flex items-baseline justify-between">
        <h2 className="font-display font-semibold uppercase tracking-tight">{t("quick.title")}</h2>
        <span className="font-mono text-[10px] text-muted uppercase tracking-wide">
          edge ≥ {Math.round(THRESHOLD * 100)}pp
        </span>
      </div>

      {filterApplied && picks.length > 0 && (
        <p className="font-mono text-[10px] uppercase tracking-wide text-muted">
          {tLang(lang, {
            en: "Showing only leagues with positive 30d ROI",
            vi: "Chỉ hiện picks từ giải có ROI 30d dương",
            th: "แสดงเฉพาะลีกที่มี ROI 30 วันเป็นบวก",
            zh: "仅显示近 30 天 ROI 为正的联赛",
            ko: "최근 30일 ROI가 양수인 리그만 표시",
          })}
        </p>
      )}

      {picks.length === 0 ? (
        <p className="text-muted text-sm">{t("quick.empty")}</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {picks.map((m) => {
            const o = m.odds!;
            const out = o.best_outcome!;
            return (
              <Link
                key={m.id}
                href={`/match/${m.id}`}
                className="rounded-xl border border-border p-4 hover:border-neon transition-colors flex flex-col gap-2"
              >
                <div className="flex items-center gap-2 text-sm">
                  <TeamLogo slug={m.home.slug} name={m.home.name} size={20} />
                  <span className="font-display font-semibold uppercase tracking-tighter">
                    {m.home.short_name}
                  </span>
                  <span className="text-muted font-body normal-case">vs</span>
                  <span className="font-display font-semibold uppercase tracking-tighter">
                    {m.away.short_name}
                  </span>
                  <TeamLogo slug={m.away.slug} name={m.away.name} size={20} />
                </div>
                <div className="flex items-end justify-between">
                  <div>
                    <p className="text-[10px] text-muted uppercase tracking-wide">
                      {t("match.value")} → {outcomeLabel(lang, out)}
                    </p>
                    <p className="font-mono text-2xl tabular-nums text-neon">
                      {pp(o.best_edge!)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] text-muted uppercase tracking-wide">{t("odds.odds")}</p>
                    <p className="font-mono text-sm tabular-nums text-secondary">
                      {out === "H" ? o.odds_home.toFixed(2) : out === "D" ? o.odds_draw.toFixed(2) : o.odds_away.toFixed(2)}
                    </p>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </section>
  );
}
