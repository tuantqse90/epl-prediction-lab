import type { Lang } from "@/lib/i18n";
import { t } from "@/lib/i18n";
import type { OddsOut, PredictionOut } from "@/lib/types";
import AddToBetslip from "./AddToBetslip";

// Fractional Kelly (capped at 25%). Returns share of bankroll.
function kelly(prob: number, odds: number, cap = 0.25): number {
  if (prob <= 0 || odds <= 1) return 0;
  const edge = prob * odds - 1;
  if (edge <= 0) return 0;
  return Math.min(cap, edge / (odds - 1));
}

export const VALUE_THRESHOLD = 0.05;

function pp(x: number) {
  const n = Math.round(x * 1000) / 10;
  return `${n > 0 ? "+" : ""}${n.toFixed(1)}pp`;
}

function outcomeLabel(lang: Lang, o: "H" | "D" | "A") {
  return o === "H"
    ? t(lang, "detail.home").toLowerCase()
    : o === "D"
    ? t(lang, "detail.draw").toLowerCase()
    : t(lang, "detail.away").toLowerCase();
}

export function ValueBetBadge({ odds, lang = "vi" }: { odds: OddsOut; lang?: Lang }) {
  if (odds.best_edge == null || odds.best_outcome == null) return null;
  if (odds.best_edge < VALUE_THRESHOLD) return null;
  return (
    <span className="inline-flex items-center gap-1 font-mono text-xs">
      <span className="rounded bg-neon px-1.5 py-0.5 text-on-neon font-semibold uppercase tracking-wide">
        {t(lang, "match.value")}
      </span>
      <span className="text-secondary">
        {outcomeLabel(lang, odds.best_outcome)} {pp(odds.best_edge)}
      </span>
    </span>
  );
}

export function OddsPanel({
  odds,
  lang = "vi",
  matchId,
  prediction,
}: {
  odds: OddsOut;
  lang?: Lang;
  matchId?: number;
  prediction?: PredictionOut | null;
}) {
  const rows: Array<{
    key: "H" | "D" | "A";
    label: string;
    odd: number;
    fair: number;
    edge: number | null | undefined;
  }> = [
    { key: "H", label: t(lang, "detail.home"), odd: odds.odds_home, fair: odds.fair_home, edge: odds.edge_home },
    { key: "D", label: t(lang, "detail.draw"), odd: odds.odds_draw, fair: odds.fair_draw, edge: odds.edge_draw },
    { key: "A", label: t(lang, "detail.away"), odd: odds.odds_away, fair: odds.fair_away, edge: odds.edge_away },
  ];
  return (
    <section className="card space-y-3">
      <div className="flex items-baseline justify-between">
        <h2 className="font-display font-semibold uppercase tracking-tight">
          {t(lang, "odds.title")}
        </h2>
        <span className="font-mono text-[10px] text-muted">{odds.source}</span>
      </div>
      <div className="overflow-x-auto -mx-2">
      <table className="w-full font-mono text-sm">
        <thead className="text-muted">
          <tr>
            <th className="label px-2 py-1 text-left">{t(lang, "odds.outcome")}</th>
            <th className="label px-2 py-1 text-right">{t(lang, "odds.odds")}</th>
            <th className="label px-2 py-1 text-right">{t(lang, "odds.fair")}</th>
            <th className="label px-2 py-1 text-right">{t(lang, "odds.edge")}</th>
            {prediction && <th className="label px-2 py-1 text-right">Kelly</th>}
            {matchId != null && <th className="label px-2 py-1 text-right"></th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const hasEdge = r.edge != null;
            const edgeClass = !hasEdge
              ? "text-muted"
              : r.edge! >= VALUE_THRESHOLD
              ? "text-neon"
              : r.edge! <= -VALUE_THRESHOLD
              ? "text-error"
              : "text-muted";
            return (
              <tr key={r.key} className="border-t border-border-muted">
                <td className="px-2 py-2 text-primary">{r.label}</td>
                <td className="px-2 py-2 tabular-nums text-right">{r.odd.toFixed(2)}</td>
                <td className="px-2 py-2 tabular-nums text-right text-secondary">
                  {Math.round(r.fair * 100)}%
                </td>
                <td className={`px-2 py-2 tabular-nums text-right ${edgeClass}`}>
                  {hasEdge ? pp(r.edge!) : "—"}
                </td>
                {prediction && (() => {
                  const modelProb =
                    r.key === "H" ? prediction.p_home_win
                    : r.key === "D" ? prediction.p_draw
                    : prediction.p_away_win;
                  const k = kelly(modelProb, r.odd);
                  return (
                    <td className={`px-2 py-2 tabular-nums text-right ${k > 0 ? "text-neon" : "text-muted"}`}>
                      {k > 0 ? `${(k * 100).toFixed(1)}%` : "—"}
                    </td>
                  );
                })()}
                {matchId != null && (
                  <td className="px-2 py-2 text-right">
                    <AddToBetslip matchId={matchId} outcome={r.key} odds={r.odd} />
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
      </div>
      {odds.best_edge != null && odds.best_edge >= VALUE_THRESHOLD && odds.best_outcome && (
        <p className="text-muted text-sm leading-relaxed">
          {t(lang, "odds.valueHint", {
            edge: pp(odds.best_edge),
            outcome: outcomeLabel(lang, odds.best_outcome),
          })}
        </p>
      )}
    </section>
  );
}

export default ValueBetBadge;
