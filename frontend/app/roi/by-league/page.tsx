import type { Metadata } from "next";
import Link from "next/link";

import { getLang, tFor } from "@/lib/i18n-server";
import type { Lang } from "@/lib/i18n";
import { tLang } from "@/lib/i18n-fallback";
import { leagueByCode } from "@/lib/leagues";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "ROI by league — where the edge actually shows up · predictor.nullshift.sh",
  description:
    "Flat-stake ROI split per league on every model edge ≥ 5pp. " +
    "Walks the same bet universe as /roi but tells you which market the P&L " +
    "is actually coming from — EPL vs La Liga vs Serie A vs Bundesliga vs Ligue 1.",
  alternates: { canonical: "/roi/by-league" },
};

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

// Sample-size trust tiers — fewer than 20 bets per league per window is
// dominated by variance (one coin-flip run can flip the sign). We grade:
//   - ≥ 20 bets: trust
//   - 10..19  :  "noisy" (amber) — directional but don't bet the farm
//   - < 10    :  "sparse" (muted) — not actionable on its own
const TRUSTED_BETS = 20;
const MIN_BETS = 10;

type RoiLeague = {
  league_code: string;
  bets: number;
  wins: number;
  pnl_vig: number;
  pnl_nov: number;
  roi_vig_pct: number;
  roi_nov_pct: number;
  mean_log_loss: number;
  scored: number;
};

type RoiByLeague = {
  window: string;
  threshold: number;
  season: string | null;
  leagues: RoiLeague[];
};

const WINDOWS = ["7d", "30d", "90d", "season"] as const;
const THRESHOLDS = [0.03, 0.05, 0.07, 0.1] as const;

async function fetchByLeague(window: string, threshold: number): Promise<RoiByLeague | null> {
  const qs = new URLSearchParams({ window, threshold: String(threshold), season: "2025-26" });
  const res = await fetch(`${BASE}/api/stats/roi/by-league?${qs}`, { next: { revalidate: 600 } });
  if (!res.ok) return null;
  return res.json();
}

function signed(x: number, digits = 2) {
  return `${x > 0 ? "+" : ""}${x.toFixed(digits)}`;
}

function copy(lang: Lang) {
  return {
    blurb: tLang(lang, {
      en: "Per-league ROI · edge ≥ 5pp, 1-unit flat stake",
      vi: "ROI theo giải · edge ≥ 5pp, stake 1 đơn vị",
      th: "ROI ต่อลีก · edge ≥ 5pp, เดิมพันคงที่ 1 หน่วย",
      zh: "各联赛 ROI · edge ≥ 5pp,固定 1 单位注额",
      ko: "리그별 ROI · edge ≥ 5pp, 플랫 1유닛",
    }),
    title: tLang(lang, {
      en: "Where does the edge actually show up?",
      vi: "Biên lợi nhuận ở giải nào?",
      th: "เอดจ์เกิดที่ไหนกันแน่?",
      zh: "edge 究竟出现在哪里?",
      ko: "엣지는 어디에서 나오는가?",
    }),
    subhead: tLang(lang, {
      en: "Aggregate ROI can look flat while the underlying P&L is very uneven. This page splits it per league so you can see which markets the edge is actually coming from.",
      vi: "Toàn thị trường có thể hòa vốn, nhưng P&L trong đó phân bố không đều. Trang này tách ROI flat-stake theo từng giải để bạn thấy giải nào model đang kiếm tiền thật, giải nào bị thị trường đè.",
      th: "ROI รวมอาจดูเสมอทุน แต่ P&L ภายในกระจายไม่เท่ากัน หน้านี้แยก ROI แบบ flat-stake ตามลีกเพื่อดูว่าตลาดไหนโมเดลได้เงินจริง ตลาดไหนโดนบี้",
      zh: "总体 ROI 可能持平,但内部 P&L 分布非常不均。本页按联赛拆分 flat-stake ROI,让您看到 edge 真实来自哪里。",
      ko: "전체 ROI는 평평해 보여도 내부 P&L은 매우 불균일할 수 있습니다. 이 페이지는 ROI를 리그별로 분리해 실제 엣지가 어디서 오는지 보여줍니다.",
    }),
    summary: (pos: number, total: number, noisyPos: number, noisyTotal: number) => {
      if (total > 0) {
        return tLang(lang, {
          en: `${pos}/${total} leagues have positive ROI with a trusted sample (≥ 20 bets). Leagues marked "noisy" (10-19) or "sparse" (<10) are directional only.`,
          vi: `${pos}/${total} giải có ROI dương ở mẫu đủ tin (≥ 20 kèo). Giải đánh dấu "ồn" (10-19) hoặc "ít mẫu" (<10) chỉ mang tính xu hướng.`,
          th: `${pos}/${total} ลีกมี ROI บวกบนตัวอย่างที่เชื่อถือได้ (≥ 20) ลีก "noisy" (10-19) หรือ "sparse" (<10) เป็นเพียงทิศทาง`,
          zh: `${pos}/${total} 个联赛在可信样本 (≥ 20) 下 ROI 为正。"noisy" (10-19) 或 "sparse" (<10) 仅表方向。`,
          ko: `신뢰 표본 (≥ 20)에서 ${pos}/${total} 리그가 ROI 양수. "noisy" (10-19) 또는 "sparse" (<10)는 방향성만.`,
        });
      }
      // No league has hit the trust threshold yet — report the directional
      // read so "all 5 positive but small sample" doesn't render as "0/0".
      return tLang(lang, {
        en: `No league has ≥ 20 bets yet at this threshold+window. Directional read (≥ 10 bets): ${noisyPos}/${noisyTotal} positive. Widen the window or threshold to build a trusted sample.`,
        vi: `Chưa giải nào đạt ≥ 20 kèo ở ngưỡng+cửa sổ này. Đọc xu hướng (≥ 10 kèo): ${noisyPos}/${noisyTotal} dương. Mở rộng cửa sổ hoặc ngưỡng để có mẫu đủ tin.`,
        th: `ยังไม่มีลีกใดถึง ≥ 20 เดิมพันที่ threshold+window นี้ ทิศทาง (≥ 10): ${noisyPos}/${noisyTotal} เป็นบวก`,
        zh: `当前阈值+窗口下,尚无联赛达到 ≥ 20 注。趋势读数 (≥ 10):${noisyPos}/${noisyTotal} 为正。`,
        ko: `현재 임계값+윈도우에서 ≥ 20 베팅 리그 없음. 방향성 (≥ 10): ${noisyPos}/${noisyTotal} 양수.`,
      });
    },
    summaryTitle: tLang(lang, { en: "Summary", vi: "Tóm tắt", th: "สรุป", zh: "摘要", ko: "요약" }),
    window: tLang(lang, { en: "window", vi: "cửa sổ", th: "ช่วงเวลา", zh: "窗口", ko: "기간" }),
    edge: "edge",
    league: tLang(lang, { en: "League", vi: "Giải", th: "ลีก", zh: "联赛", ko: "리그" }),
    bets: tLang(lang, { en: "Bets", vi: "Kèo", th: "เดิมพัน", zh: "注", ko: "베팅" }),
    wins: tLang(lang, { en: "Wins", vi: "Thắng", th: "ชนะ", zh: "胜", ko: "승" }),
    sparse: tLang(lang, { en: "sparse", vi: "ít mẫu", th: "น้อย", zh: "稀少", ko: "적음" }),
    noisy: tLang(lang, { en: "noisy", vi: "ồn", th: "เสียง", zh: "噪声", ko: "노이즈" }),
    noData: tLang(lang, { en: "No data", vi: "Chưa có dữ liệu", th: "ไม่มีข้อมูล", zh: "无数据", ko: "데이터 없음" }),
    footVig: tLang(lang, {
      en: "• ROI (vig) = 1u flat stake at best available bookmaker odds",
      vi: "• ROI (vig) = flat-stake 1u tại best-odds, ăn cả vig thị trường",
      th: "• ROI (vig) = flat-stake 1u ที่ราคาดีสุดของโบรกเกอร์",
      zh: "• ROI (vig) = 按博彩公司最佳赔率 flat-stake 1u",
      ko: "• ROI (vig) = 최고가 북 오즈 플랫 1u 스테이크",
    }),
    footNov: tLang(lang, {
      en: "• ROI (no-vig) = simulates a Polymarket-style zero-overround market",
      vi: "• ROI (no-vig) = mô phỏng thị trường Polymarket-style (0% phí)",
      th: "• ROI (no-vig) = จำลองตลาด Polymarket-style (0% vig)",
      zh: "• ROI (no-vig) = 模拟 Polymarket 式零 vig 市场",
      ko: "• ROI (no-vig) = Polymarket 스타일 제로 vig 시장 시뮬레이션",
    }),
    footSample: tLang(lang, {
      en: `• < ${TRUSTED_BETS} bets flagged: 10–19 "noisy" (amber), < 10 "sparse" (muted)`,
      vi: `• < ${TRUSTED_BETS} kèo đánh dấu: 10–19 "ồn" (vàng), < 10 "ít mẫu" (xám)`,
      th: `• < ${TRUSTED_BETS} เดิมพันจะมีป้าย: 10–19 "noisy" (อำพัน), < 10 "sparse" (เทา)`,
      zh: `• 少于 ${TRUSTED_BETS} 注会被标记: 10–19 "noisy" (琥珀), < 10 "sparse" (灰)`,
      ko: `• ${TRUSTED_BETS}개 미만 베팅 표시: 10–19 "noisy" (앰버), < 10 "sparse" (뮤트)`,
    }),
  };
}

export default async function RoiByLeaguePage({
  searchParams,
}: {
  searchParams: Promise<{ window?: string; threshold?: string }>;
}) {
  const sp = await searchParams;
  const window = (WINDOWS as readonly string[]).includes(sp.window ?? "")
    ? (sp.window as string)
    : "30d";
  const thr = Number(sp.threshold ?? "0.05");
  const threshold = (THRESHOLDS as readonly number[]).includes(thr) ? thr : 0.05;

  const lang = await getLang();
  const t = tFor(lang);
  const c = copy(lang);
  const data = await fetchByLeague(window, threshold);

  if (!data) {
    return (
      <main className="mx-auto max-w-5xl px-6 py-12">
        <div className="card text-error">{t("dash.apiError")}</div>
      </main>
    );
  }

  const positives = data.leagues.filter((l) => l.bets >= TRUSTED_BETS && l.roi_vig_pct > 0).length;
  const total = data.leagues.filter((l) => l.bets >= TRUSTED_BETS).length;
  const noisyPositives = data.leagues.filter((l) => l.bets >= MIN_BETS && l.roi_vig_pct > 0).length;
  const noisyTotal = data.leagues.filter((l) => l.bets >= MIN_BETS).length;

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-10">
      <Link href="/roi" className="btn-ghost text-sm">{t("common.back")}</Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">{c.blurb}</p>
        <h1 className="headline-section">{c.title}</h1>
        <p className="max-w-2xl text-secondary">{c.subhead}</p>
      </header>

      <section className="flex flex-wrap gap-2">
        <div className="flex flex-wrap gap-2 mr-4">
          <span className="font-mono text-[10px] uppercase tracking-wide text-muted self-center mr-1">
            {c.window}
          </span>
          {WINDOWS.map((w) => (
            <Link
              key={w}
              href={`/roi/by-league?window=${w}&threshold=${threshold}`}
              className={
                "rounded-full px-3 py-1 font-mono text-xs uppercase tracking-wide border " +
                (window === w
                  ? "border-neon bg-neon text-on-neon"
                  : "border-border text-secondary hover:border-neon hover:text-neon")
              }
            >
              {w}
            </Link>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="font-mono text-[10px] uppercase tracking-wide text-muted self-center mr-1">
            {c.edge}
          </span>
          {THRESHOLDS.map((t) => (
            <Link
              key={t}
              href={`/roi/by-league?window=${window}&threshold=${t}`}
              className={
                "rounded-full px-3 py-1 font-mono text-xs uppercase tracking-wide border " +
                (Math.abs(t - threshold) < 0.0001
                  ? "border-neon bg-neon text-on-neon"
                  : "border-border text-secondary hover:border-neon hover:text-neon")
              }
            >
              ≥ {Math.round(t * 100)}%
            </Link>
          ))}
        </div>
      </section>

      <section className="card space-y-3">
        <p className="font-mono text-[10px] uppercase tracking-wide text-muted">{c.summaryTitle}</p>
        <p className="text-secondary">{c.summary(positives, total, noisyPositives, noisyTotal)}</p>
      </section>

      <section className="card">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-[10px] uppercase tracking-wide text-muted">
              <tr className="text-left">
                <th className="py-2 pr-4">{c.league}</th>
                <th className="py-2 pr-4 text-right">{c.bets}</th>
                <th className="py-2 pr-4 text-right">{c.wins}</th>
                <th className="py-2 pr-4 text-right">P&amp;L (u)</th>
                <th className="py-2 pr-4 text-right">ROI (vig)</th>
                <th className="py-2 pr-4 text-right">ROI (no-vig)</th>
                <th className="py-2 pr-4 text-right">Log-loss</th>
              </tr>
            </thead>
            <tbody>
              {data.leagues.map((l) => {
                const info = leagueByCode(l.league_code);
                const labelEmoji = info?.emoji ?? "🌍";
                const labelName = info ? (lang === "vi" ? info.name_vi : info.name_en) : l.league_code;
                const sparse = l.bets < MIN_BETS;
                const noisy = !sparse && l.bets < TRUSTED_BETS;
                // Colour the ROI cells faithfully: only trust the sign when the
                // sample is big enough to have meaningful signal.
                const roiColor = (val: number) => {
                  if (sparse) return "text-muted";            // don't shout a 5-bet direction
                  if (noisy) return val > 0 ? "text-warning" : "text-warning";
                  return val > 0 ? "text-neon" : "text-error";
                };
                const tagClass = sparse
                  ? "text-muted"
                  : noisy
                  ? "text-warning"
                  : "";
                const rowClass =
                  "border-t border-border-muted " +
                  (sparse ? "text-muted " : "") +
                  (noisy ? "opacity-90" : "");
                return (
                  <tr key={l.league_code} className={rowClass}>
                    <td className="py-2 pr-4">
                      <span className="mr-2">{labelEmoji}</span>
                      <span className="font-display uppercase tracking-tighter">{labelName}</span>
                      {sparse && (
                        <span className={"ml-2 font-mono text-[9px] uppercase tracking-wide " + tagClass}>
                          {c.sparse}
                        </span>
                      )}
                      {noisy && (
                        <span className={"ml-2 font-mono text-[9px] uppercase tracking-wide " + tagClass}>
                          {c.noisy}
                        </span>
                      )}
                    </td>
                    <td className="py-2 pr-4 text-right font-mono tabular-nums">{l.bets}</td>
                    <td className="py-2 pr-4 text-right font-mono tabular-nums">{l.wins}</td>
                    <td className="py-2 pr-4 text-right font-mono tabular-nums">{signed(l.pnl_vig)}</td>
                    <td className={"py-2 pr-4 text-right font-mono tabular-nums " + roiColor(l.roi_vig_pct)}>
                      {signed(l.roi_vig_pct)}%
                    </td>
                    <td className={"py-2 pr-4 text-right font-mono tabular-nums " + roiColor(l.roi_nov_pct)}>
                      {signed(l.roi_nov_pct)}%
                    </td>
                    <td className="py-2 pr-4 text-right font-mono tabular-nums text-muted">
                      {l.mean_log_loss.toFixed(3)}
                    </td>
                  </tr>
                );
              })}
              {data.leagues.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-muted">{c.noData}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="font-mono text-[11px] uppercase tracking-wide text-muted space-y-1">
        <p>{c.footVig}</p>
        <p>{c.footNov}</p>
        <p>{c.footSample}</p>
      </section>
    </main>
  );
}
