import type { Markets } from "@/lib/api";
import type { Lang } from "@/lib/i18n";

function pct(x: number) {
  return `${(x * 100).toFixed(1)}%`;
}

function fairOdds(p: number): string {
  if (p <= 0 || p >= 1) return "—";
  return (1 / p).toFixed(2);
}

type Row = {
  market: string;
  selection: string;
  modelProb: number;
  note?: string;
};

export default function MarketsEdge({ markets, lang, homeShort, awayShort }: {
  markets: Markets;
  lang: Lang;
  homeShort: string;
  awayShort: string;
}) {
  // SGP correlation explainer: compare joint vs naive product of marginals.
  // Books often price SGPs as if independent; the difference here is the
  // systematic mispricing we expose to the user.
  const sgp = markets.prob_sgp_btts_over_2_5 ?? 0;
  const naiveSgp = markets.prob_btts * markets.prob_over_2_5;
  const sgpDelta = sgp - naiveSgp; // positive = book independence assumption UNDER-prices

  const rows: Row[] = [
    { market: "Over/Under 2.5", selection: "Over", modelProb: markets.prob_over_2_5 },
    { market: "Over/Under 2.5", selection: "Under", modelProb: 1 - markets.prob_over_2_5 },
    { market: "Over/Under 1.5", selection: "Over", modelProb: markets.prob_over_1_5 },
    { market: "Over/Under 3.5", selection: "Over", modelProb: markets.prob_over_3_5 },
    { market: "BTTS", selection: "Yes", modelProb: markets.prob_btts },
    { market: "BTTS", selection: "No", modelProb: 1 - markets.prob_btts },
  ];

  if (markets.prob_ah_home_minus_1_5 !== undefined) {
    rows.push(
      { market: `AH ${homeShort} -1.5`, selection: homeShort, modelProb: markets.prob_ah_home_minus_1_5 },
      { market: `AH ${homeShort} -0.5`, selection: homeShort, modelProb: markets.prob_ah_home_minus_0_5 ?? 0 },
      { market: `AH ${homeShort} +0.5`, selection: homeShort, modelProb: markets.prob_ah_home_plus_0_5 ?? 0 },
      { market: `AH ${homeShort} +1.5`, selection: homeShort, modelProb: markets.prob_ah_home_plus_1_5 ?? 0 },
    );
  }

  if (markets.prob_sgp_btts_over_2_5 !== undefined) {
    rows.push({
      market: "SGP: BTTS & Over 2.5",
      selection: "Yes",
      modelProb: sgp,
      note: sgpDelta > 0.01
        ? lang === "vi"
          ? `Book nhân rời → under-price ${Math.round(Math.abs(sgpDelta) * 100)}pp`
          : `Book independence assumption under-prices by ${Math.round(Math.abs(sgpDelta) * 100)}pp`
        : sgpDelta < -0.01
          ? lang === "vi"
            ? `Book nhân rời → over-price ${Math.round(Math.abs(sgpDelta) * 100)}pp`
            : `Book independence assumption over-prices by ${Math.round(Math.abs(sgpDelta) * 100)}pp`
          : undefined,
    });
  }

  return (
    <section className="card space-y-3">
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <h2 className="label">
          {lang === "vi" ? "Thị trường tương quan" : "Correlated markets"}
        </h2>
        <p className="text-[11px] text-muted max-w-md">
          {lang === "vi"
            ? "Xác suất lấy trực tiếp từ ma trận tỷ số. Kèo châu Á + SGP tính đúng tương quan — không phải tích của xác suất rời."
            : "Probabilities read directly off the scoreline matrix. Asian handicap + SGP use the correlated joint, not the naive product of marginals."}
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-[10px] uppercase tracking-wide text-muted">
            <tr className="text-left">
              <th className="py-2 pr-4">{lang === "vi" ? "Thị trường" : "Market"}</th>
              <th className="py-2 pr-4">{lang === "vi" ? "Cửa" : "Selection"}</th>
              <th className="py-2 pr-4 text-right">{lang === "vi" ? "Xác suất model" : "Model prob"}</th>
              <th className="py-2 pr-4 text-right">{lang === "vi" ? "Giá fair" : "Fair odds"}</th>
              <th className="py-2 pr-4">{lang === "vi" ? "Chú" : "Note"}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={`${r.market}-${r.selection}-${i}`} className="border-t border-border-muted">
                <td className="py-1.5 pr-4 font-mono text-xs text-secondary">{r.market}</td>
                <td className="py-1.5 pr-4 font-mono text-xs">{r.selection}</td>
                <td className="py-1.5 pr-4 text-right font-mono tabular-nums">
                  {pct(r.modelProb)}
                </td>
                <td className="py-1.5 pr-4 text-right font-mono tabular-nums text-neon">
                  {fairOdds(r.modelProb)}
                </td>
                <td className="py-1.5 pr-4 font-mono text-[10px] text-muted">{r.note ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="font-mono text-[10px] uppercase tracking-wide text-muted">
        {lang === "vi"
          ? "So với book: nếu giá thực > giá fair ở trên thì có value. Edge = (giá book / giá fair) − 1."
          : "Compare vs your book: if the book's price exceeds fair odds above, there's value. Edge = (book / fair) − 1."}
      </p>
    </section>
  );
}
