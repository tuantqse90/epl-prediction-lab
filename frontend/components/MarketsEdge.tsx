import type { Markets, MarketsEdge as MarketsEdgeData } from "@/lib/api";
import type { Lang } from "@/lib/i18n";

function pct(x: number) {
  return `${(x * 100).toFixed(1)}%`;
}

function signedPp(x: number) {
  return `${x >= 0 ? "+" : ""}${x.toFixed(1)}pp`;
}

export default function MarketsEdge({
  markets,
  edge,
  lang,
  homeShort,
  awayShort,
}: {
  markets: Markets;
  // Phase 6b: when present, each row has best-book odds + edge_pp joined
  // from match_odds_markets. When absent, we only show model fair odds
  // (fall back to the phase-6-ship-1 UX — manual-compare view).
  edge: MarketsEdgeData | null;
  lang: Lang;
  homeShort: string;
  awayShort: string;
}) {
  // SGP correlation explainer: compare joint vs naive product of marginals.
  const sgp = markets.prob_sgp_btts_over_2_5 ?? 0;
  const naiveSgp = markets.prob_btts * markets.prob_over_2_5;
  const sgpDelta = sgp - naiveSgp;

  const rows = edge?.rows ?? [];
  const threshold = edge?.edge_threshold_pp ?? 5;
  const hasBookData = rows.some((r) => r.best_book_odds != null);

  // Replace "AH Home" with the actual team short name.
  const prettyLabel = (label: string) => label.replace(/^AH Home/, `AH ${homeShort}`);

  return (
    <section className="card space-y-3">
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <h2 className="label">
          {lang === "vi" ? "Thị trường tương quan" : "Correlated markets"}
        </h2>
        <p className="text-[11px] text-muted max-w-md">
          {lang === "vi"
            ? "Xác suất từ ma trận tỷ số. Best-odds là giá cao nhất trên các nhà cái đang theo dõi; edge = (prob × odds − 1) × 100."
            : "Probabilities from the scoreline matrix. Best-odds is the highest quote across tracked books; edge = (prob × odds − 1) × 100."}
        </p>
      </div>

      {rows.length === 0 ? (
        <p className="text-muted text-sm">
          {lang === "vi" ? "Chưa có dự đoán cho trận này." : "No prediction yet for this fixture."}
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-[10px] uppercase tracking-wide text-muted">
              <tr className="text-left">
                <th className="py-2 pr-4">{lang === "vi" ? "Cửa" : "Selection"}</th>
                <th className="py-2 pr-4 text-right">Model</th>
                <th className="py-2 pr-4 text-right" title="Pinnacle devigged — sharp reference">
                  Sharp
                </th>
                <th className="py-2 pr-4 text-right">{lang === "vi" ? "Giá fair" : "Fair"}</th>
                <th className="py-2 pr-4 text-right">{lang === "vi" ? "Best book" : "Best"}</th>
                <th className="py-2 pr-4 text-right">Edge</th>
                <th className="py-2 pr-4">{lang === "vi" ? "Nguồn" : "Source"}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const edgeColor = r.edge_pp == null
                  ? "text-muted"
                  : r.flagged
                  ? "text-neon"
                  : r.edge_pp >= 0
                  ? "text-secondary"
                  : "text-error";
                // Sharp disagreement: > 3pp either way = model diverges from
                // the sharp consensus, worth second-guessing the pick.
                const disagrees = r.sharp_disagreement_pp != null && Math.abs(r.sharp_disagreement_pp) >= 3.0;
                return (
                  <tr key={r.key} className={"border-t border-border-muted " + (r.flagged ? "bg-high/60" : "")}>
                    <td className="py-1.5 pr-4 font-mono text-xs text-secondary">
                      {r.flagged && <span className="inline-block w-1.5 h-1.5 rounded-full bg-neon mr-2 align-middle" />}
                      {prettyLabel(r.label)}
                    </td>
                    <td className="py-1.5 pr-4 text-right font-mono tabular-nums">{pct(r.model_prob)}</td>
                    <td
                      className={"py-1.5 pr-4 text-right font-mono tabular-nums " + (disagrees ? "text-warning" : "text-muted")}
                      title={r.sharp_disagreement_pp != null ? `model − sharp = ${signedPp(r.sharp_disagreement_pp)}` : ""}
                    >
                      {r.pinnacle_prob != null ? pct(r.pinnacle_prob) : "—"}
                    </td>
                    <td className="py-1.5 pr-4 text-right font-mono tabular-nums text-muted">{r.fair_odds.toFixed(2)}</td>
                    <td className="py-1.5 pr-4 text-right font-mono tabular-nums">
                      {r.best_book_odds != null ? r.best_book_odds.toFixed(2) : "—"}
                    </td>
                    <td className={"py-1.5 pr-4 text-right font-mono tabular-nums " + edgeColor}>
                      {r.edge_pp != null ? signedPp(r.edge_pp) : "—"}
                    </td>
                    <td className="py-1.5 pr-4 font-mono text-[10px] text-muted">
                      {r.best_source?.replace("odds-api:", "").replace("af:", "") ?? ""}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {markets.prob_sgp_btts_over_2_5 !== undefined && Math.abs(sgpDelta) > 0.01 && (
        <div className="border-t border-border-muted pt-3 space-y-1">
          <p className="label">SGP: BTTS & Over 2.5</p>
          <p className="text-sm text-secondary">
            {lang === "vi"
              ? `Joint thật = ${pct(sgp)}. Nếu book coi BTTS & O/U độc lập thì prices ra ${pct(naiveSgp)} — `
              : `True joint = ${pct(sgp)}. If book prices BTTS & O/U independently it comes out to ${pct(naiveSgp)} — `}
            <span className={sgpDelta > 0 ? "text-neon" : "text-error"}>
              {sgpDelta > 0
                ? lang === "vi" ? `under-price ${Math.round(sgpDelta * 100)}pp` : `under-prices by ${Math.round(sgpDelta * 100)}pp`
                : lang === "vi" ? `over-price ${Math.round(-sgpDelta * 100)}pp` : `over-prices by ${Math.round(-sgpDelta * 100)}pp`}
            </span>.
          </p>
        </div>
      )}

      <p className="font-mono text-[10px] uppercase tracking-wide text-muted">
        {hasBookData
          ? lang === "vi"
            ? `Viền neon = edge ≥ ${threshold}pp tại best book · Sharp = Pinnacle devigged (vig thấp nhất retail) · Màu cam = model lệch sharp ≥ 3pp`
            : `Neon row = edge ≥ ${threshold}pp at best book · Sharp = Pinnacle devigged (lowest retail vig) · Amber = model diverges from sharp by ≥ 3pp`
          : lang === "vi"
          ? "Chưa có book odds cho các market này — so thủ công với book của bạn"
          : "No book odds stored yet for these markets — compare manually vs your book"}
      </p>
    </section>
  );
}
