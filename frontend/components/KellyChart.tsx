import { tFor } from "@/lib/i18n-server";
import type { Lang } from "@/lib/i18n";
import { tLang } from "@/lib/i18n-fallback";

type KellyPoint = { date: string; bets: number; bankroll: number };
type KellyData = {
  season: string;
  threshold: number;
  cap: number;
  starting_units: number;
  final_units: number;
  peak_units: number;
  max_drawdown_pct: number;
  total_bets: number;
  roi_percent: number;
  points: KellyPoint[];
};

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

async function fetchKelly(
  season: string, threshold: number, cap: number, starting: number, league?: string,
): Promise<KellyData | null> {
  const qs = new URLSearchParams({
    season, threshold: String(threshold), cap: String(cap), starting: String(starting),
  });
  if (league) qs.set("league", league);
  const res = await fetch(`${BASE}/api/stats/roi/kelly?${qs}`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export default async function KellyChart({
  season, threshold = 0.05, cap = 0.25, starting = 100, league, lang,
}: {
  season: string; threshold?: number; cap?: number; starting?: number;
  league?: string; lang: Lang;
}) {
  const t = tFor(lang);
  const d = await fetchKelly(season, threshold, cap, starting, league);

  const title = tLang(lang, {
    en: "Virtual bankroll · Kelly",
    vi: "Bankroll ảo · Kelly",
    th: "บัญชีจำลอง · Kelly",
    zh: "虚拟资金 · Kelly",
    ko: "가상 뱅크롤 · Kelly",
  });

  if (!d || d.points.length < 2) {
    return (
      <section className="card space-y-2">
        <h2 className="font-display font-semibold uppercase tracking-tight">{title}</h2>
        <p className="text-muted text-sm">{t("roi.empty")}</p>
      </section>
    );
  }

  const W = 720, H = 180, PAD = 8;
  const xs = d.points.map((_, i) => i);
  const ys = d.points.map((p) => p.bankroll);
  const minY = Math.min(d.starting_units, ...ys);
  const maxY = Math.max(d.starting_units, d.peak_units, ...ys);
  const rangeY = maxY - minY || 1;
  const rangeX = xs[xs.length - 1] || 1;

  const project = (i: number, y: number) => ({
    x: PAD + (i / rangeX) * (W - 2 * PAD),
    y: H - PAD - ((y - minY) / rangeY) * (H - 2 * PAD),
  });
  const coords = d.points.map((p, i) => ({ ...project(i, p.bankroll), bankroll: p.bankroll }));
  const path = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ");
  const startY = project(0, d.starting_units).y;
  const peakY = project(0, d.peak_units).y;

  const up = d.final_units >= d.starting_units;
  const lineColor = up ? "#E0FF32" : "#FF4D4F";

  const drawdownArea = [
    ...coords.filter((_, i) => d.points[i].bankroll < d.peak_units).map((c) => `${c.x.toFixed(1)},${c.y.toFixed(1)}`),
    ...coords.filter((_, i) => d.points[i].bankroll < d.peak_units).reverse()
      .map((c) => `${c.x.toFixed(1)},${peakY.toFixed(1)}`),
  ];
  const drawdownPoly = drawdownArea.length > 0 ? drawdownArea.join(" ") : null;
  const thresholdPP = `${Math.round(threshold * 100)}`;
  const capPct = Math.round(d.cap * 100);

  const L = {
    starting: tLang(lang, { en: "Starting", vi: "Khởi đầu", th: "เริ่มต้น", zh: "起始", ko: "시작" }),
    peak:     tLang(lang, { en: "Peak",     vi: "Đỉnh",    th: "จุดสูงสุด", zh: "峰值", ko: "고점" }),
    final:    tLang(lang, { en: "Final",    vi: "Cuối",    th: "สุดท้าย",  zh: "最终", ko: "최종" }),
    maxDD:    tLang(lang, { en: "Max DD",   vi: "Drawdown", th: "ดรอว์ดาวน์", zh: "最大回撤", ko: "최대 낙폭" }),
    bets:     tLang(lang, { en: "bets",     vi: "kèo",     th: "เดิมพัน",  zh: "注",  ko: "베팅" }),
    wiped:    tLang(lang, { en: "Bankroll wiped", vi: "Bankroll bị sập", th: "บัญชีหมด",
                            zh: "资金归零", ko: "뱅크롤 소진" }),
    stake: tLang(lang, {
      en: `Each ≥${thresholdPP}pp-edge bet is staked via fractional Kelly capped at ${capPct}% of the current bankroll, compounding over time. Starting balance ${d.starting_units}u.`,
      vi: `Mỗi kèo edge ≥ ${thresholdPP}pp được stake bằng fractional Kelly capped ${capPct}% bankroll, compounding theo thời gian. Bắt đầu với ${d.starting_units}u.`,
      th: `ทุกเดิมพันเอดจ์ ≥ ${thresholdPP}pp ใช้ Kelly แบบเศษส่วน เพดาน ${capPct}% ของบัญชีปัจจุบัน ทบต้นตามเวลา เริ่มที่ ${d.starting_units}u`,
      zh: `对每笔 edge ≥ ${thresholdPP}pp 的下注,按当前资金 ${capPct}% 上限的分数凯利注额,随时间复利。起始 ${d.starting_units}u。`,
      ko: `edge ≥ ${thresholdPP}pp 베팅마다 현재 뱅크롤의 ${capPct}% 한도 내 분수 켈리로 복리 스테이킹. 시작 ${d.starting_units}u.`,
    }),
    wipedExplainer: tLang(lang, {
      en: `At a ${thresholdPP}pp threshold, ${capPct}% Kelly reduces the bankroll to ~0 — the "edges" flagged at this level are noise + adverse selection, not real edges. Flat 1u is also losing (compare mode on this page); Kelly just magnifies the loss exponentially.`,
      vi: `Ở ngưỡng ${thresholdPP}pp, Kelly ${capPct}% làm bankroll về ~0 — nghĩa là cái "edge" model flag ở mức này không phải edge thật mà là noise + adverse selection. Flat 1u cũng lỗ (so trên page này), Kelly chỉ làm mất nhanh hơn theo cấp số nhân.`,
      th: `ที่เกณฑ์ ${thresholdPP}pp และ Kelly ${capPct}% บัญชีเหลือ ~0 — "เอดจ์" ระดับนี้เป็นสัญญาณรบกวน + adverse selection ไม่ใช่เอดจ์จริง Flat 1u ก็ขาดทุน Kelly แค่ขยายผลขาดทุนแบบทวีคูณ`,
      zh: `在 ${thresholdPP}pp 阈值下,${capPct}% 凯利将资金降至 ~0 — 在该水平被标记的"edge"是噪声 + 逆向选择,不是真实 edge。固定 1u 也在亏损,凯利只是以指数级放大亏损。`,
      ko: `${thresholdPP}pp 임계치에서 ${capPct}% 켈리는 뱅크롤을 ~0까지 감소시킵니다. 이 수준에서 플래그된 "엣지"는 실제 엣지가 아닌 노이즈 + 역선택입니다. 플랫 1u도 손실이며, 켈리는 손실을 지수적으로 확대할 뿐입니다.`,
    }),
    fixes: tLang(lang, {
      en: "Fixes to try: raise the edge threshold, use quarter-Kelly (cap ≤ 6%), or bet only on leagues with positive recent ROI at /roi/by-league.",
      vi: "Trong thực tế: raise threshold, dùng quarter-Kelly (cap ≤ 6%), hoặc chỉ đánh giải có ROI dương trong /roi/by-league.",
      th: "วิธีแก้: เพิ่มเกณฑ์เอดจ์ ใช้ quarter-Kelly (เพดาน ≤ 6%) หรือเดิมพันเฉพาะลีกที่มี ROI ล่าสุดเป็นบวกที่ /roi/by-league",
      zh: "修复方法: 提高 edge 阈值、使用四分之一凯利(上限 ≤ 6%)、或仅在 /roi/by-league 中 ROI 为正的联赛下注。",
      ko: "대안: edge 임계치 상향, 쿼터 켈리 사용 (한도 ≤ 6%), 또는 /roi/by-league에서 최근 ROI가 양수인 리그만 베팅.",
    }),
    disclaimer: tLang(lang, {
      en: "Simulated on historical value bets only — no custody, no stakes placed.",
      vi: "Không phải stake thật — mô phỏng trên kèo lịch sử. Không custody, không đặt cược hộ.",
      th: "จำลองจากการเดิมพันย้อนหลังเท่านั้น ไม่มีการถือเงิน ไม่มีการวางเงินจริง",
      zh: "仅基于历史价值投注的模拟 — 不托管资金,不代客下注。",
      ko: "과거 가치 베팅에 대한 시뮬레이션일 뿐 — 자금 보관 없음, 실제 베팅 없음.",
    }),
  };

  return (
    <section className="card space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="font-display font-semibold uppercase tracking-tight">{title}</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 md:gap-6 font-mono text-sm tabular-nums w-full md:w-auto">
          <div>
            <p className="text-xs text-muted">{L.starting}</p>
            <p className="stat text-base">{d.starting_units.toFixed(0)}u</p>
          </div>
          <div>
            <p className="text-xs text-muted">{L.peak}</p>
            <p className="stat text-base text-neon">{d.peak_units.toFixed(1)}u</p>
          </div>
          <div>
            <p className="text-xs text-muted">{L.final}</p>
            <p className="stat text-base" style={{ color: lineColor }}>{d.final_units.toFixed(1)}u</p>
          </div>
          <div>
            <p className="text-xs text-muted">ROI</p>
            <p className="stat text-base" style={{ color: lineColor }}>
              {d.roi_percent >= 0 ? "+" : ""}{d.roi_percent.toFixed(1)}%
            </p>
          </div>
          <div>
            <p className="text-xs text-muted">{L.maxDD}</p>
            <p className="stat text-base text-error">−{d.max_drawdown_pct.toFixed(1)}%</p>
          </div>
        </div>
      </div>

      <p className="text-muted text-sm">{L.stake}</p>

      <div className="overflow-x-auto">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full min-w-[360px]" preserveAspectRatio="none">
          <line x1={PAD} x2={W - PAD} y1={startY} y2={startY} stroke="#242424" strokeDasharray="4 4" />
          <line x1={PAD} x2={W - PAD} y1={peakY} y2={peakY} stroke="#3a4a10" strokeDasharray="2 6" />
          {drawdownPoly && <polygon points={drawdownPoly} fill="rgba(255, 77, 79, 0.18)" />}
          <path d={path} fill="none" stroke={lineColor} strokeWidth="2" strokeLinejoin="round" />
          {coords.length > 0 && (
            <circle cx={coords[coords.length - 1].x} cy={coords[coords.length - 1].y} r="4" fill={lineColor} />
          )}
        </svg>
      </div>

      <div className="flex justify-between font-mono text-[10px] text-muted">
        <span>{d.points[0].date}</span>
        <span>{d.total_bets} {L.bets}</span>
        <span>{d.points[d.points.length - 1].date}</span>
      </div>

      {d.max_drawdown_pct > 95 && (
        <div className="rounded-xl border border-error/40 bg-high p-4 space-y-2">
          <p className="font-mono text-[10px] uppercase tracking-wide text-error">{L.wiped}</p>
          <p className="text-secondary text-sm leading-relaxed">{L.wipedExplainer}</p>
          <p className="text-secondary text-sm leading-relaxed">{L.fixes}</p>
        </div>
      )}

      <p className="font-mono text-[10px] uppercase tracking-wide text-muted">{L.disclaimer}</p>
    </section>
  );
}
