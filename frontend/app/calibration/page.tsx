import Link from "next/link";

import { getLang } from "@/lib/i18n-server";
import { tLang } from "@/lib/i18n-fallback";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type Bin = {
  bin_low: number;
  bin_high: number;
  n: number;
  mean_predicted: number;
  actual_hit_rate: number;
  gap: number;
};

type CalibrationResponse = {
  total: number;
  brier: number;
  log_loss: number;
  reliability: number;
  bins: Bin[];
};

async function fetchData(): Promise<CalibrationResponse | null> {
  try {
    const res = await fetch(`${BASE}/api/stats/reliability?n_bins=10`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return (await res.json()) as CalibrationResponse;
  } catch {
    return null;
  }
}

function pct(x: number) { return `${(x * 100).toFixed(1)}%`; }

// Reliability diagram SVG — 400x400, diagonal reference line + dots sized by bin n.
function ReliabilityChart({ bins }: { bins: Bin[] }) {
  const W = 440, H = 440, PAD = 40;
  const toX = (p: number) => PAD + p * (W - 2 * PAD);
  const toY = (p: number) => H - PAD - p * (H - 2 * PAD);
  const maxN = Math.max(...bins.map((b) => b.n), 1);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-lg">
      {/* Grid */}
      {[0, 0.25, 0.5, 0.75, 1].map((v) => (
        <g key={v}>
          <line x1={toX(v)} x2={toX(v)} y1={PAD} y2={H - PAD} stroke="rgba(255,255,255,0.05)" />
          <line y1={toY(v)} y2={toY(v)} x1={PAD} x2={W - PAD} stroke="rgba(255,255,255,0.05)" />
          <text x={toX(v)} y={H - 14} fill="#777" fontSize="10" textAnchor="middle">
            {pct(v)}
          </text>
          <text x={14} y={toY(v) + 3} fill="#777" fontSize="10">
            {pct(v)}
          </text>
        </g>
      ))}
      {/* Perfect-calibration diagonal */}
      <line
        x1={toX(0)} y1={toY(0)} x2={toX(1)} y2={toY(1)}
        stroke="#E0FF32" strokeWidth="1.5" strokeDasharray="4 4"
        opacity="0.4"
      />
      {/* Bin connectors */}
      <polyline
        fill="none"
        stroke="#E0FF32"
        strokeWidth="2"
        points={bins
          .map((b) => `${toX(b.mean_predicted)},${toY(b.actual_hit_rate)}`)
          .join(" ")}
      />
      {/* Bin dots (sized by n) */}
      {bins.map((b) => {
        const r = 3 + (b.n / maxN) * 10;
        return (
          <circle
            key={b.bin_low}
            cx={toX(b.mean_predicted)}
            cy={toY(b.actual_hit_rate)}
            r={r}
            fill="#E0FF32"
            fillOpacity="0.6"
            stroke="#E0FF32"
          />
        );
      })}
      {/* Axis labels */}
      <text x={W / 2} y={H - 2} fill="#999" fontSize="11" textAnchor="middle">
        Predicted confidence
      </text>
      <text
        x={-H / 2}
        y={10}
        fill="#999"
        fontSize="11"
        textAnchor="middle"
        transform="rotate(-90)"
      >
        Actual hit rate
      </text>
    </svg>
  );
}

export default async function CalibrationPage() {
  const lang = await getLang();
  const data = await fetchData();

  if (!data) {
    return <main className="mx-auto max-w-3xl px-6 py-12"><div className="card text-muted">—</div></main>;
  }

  const wellCal = data.reliability < 0.005;
  const brierVsBaseline = 0.25 - data.brier;  // higher = better vs coin-flip

  return (
    <main className="mx-auto max-w-4xl px-6 py-12 space-y-10">
      <Link href="/benchmark" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Benchmark", vi: "← Benchmark", th: "← Benchmark", zh: "← 基准", ko: "← 벤치마크" })}
      </Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">benchmark · calibration</p>
        <h1 className="headline-section">
          {tLang(lang, {
            en: "Calibration — does 60% confidence actually mean 60%?",
            vi: "Calibration — tự tin 60% có đúng là 60%?",
            th: "Calibration — 60% แปลว่า 60% จริงไหม?",
            zh: "Calibration — 60% 真的是 60% 吗?",
            ko: "Calibration — 60% 신뢰도가 실제로 60%인가?",
          })}
        </h1>
        <p className="max-w-2xl text-secondary">
          {tLang(lang, {
            en: "Perfect calibration = dots on the dashed diagonal. Dots above = model is too cautious (underpredicts); below = model is too confident (overpredicts). Dot size = sample count per bin.",
            vi: "Calibration chuẩn = dots trên đường chéo. Trên = model quá thận trọng (dự đoán thấp); dưới = model quá tự tin. Kích thước dot = số mẫu trong bin.",
            th: "Calibration สมบูรณ์ = จุดอยู่บนเส้นทแยง",
            zh: "完美校准 = 点在虚线对角线上",
            ko: "완벽한 보정 = 점이 대각선 위에",
          })}
        </p>
      </header>

      <section className="card grid grid-cols-2 md:grid-cols-4 gap-6">
        <div>
          <p className="label">{tLang(lang, { en: "Sample size", vi: "Cỡ mẫu", th: "ตัวอย่าง", zh: "样本", ko: "표본" })}</p>
          <p className="stat">{data.total.toLocaleString()}</p>
        </div>
        <div>
          <p className="label">Brier</p>
          <p className={`stat ${brierVsBaseline > 0.04 ? "text-neon" : brierVsBaseline > 0 ? "" : "text-error"}`}>
            {data.brier.toFixed(3)}
          </p>
          <p className="font-mono text-[11px] text-muted mt-1">vs 0.250 coin-flip</p>
        </div>
        <div>
          <p className="label">Log-loss</p>
          <p className="stat">{data.log_loss.toFixed(3)}</p>
          <p className="font-mono text-[11px] text-muted mt-1">vs 1.099 uniform</p>
        </div>
        <div>
          <p className="label">Reliability</p>
          <p className={`stat ${wellCal ? "text-neon" : "text-error"}`}>{data.reliability.toFixed(4)}</p>
          <p className="font-mono text-[11px] text-muted mt-1">
            {wellCal
              ? tLang(lang, { en: "well calibrated", vi: "calibration tốt", th: "calibration ดี", zh: "校准良好", ko: "보정 양호" })
              : tLang(lang, { en: "miscalibrated", vi: "miscalibrated", th: "miscalibrated", zh: "校准偏差", ko: "보정 불량" })}
          </p>
        </div>
      </section>

      <section className="card flex justify-center">
        <ReliabilityChart bins={data.bins} />
      </section>

      <section className="card p-0 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-[10px] uppercase tracking-wide text-muted">
            <tr className="border-b border-border">
              <th className="px-3 py-3 text-left">Bin</th>
              <th className="px-3 py-3 text-right">n</th>
              <th className="px-3 py-3 text-right">Mean pred</th>
              <th className="px-3 py-3 text-right">Actual hit</th>
              <th className="px-3 py-3 text-right">Gap</th>
            </tr>
          </thead>
          <tbody>
            {data.bins.map((b) => (
              <tr key={b.bin_low} className="border-t border-border-muted">
                <td className="px-3 py-2 font-mono tabular-nums text-muted">
                  {pct(b.bin_low)}–{pct(b.bin_high)}
                </td>
                <td className="px-3 py-2 text-right font-mono tabular-nums">{b.n}</td>
                <td className="px-3 py-2 text-right font-mono tabular-nums">{pct(b.mean_predicted)}</td>
                <td className="px-3 py-2 text-right font-mono tabular-nums">{pct(b.actual_hit_rate)}</td>
                <td
                  className={`px-3 py-2 text-right font-mono tabular-nums ${
                    Math.abs(b.gap) < 0.05 ? "text-muted" : b.gap > 0 ? "text-error" : "text-neon"
                  }`}
                >
                  {b.gap > 0 ? "+" : ""}{pct(b.gap)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="font-mono text-[11px] uppercase tracking-wide text-muted space-y-1">
        <p>• Gap = mean_predicted − actual_hit_rate · negative gap = model underconfident in this band</p>
        <p>• Brier score: 0 = perfect, 0.25 = coin-flip baseline. Lower is better.</p>
        <p>• Reliability = weighted mean squared gap across bins</p>
      </section>
    </main>
  );
}
