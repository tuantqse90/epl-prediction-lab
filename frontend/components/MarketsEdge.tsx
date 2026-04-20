import type { Markets, MarketsEdge as MarketsEdgeData } from "@/lib/api";
import type { Lang } from "@/lib/i18n";
import { tLang } from "@/lib/i18n-fallback";

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

  const L = {
    title:    tLang(lang, { en: "Correlated markets", vi: "Thị trường tương quan",
                             th: "ตลาดที่สัมพันธ์กัน", zh: "关联市场", ko: "상관 마켓" }),
    hint:     tLang(lang, {
      en: "Probabilities from the scoreline matrix. Best-odds is the highest quote across tracked books; edge = (prob × odds − 1) × 100.",
      vi: "Xác suất từ ma trận tỷ số. Best-odds là giá cao nhất trên các nhà cái đang theo dõi; edge = (prob × odds − 1) × 100.",
      th: "ความน่าจะเป็นจากเมทริกซ์สกอร์ Best-odds คือราคาสูงสุดในโบรกเกอร์ที่ติดตาม; edge = (prob × odds − 1) × 100",
      zh: "概率来自比分矩阵。Best-odds 为所跟踪博彩公司的最高报价;edge = (prob × odds − 1) × 100。",
      ko: "스코어 매트릭스에서 나온 확률. Best-odds는 추적 중인 북의 최고가; edge = (prob × odds − 1) × 100.",
    }),
    noData: tLang(lang, {
      en: "No prediction yet for this fixture.", vi: "Chưa có dự đoán cho trận này.",
      th: "ยังไม่มีการทำนายสำหรับคู่นี้", zh: "尚未对该场次做出预测。", ko: "아직 이 경기에 대한 예측이 없습니다.",
    }),
    selection: tLang(lang, { en: "Selection", vi: "Cửa", th: "ทางเลือก", zh: "选项", ko: "선택" }),
    fair:     tLang(lang, { en: "Fair",    vi: "Giá fair", th: "ราคายุติธรรม", zh: "公允赔率", ko: "공정" }),
    best:     tLang(lang, { en: "Best",    vi: "Best book", th: "ดีสุด", zh: "最佳", ko: "최고가" }),
    source:   tLang(lang, { en: "Source",  vi: "Nguồn", th: "แหล่ง", zh: "来源", ko: "출처" }),
  };

  return (
    <section className="card space-y-3">
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <h2 className="label">{L.title}</h2>
        <p className="text-[11px] text-muted max-w-md">{L.hint}</p>
      </div>

      {rows.length === 0 ? (
        <p className="text-muted text-sm">{L.noData}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-[10px] uppercase tracking-wide text-muted">
              <tr className="text-left">
                <th className="py-2 pr-4">{L.selection}</th>
                <th className="py-2 pr-4 text-right">Model</th>
                <th className="py-2 pr-4 text-right" title="Pinnacle devigged — sharp reference">Sharp</th>
                <th className="py-2 pr-4 text-right">{L.fair}</th>
                <th className="py-2 pr-4 text-right">{L.best}</th>
                <th className="py-2 pr-4 text-right">Edge</th>
                <th className="py-2 pr-4">{L.source}</th>
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
            {tLang(lang, {
              en: `True joint = ${pct(sgp)}. If book prices BTTS & O/U independently it comes out to ${pct(naiveSgp)} — `,
              vi: `Joint thật = ${pct(sgp)}. Nếu book coi BTTS & O/U độc lập thì prices ra ${pct(naiveSgp)} — `,
              th: `Joint จริง = ${pct(sgp)} หากโบรกเกอร์คิด BTTS & O/U แบบอิสระจะได้ ${pct(naiveSgp)} — `,
              zh: `真实联合概率 = ${pct(sgp)}。若博彩公司将 BTTS & O/U 独立定价会得到 ${pct(naiveSgp)} — `,
              ko: `실제 결합 확률 = ${pct(sgp)}. 북이 BTTS와 O/U를 독립으로 산정하면 ${pct(naiveSgp)}가 됩니다 — `,
            })}
            <span className={sgpDelta > 0 ? "text-neon" : "text-error"}>
              {sgpDelta > 0
                ? tLang(lang, {
                    en: `under-prices by ${Math.round(sgpDelta * 100)}pp`,
                    vi: `under-price ${Math.round(sgpDelta * 100)}pp`,
                    th: `ตั้งราคาต่ำเกินไป ${Math.round(sgpDelta * 100)}pp`,
                    zh: `低估 ${Math.round(sgpDelta * 100)}pp`,
                    ko: `${Math.round(sgpDelta * 100)}pp 저평가`,
                  })
                : tLang(lang, {
                    en: `over-prices by ${Math.round(-sgpDelta * 100)}pp`,
                    vi: `over-price ${Math.round(-sgpDelta * 100)}pp`,
                    th: `ตั้งราคาสูงเกินไป ${Math.round(-sgpDelta * 100)}pp`,
                    zh: `高估 ${Math.round(-sgpDelta * 100)}pp`,
                    ko: `${Math.round(-sgpDelta * 100)}pp 고평가`,
                  })}
            </span>.
          </p>
        </div>
      )}

      <p className="font-mono text-[10px] uppercase tracking-wide text-muted">
        {hasBookData
          ? tLang(lang, {
              en: `Neon row = edge ≥ ${threshold}pp at best book · Sharp = Pinnacle devigged (lowest retail vig) · Amber = model diverges from sharp by ≥ 3pp`,
              vi: `Viền neon = edge ≥ ${threshold}pp tại best book · Sharp = Pinnacle devigged (vig thấp nhất retail) · Màu cam = model lệch sharp ≥ 3pp`,
              th: `แถวเนียน = edge ≥ ${threshold}pp ที่ best book · Sharp = Pinnacle devigged (vig ต่ำสุดใน retail) · สีเหลืองอำพัน = โมเดลต่างจาก sharp ≥ 3pp`,
              zh: `霓虹行 = best book 下 edge ≥ ${threshold}pp · Sharp = Pinnacle 去 vig(零售最低) · 琥珀色 = 模型与 sharp 偏离 ≥ 3pp`,
              ko: `네온 행 = best book에서 edge ≥ ${threshold}pp · Sharp = Pinnacle devigged (리테일 vig 최저) · 앰버 = 모델이 sharp와 ≥ 3pp 괴리`,
            })
          : tLang(lang, {
              en: "No book odds stored yet for these markets — compare manually vs your book",
              vi: "Chưa có book odds cho các market này — so thủ công với book của bạn",
              th: "ยังไม่มีราคาโบรกเกอร์สำหรับตลาดเหล่านี้ — เทียบเองกับโบรกเกอร์ของคุณ",
              zh: "这些市场尚无博彩公司报价 — 请与您自己的博彩公司手动比较",
              ko: "이 마켓에는 아직 저장된 북 오즈가 없습니다 — 당신의 북과 수동으로 비교하세요",
            })}
      </p>
    </section>
  );
}
