import type { Lang } from "@/lib/i18n";
import { t } from "@/lib/i18n";
import { tLang } from "@/lib/i18n-fallback";
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
export const VALUE_POPOUT_THRESHOLD = 0.10;

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
  const bestRow = odds.best_outcome
    ? rows.find((r) => r.key === odds.best_outcome)
    : null;
  const bestModelProb = bestRow && prediction
    ? bestRow.key === "H" ? prediction.p_home_win
      : bestRow.key === "D" ? prediction.p_draw
      : prediction.p_away_win
    : null;
  const bestKelly = bestRow && bestModelProb != null ? kelly(bestModelProb, bestRow.odd) : 0;
  const showPopout = odds.best_edge != null
    && odds.best_edge >= VALUE_POPOUT_THRESHOLD
    && bestRow != null;

  return (
    <section className="card space-y-3">
      <div className="flex items-baseline justify-between">
        <h2 className="font-display font-semibold uppercase tracking-tight">
          {t(lang, "odds.title")}
        </h2>
        <span className="font-mono text-[10px] text-muted">{odds.source}</span>
      </div>
      {showPopout && bestRow && (
        <div className="rounded-lg border-2 border-neon bg-neon/10 p-4 space-y-3">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <span className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.15em] text-neon font-semibold">
              <span aria-hidden>◆</span>
              {tLang(lang, { en: "Value detected", vi: "Cơ hội giá trị",
                              th: "พบค่า EV+", zh: "发现价值", ko: "가치 발견" })}
            </span>
            <span className="font-mono text-[10px] uppercase tracking-wide text-neon/70">
              {tLang(lang, { en: "Model beats market", vi: "Model > Nhà cái",
                              th: "โมเดลชนะตลาด", zh: "模型跑赢庄家", ko: "모델이 시장 초과" })}
            </span>
          </div>
          <div className="flex items-baseline gap-3 flex-wrap">
            <span className="font-display text-2xl md:text-3xl font-semibold uppercase tracking-tight text-neon">
              {bestRow.label}
            </span>
            <span className="font-mono text-sm text-secondary">
              @ {bestRow.odd.toFixed(2)}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-4 pt-2 border-t border-neon/30">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-wide text-muted">
                {tLang(lang, { en: "Edge", vi: "Chênh lệch", th: "เอดจ์", zh: "edge", ko: "엣지" })}
              </p>
              <p className="stat text-neon text-xl">{pp(odds.best_edge!)}</p>
            </div>
            <div>
              <p className="font-mono text-[10px] uppercase tracking-wide text-muted">
                {tLang(lang, { en: "Model prob", vi: "Xác suất model",
                                th: "ความน่าจะเป็นโมเดล", zh: "模型概率", ko: "모델 확률" })}
              </p>
              <p className="stat text-primary text-xl">
                {bestModelProb != null ? `${Math.round(bestModelProb * 100)}%` : "—"}
              </p>
            </div>
            <div>
              <p className="font-mono text-[10px] uppercase tracking-wide text-muted">
                {tLang(lang, { en: "Kelly stake", vi: "Stake Kelly",
                                th: "Kelly stake", zh: "凯利注额", ko: "켈리 스테이크" })}
              </p>
              <p className="stat text-neon text-xl">
                {bestKelly > 0 ? `${(bestKelly * 100).toFixed(1)}%` : "—"}
              </p>
            </div>
          </div>
          <p className="font-mono text-[10px] text-muted leading-relaxed">
            {tLang(lang, {
              en: "Fractional Kelly, capped at 25% of bankroll. Statistical guidance, not betting advice.",
              vi: "Kelly phân đoạn, tối đa 25% vốn. Chỉ là gợi ý thống kê — không phải lời khuyên cá cược.",
              th: "Kelly แบบเศษส่วน เพดาน 25% ของทุน เป็นคำแนะนำทางสถิติเท่านั้น ไม่ใช่คำแนะนำการพนัน",
              zh: "分数凯利,上限为资金的 25%。仅为统计参考,非投注建议。",
              ko: "분수 켈리, 뱅크롤의 25% 한도. 통계적 가이드일 뿐 베팅 조언이 아닙니다.",
            })}
          </p>
        </div>
      )}
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
