"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getMatch } from "@/lib/api";
import { readSlip, removePick, type BetslipEntry } from "@/lib/betslip";
import { useLang } from "@/lib/i18n-client";
import { tLang } from "@/lib/i18n-fallback";
import type { MatchOut } from "@/lib/types";

type Hydrated = BetslipEntry & { match: MatchOut | null };

function modelProb(m: MatchOut | null, side: "H" | "D" | "A"): number | null {
  if (!m?.prediction) return null;
  return side === "H" ? m.prediction.p_home_win
    : side === "A" ? m.prediction.p_away_win
    : m.prediction.p_draw;
}

function kelly(prob: number, odds: number, cap = 0.25): number {
  if (prob <= 0 || odds <= 1) return 0;
  const edge = prob * odds - 1;
  if (edge <= 0) return 0;
  return Math.min(cap, edge / (odds - 1));
}

export default function ParlayPage() {
  const lang = useLang();
  const [entries, setEntries] = useState<BetslipEntry[]>([]);
  const [hydrated, setHydrated] = useState<Hydrated[]>([]);

  useEffect(() => {
    function load() { setEntries(readSlip()); }
    load();
    window.addEventListener("betslip-change", load);
    return () => window.removeEventListener("betslip-change", load);
  }, []);

  useEffect(() => {
    let cancelled = false;
    Promise.all(
      entries.map(async (e) => {
        try { return { ...e, match: await getMatch(e.match_id) }; }
        catch { return { ...e, match: null }; }
      }),
    ).then((r) => { if (!cancelled) setHydrated(r); });
    return () => { cancelled = true; };
  }, [entries]);

  const back = tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" });
  const title = tLang(lang, {
    en: "Parlay calculator",
    vi: "Parlay — ghép kèo",
    th: "คำนวณพาร์เลย์",
    zh: "连串盘计算器",
    ko: "파레이 계산기",
  });

  if (entries.length === 0) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12 space-y-6">
        <Link href="/" className="btn-ghost text-sm">{back}</Link>
        <h1 className="headline-section">{title}</h1>
        <div className="card space-y-3">
          <p className="text-secondary">
            {tLang(lang, {
              en: "Your parlay is empty. Open any match, pick an outcome on the odds panel, and it lands here automatically.",
              vi: "Chưa có kèo nào. Vào bất kỳ trận nào, bấm một lựa chọn ở bảng odds, hệ thống tự thêm vào đây.",
              th: "พาร์เลย์ของคุณว่างอยู่ เปิดแมตช์ใดก็ได้แล้วเลือกผลที่แผงราคา ระบบจะเพิ่มให้อัตโนมัติ",
              zh: "您的连串盘为空。打开任一比赛,在赔率面板选择结果,系统会自动添加。",
              ko: "파레이가 비어 있습니다. 경기를 열고 배당 패널에서 결과를 선택하면 자동으로 추가됩니다.",
            })}
          </p>
          <div className="flex gap-3 pt-2">
            <Link href="/" className="btn-primary text-sm">
              {tLang(lang, {
                en: "Browse matches",
                vi: "Xem trận đang có",
                th: "ดูรายการแมตช์",
                zh: "浏览比赛",
                ko: "경기 보기",
              })}
            </Link>
            <Link href="/strategies" className="btn-ghost text-sm">
              {tLang(lang, {
                en: "Explore strategies",
                vi: "Xem chiến thuật",
                th: "ดูกลยุทธ์",
                zh: "查看策略",
                ko: "전략 보기",
              })}
            </Link>
          </div>
        </div>
      </main>
    );
  }

  // Independent-leg assumption: combined probability = product of per-leg probs.
  // Real parlays correlate (same-match multi-events especially), but across
  // different matches the independence approximation is fine.
  const legs = hydrated.map((e) => {
    const p = modelProb(e.match, e.outcome);
    return { ...e, model_p: p };
  });

  const allHavePreds = legs.every((l) => l.model_p !== null);
  const combinedProb = allHavePreds
    ? legs.reduce((acc, l) => acc * (l.model_p as number), 1)
    : null;
  const combinedOdds = legs.reduce((acc, l) => acc * l.odds, 1);
  const combinedStake = combinedProb != null ? kelly(combinedProb, combinedOdds) : 0;
  const expectedValue = combinedProb != null ? combinedProb * combinedOdds - 1 : null;

  return (
    <main className="mx-auto max-w-3xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">{back}</Link>
      <header className="space-y-2">
        <h1 className="headline-section">{title}</h1>
        <p className="text-secondary">
          {tLang(lang, {
            en: "Treats legs as independent. Multi-market picks on the same match are correlated — model those externally.",
            vi: "Giả định các vế độc lập. Nhiều kèo cùng 1 trận bị tương quan — tính riêng bên ngoài.",
            th: "ถือว่าแต่ละวางแทงเป็นอิสระ แมตช์เดียวกันหลายตลาดมีความสัมพันธ์ — คำนวณแยก",
            zh: "各注视为独立。同一场比赛多市场之间相关,需另行建模。",
            ko: "각 레그를 독립으로 간주. 같은 경기의 다중 마켓은 상관관계 있어 별도 계산 필요.",
          })}
        </p>
      </header>

      <section className="card grid grid-cols-2 md:grid-cols-4 gap-6">
        <div>
          <p className="label">{tLang(lang, { en: "Legs", vi: "Số vế", th: "จำนวนวาง", zh: "注数", ko: "레그" })}</p>
          <p className="stat">{legs.length}</p>
        </div>
        <div>
          <p className="label">{tLang(lang, { en: "Model P(all)", vi: "P(all) theo model", th: "P(ทั้งหมด) จากโมเดล", zh: "模型 P(全中)", ko: "모델 P(전부)" })}</p>
          <p className="stat text-neon">{combinedProb != null ? `${(combinedProb * 100).toFixed(1)}%` : "—"}</p>
        </div>
        <div>
          <p className="label">{tLang(lang, { en: "Combined odds", vi: "Odds ghép", th: "ราคารวม", zh: "累计赔率", ko: "합산 배당" })}</p>
          <p className="stat">{combinedOdds.toFixed(2)}</p>
        </div>
        <div>
          <p className="label">{tLang(lang, { en: "Expected value", vi: "Kỳ vọng", th: "มูลค่าคาดหวัง", zh: "期望值", ko: "기대값" })}</p>
          <p className={`stat ${expectedValue != null && expectedValue > 0 ? "text-neon" : expectedValue != null && expectedValue < 0 ? "text-error" : ""}`}>
            {expectedValue != null ? `${expectedValue >= 0 ? "+" : ""}${(expectedValue * 100).toFixed(1)}%` : "—"}
          </p>
        </div>
      </section>

      {combinedProb != null && expectedValue! > 0 && (
        <section className="card">
          <p className="label">
            {tLang(lang, {
              en: "Kelly stake (fractional, capped 25%)",
              vi: "Stake Kelly (phân số, cap 25%)",
              th: "สเตค Kelly (เศษส่วน สูงสุด 25%)",
              zh: "Kelly 注额(分数式,上限 25%)",
              ko: "Kelly 스테이크 (분수, 25% 상한)",
            })}
          </p>
          <p className="stat text-neon">{(combinedStake * 100).toFixed(1)}%</p>
          <p className="text-[11px] text-muted">
            {tLang(lang, {
              en: "Share of bankroll to wager on this parlay. Full Kelly is brutal on estimate error — fractional cap protects you.",
              vi: "Tỷ lệ bankroll bỏ vào parlay này. Full Kelly trừng phạt sai số rất mạnh — cap phân số bảo vệ bạn.",
              th: "สัดส่วนเงินทุนที่จะวาง Full Kelly โหดต่อความคลาดเคลื่อน — fractional cap ช่วยป้องกัน",
              zh: "投入此连串盘的资金比例。全 Kelly 对估计误差惩罚极大,分数上限能保护你。",
              ko: "이 파레이에 투입할 자금 비율. 풀 Kelly는 추정 오차에 가혹 — 분수 캡이 보호합니다.",
            })}
          </p>
        </section>
      )}

      <section className="card p-0 overflow-x-auto">
        <table className="w-full font-mono text-sm">
          <thead className="text-muted">
            <tr className="border-b border-border">
              {[
                tLang(lang, { en: "Match", vi: "Trận", th: "แมตช์", zh: "比赛", ko: "경기" }),
                tLang(lang, { en: "Pick", vi: "Chọn", th: "ทาง", zh: "选择", ko: "선택" }),
                tLang(lang, { en: "Odds", vi: "Odds", th: "ราคา", zh: "赔率", ko: "배당" }),
                tLang(lang, { en: "Model P", vi: "P model", th: "P โมเดล", zh: "模型 P", ko: "모델 P" }),
                "",
              ].map((h, i) => (
                <th key={i} className="label px-3 py-3 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {legs.map((l) => {
              const m = l.match;
              const mp = l.model_p;
              const label = m ? `${m.home.short_name} vs ${m.away.short_name}` : `#${l.match_id}`;
              const drawLabel = tLang(lang, { en: "Draw", vi: "Hoà", th: "เสมอ", zh: "平", ko: "무" });
              const sideLabel = l.outcome === "H"
                ? m?.home.short_name ?? "Home"
                : l.outcome === "A"
                ? m?.away.short_name ?? "Away"
                : drawLabel;
              return (
                <tr key={`${l.match_id}-${l.outcome}`} className="border-b border-border-muted">
                  <td className="px-3 py-2">
                    {m ? <Link href={`/match/${m.id}`} className="hover:text-neon">{label}</Link> : label}
                  </td>
                  <td className="px-3 py-2">{sideLabel}</td>
                  <td className="px-3 py-2 tabular-nums">{l.odds.toFixed(2)}</td>
                  <td className="px-3 py-2 tabular-nums text-neon">
                    {mp != null ? `${Math.round(mp * 100)}%` : "—"}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => removePick(l.match_id, l.outcome)}
                      className="text-muted hover:text-error"
                      aria-label={tLang(lang, { en: "Remove", vi: "Xoá", th: "ลบ", zh: "移除", ko: "제거" })}
                    >×</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </main>
  );
}
