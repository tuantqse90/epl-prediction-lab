import type { ScorerOdds } from "@/lib/api";
import type { Lang } from "@/lib/i18n";
import TeamLogo from "./TeamLogo";

function pct(x: number) {
  return `${Math.round(x * 100)}%`;
}

export default function ScorerOddsPanel({
  rows,
  lang,
}: {
  rows: ScorerOdds[];
  lang: Lang;
}) {
  if (rows.length === 0) return null;

  const title = lang === "vi" ? "Ai có khả năng ghi bàn?" : "Anytime goalscorer odds";
  const subhead =
    lang === "vi"
      ? "P(ghi ≥ 1 bàn) từ xG mùa của cầu thủ × λ trận × (trận này / trận mùa)."
      : "P(≥ 1 goal) from player season xG × match λ × availability share.";
  const maxP = Math.max(...rows.map((r) => r.p_anytime), 0.01);

  return (
    <section className="card space-y-3">
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <h2 className="label">{title}</h2>
        <p className="text-[11px] text-muted max-w-md">{subhead}</p>
      </div>

      <ul className="space-y-1.5">
        {rows.map((r) => {
          const widthPct = (r.p_anytime / maxP) * 100;
          return (
            <li
              key={`${r.team_slug}-${r.player_name}`}
              className="flex items-center gap-3 text-sm"
            >
              <TeamLogo slug={r.team_slug} name={r.team_short} size={16} />
              <span className="min-w-0 truncate flex-1">
                {r.player_name}
                {r.position && (
                  <span className="ml-1.5 font-mono text-[10px] text-muted uppercase">
                    {r.position}
                  </span>
                )}
              </span>
              <div className="flex-1 max-w-[140px] h-2 rounded bg-high overflow-hidden">
                <div
                  className="h-full bg-neon transition-all"
                  style={{ width: `${widthPct}%` }}
                />
              </div>
              <span className="w-14 shrink-0 text-right tabular-nums font-mono text-xs text-neon">
                {pct(r.p_anytime)}
              </span>
              <span className="w-12 shrink-0 text-right tabular-nums font-mono text-[10px] text-muted">
                xG {r.expected_goals.toFixed(2)}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
