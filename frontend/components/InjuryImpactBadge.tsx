import type { InjuryImpact } from "@/lib/api";
import type { Lang } from "@/lib/i18n";

// Inline under the prediction card: shows how injuries shrank λ + who's out.
// Hidden when both teams have zero impact.
export default function InjuryImpactBadge({
  impact,
  lang,
  homeShort,
  awayShort,
}: {
  impact: InjuryImpact;
  lang: Lang;
  homeShort: string;
  awayShort: string;
}) {
  const hasHome = impact.home.injured_xg_share > 0.01;
  const hasAway = impact.away.injured_xg_share > 0.01;
  if (!hasHome && !hasAway) return null;

  const label =
    lang === "vi"
      ? "Model đã giảm λ do chấn thương"
      : "Model shrunk λ due to injuries";

  function row(
    team: "home" | "away",
    short: string,
    data: InjuryImpact["home"],
  ) {
    if (data.injured_xg_share < 0.01) return null;
    const dropPct = Math.round((1 - data.lambda_multiplier) * 100);
    const names = data.top_absent.slice(0, 3).join(", ") || "—";
    return (
      <div key={team} className="flex flex-wrap items-baseline gap-2 font-mono text-xs">
        <span className="text-secondary w-12 shrink-0">{short}</span>
        <span className="text-error">-{dropPct}% λ</span>
        <span className="text-muted truncate">
          {lang === "vi" ? "vắng:" : "out:"} {names}
        </span>
      </div>
    );
  }

  return (
    <section className="card space-y-2 border-error/30">
      <h2 className="label text-error/80">🚑 {label}</h2>
      <div className="space-y-1">
        {row("home", homeShort, impact.home)}
        {row("away", awayShort, impact.away)}
      </div>
    </section>
  );
}
