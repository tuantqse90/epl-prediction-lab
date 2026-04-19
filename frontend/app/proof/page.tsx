import Link from "next/link";

import { getLang, getLeagueSlug, leagueForApi, tFor } from "@/lib/i18n-server";
import { getLeague } from "@/lib/leagues";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type HistorySeason = {
  season: string;
  scored: number;
  correct: number;
  accuracy: number;
  mean_log_loss: number;
  baseline_home_accuracy: number;
};

type CalibrationBin = {
  bin_lo: number;
  bin_hi: number;
  n: number;
  mean_predicted: number;
  actual_hit_rate: number;
};

type Overall = {
  season: string;
  scored: number;
  correct: number;
  accuracy: number;
  baseline_home_accuracy: number;
  mean_log_loss: number;
  uniform_log_loss: number;
};

type StatsOut = {
  season: string;
  overall: Overall;
  brier: number;
  by_week: Array<{ week: number; accuracy: number; n: number }>;
  by_confidence: CalibrationBin[];
};

type Comparison = {
  days: number;
  league_code: string | null;
  scored: number;
  model_accuracy: number;
  bookmaker_accuracy: number;
  home_baseline_accuracy: number;
  uniform_baseline_accuracy: number;
  model_log_loss: number;
};

async function fetchHistory(league?: string): Promise<HistorySeason[]> {
  const qs = league ? `?league=${encodeURIComponent(league)}` : "";
  try {
    const res = await fetch(`${BASE}/api/stats/history${qs}`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

async function fetchCalibration(season: string, league?: string): Promise<StatsOut | null> {
  const qs = new URLSearchParams({ season });
  if (league) qs.set("league", league);
  try {
    const res = await fetch(`${BASE}/api/stats/calibration?${qs}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

async function fetchComparison(days: number, league?: string): Promise<Comparison | null> {
  const qs = new URLSearchParams({ days: String(days) });
  if (league) qs.set("league", league);
  try {
    const res = await fetch(`${BASE}/api/stats/comparison?${qs}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

function pct(x: number) {
  return `${Math.round(x * 100)}%`;
}

export default async function ProofPage() {
  const lang = await getLang();
  const t = tFor(lang);
  const league = await getLeagueSlug();
  const leagueInfo = getLeague(league);
  const leagueParam = leagueForApi(league);
  const leagueLabel = lang === "vi" ? leagueInfo.name_vi : leagueInfo.name_en;

  const [history, cal, comp30, compSeason, compAll] = await Promise.all([
    fetchHistory(leagueParam),
    fetchCalibration("2025-26", leagueParam),
    fetchComparison(30, leagueParam),
    fetchComparison(240, leagueParam), // ~current season window
    fetchComparison(0, leagueParam),
  ]);

  const totalScored = history.reduce((s, r) => s + r.scored, 0);
  const weightedAcc = totalScored > 0
    ? history.reduce((s, r) => s + r.correct, 0) / totalScored
    : (cal?.overall.accuracy ?? 0);
  const weightedBaseline = totalScored > 0
    ? history.reduce((s, r) => s + r.baseline_home_accuracy * r.scored, 0) / totalScored
    : (cal?.overall.baseline_home_accuracy ?? 0);
  const weightedLogLoss = totalScored > 0
    ? history.reduce((s, r) => s + r.mean_log_loss * r.scored, 0) / totalScored
    : (cal?.overall.mean_log_loss ?? 0);
  const uniformLogLoss = 1.0986; // -ln(1/3)
  const logLossGap = uniformLogLoss - weightedLogLoss;

  const maxAccuracy = history.length > 0 ? Math.max(...history.map((r) => r.accuracy), 0.55) : 0.55;

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-12">
      <Link href="/" className="btn-ghost text-sm">
        {t("common.back")}
      </Link>

      {/* Hero */}
      <header className="space-y-5 text-center md:text-left">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-neon">
          {lang === "vi" ? "Chứng minh" : "The proof"}
        </p>
        <h1 className="headline-hero">
          {lang === "vi"
            ? "Mô hình này có thật sự tốt hơn không?"
            : "Is the model actually any good?"}
        </h1>
        <p className="max-w-2xl text-secondary text-base md:text-lg">
          {lang === "vi"
            ? "Không phải lời quảng cáo — đây là số liệu thô. Mỗi dự đoán được ghi lại, chấm điểm sau trận, và mã hóa trước khi bóng lăn."
            : "Not marketing copy — raw numbers. Every prediction is timestamped before kickoff, scored after full-time, and hash-committed so nothing can be edited after."}
        </p>
        <p className="font-mono text-xs text-muted">
          {leagueInfo.emoji} {leagueLabel} · {totalScored.toLocaleString()} {lang === "vi" ? "trận đã chấm điểm" : "matches scored"}
        </p>
      </header>

      {/* Ensemble-upgrade banner — 3-leg ensemble went live 2026-04-19 */}
      <section className="relative overflow-hidden rounded-xl border border-neon/40 bg-black p-5 md:p-6">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-60"
          style={{
            background:
              "radial-gradient(closest-side at 0% 0%, rgba(224,255,50,0.18), transparent 55%)",
          }}
        />
        <div className="relative space-y-3">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.18em] text-neon">
              <span className="relative inline-flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full rounded-full bg-neon opacity-75 animate-ping" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-neon" />
              </span>
              {lang === "vi" ? "Ensemble v2 đã live" : "Ensemble v2 live"}
            </div>
            <span className="font-mono text-[10px] uppercase tracking-wide text-muted">
              {lang === "vi" ? "từ 19-04-2026" : "since 2026-04-19"}
            </span>
          </div>
          <p className="font-display text-xl md:text-2xl font-semibold text-primary">
            {lang === "vi"
              ? "3 model gộp, trọng số tối ưu trên 1,816 trận out-of-sample."
              : "Three-leg ensemble, weights tuned on 1,816 out-of-sample matches."}
          </p>
          <div className="grid grid-cols-3 gap-3 pt-2 border-t border-neon/20">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-wide text-muted">
                {lang === "vi" ? "Cấu hình cũ" : "Old config"}
              </p>
              <p className="font-mono text-sm text-secondary">elo=0.25 · xgb=0.15</p>
              <p className="font-mono text-xs text-muted">log-loss 0.9834 · acc 52.4%</p>
            </div>
            <div>
              <p className="font-mono text-[10px] uppercase tracking-wide text-neon">
                {lang === "vi" ? "Cấu hình mới" : "New config"}
              </p>
              <p className="font-mono text-sm text-neon">elo=0.20 · xgb=0.60</p>
              <p className="font-mono text-xs text-primary">log-loss 0.9278 · acc 56.2%</p>
            </div>
            <div>
              <p className="font-mono text-[10px] uppercase tracking-wide text-muted">
                {lang === "vi" ? "Thay đổi" : "Delta"}
              </p>
              <p className="stat text-neon text-lg">−5.6%</p>
              <p className="font-mono text-xs text-neon">+3.8pp {lang === "vi" ? "chính xác" : "accuracy"}</p>
            </div>
          </div>
          <p className="font-mono text-[10px] text-muted leading-relaxed pt-2">
            {lang === "vi"
              ? "Số live log-loss sẽ cập nhật khi có đủ trận đã chấm với model mới."
              : "Live log-loss over the new ensemble will populate as new matches finalize."}
          </p>
        </div>
      </section>

      {/* Big trust numbers */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card">
          <p className="label">{lang === "vi" ? "Chính xác" : "Accuracy"}</p>
          <p className="stat text-neon text-4xl md:text-5xl">{pct(weightedAcc)}</p>
          <p className="font-mono text-[11px] text-muted mt-1">
            vs {pct(weightedBaseline)} {lang === "vi" ? "baseline" : "baseline"}
          </p>
        </div>
        <div className="card">
          <p className="label">{lang === "vi" ? "Log-loss" : "Log-loss"}</p>
          <p className="stat text-neon text-4xl md:text-5xl">{weightedLogLoss.toFixed(3)}</p>
          <p className="font-mono text-[11px] text-muted mt-1">
            {lang === "vi" ? "thấp hơn" : "lower by"} {logLossGap.toFixed(3)} {lang === "vi" ? "so với random" : "vs random"}
          </p>
        </div>
        <div className="card">
          <p className="label">{lang === "vi" ? "Trận đã chấm" : "Matches scored"}</p>
          <p className="stat text-4xl md:text-5xl">{totalScored.toLocaleString()}</p>
          <p className="font-mono text-[11px] text-muted mt-1">
            {history.length} {lang === "vi" ? "mùa giải" : history.length === 1 ? "season" : "seasons"}
          </p>
        </div>
        <div className="card">
          <p className="label">{lang === "vi" ? "Chi phí dự đoán" : "Cost per pick"}</p>
          <p className="stat text-4xl md:text-5xl">$0</p>
          <p className="font-mono text-[11px] text-muted mt-1">
            {lang === "vi" ? "luôn miễn phí" : "always free"}
          </p>
        </div>
      </section>

      {/* Comparison: 3 windows — 30d, season, all-time */}
      {(() => {
        const windows = [
          {
            key: "30d",
            title: lang === "vi" ? "30 ngày gần nhất" : "Last 30 days",
            data: comp30,
          },
          {
            key: "season",
            title: lang === "vi" ? "Mùa hiện tại" : "Current season",
            data: compSeason,
          },
          {
            key: "all",
            title: lang === "vi" ? "Mọi thời điểm (kể từ 2019)" : "All-time (since 2019)",
            data: compAll,
          },
        ].filter((w) => w.data && w.data.scored >= 10);
        if (windows.length === 0) return null;
        return (
          <section className="card space-y-6">
            <div className="space-y-2">
              <h2 className="headline-section text-2xl md:text-3xl">
                {lang === "vi" ? "Mô hình vs nhà cái" : "Model vs the market"}
              </h2>
              <p className="text-secondary text-sm">
                {lang === "vi"
                  ? "Mỗi khung thời gian so argmax của model vs argmax của odds đã khử vig. Cùng tập trận — khác nhau ai đoán đúng."
                  : "Each window compares model argmax vs devigged-bookmaker argmax on the same finals. Same matches, different picks."}
              </p>
            </div>
            <div className="space-y-8">
              {windows.map((w) => {
                const c = w.data!;
                const rows = [
                  { label: lang === "vi" ? "MODEL" : "Model", value: c.model_accuracy, accent: true },
                  { label: lang === "vi" ? "NHÀ CÁI" : "Bookmakers", value: c.bookmaker_accuracy },
                  { label: lang === "vi" ? "LUÔN CHỦ NHÀ" : "Always Home", value: c.home_baseline_accuracy },
                  { label: lang === "vi" ? "NGẪU NHIÊN" : "Random", value: c.uniform_baseline_accuracy },
                ];
                const max = Math.max(0.6, ...rows.map((r) => r.value));
                const beat = c.model_accuracy > c.bookmaker_accuracy;
                const delta = Math.round((c.model_accuracy - c.bookmaker_accuracy) * 1000) / 10;
                return (
                  <div key={w.key} className="space-y-3">
                    <div className="flex items-baseline justify-between gap-3 flex-wrap">
                      <h3 className="font-display font-semibold uppercase tracking-tight text-lg">
                        {w.title}
                      </h3>
                      <div className="flex items-baseline gap-3 font-mono text-[11px]">
                        <span className="text-muted">
                          {c.scored} {lang === "vi" ? "trận" : "matches"}
                        </span>
                        <span className={beat ? "text-neon" : "text-error"}>
                          {beat ? "+" : ""}{delta.toFixed(1)}pp
                        </span>
                      </div>
                    </div>
                    <div className="space-y-2 font-mono text-xs">
                      {rows.map((r) => {
                        const width = Math.min(100, (r.value / max) * 100);
                        return (
                          <div key={r.label} className="flex items-center gap-3">
                            <span className={`w-28 shrink-0 uppercase tracking-wide ${r.accent ? "text-neon" : "text-secondary"}`}>
                              {r.label}
                            </span>
                            <div className="flex-1 h-6 rounded bg-high overflow-hidden">
                              <div
                                className={`h-full ${r.accent ? "bg-neon" : "bg-secondary/40"} transition-all`}
                                style={{ width: `${width}%` }}
                              />
                            </div>
                            <span className={`w-14 text-right tabular-nums ${r.accent ? "text-neon font-semibold" : "text-primary"}`}>
                              {pct(r.value)}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        );
      })()}

      {/* Per-season rolling accuracy */}
      {history.length > 0 && (
        <section className="card space-y-4">
          <h2 className="headline-section text-2xl md:text-3xl">
            {lang === "vi" ? "Chính xác theo từng mùa" : "Accuracy across seasons"}
          </h2>
          <p className="text-secondary text-sm">
            {lang === "vi"
              ? "Vạch dọc = baseline \"luôn chọn chủ nhà\". Thanh neon = model thắng baseline, đỏ = thua."
              : 'Vertical line = "always pick home" baseline. Neon = model beats baseline. Red = worse than baseline.'}
          </p>
          <div className="space-y-2">
            {history.map((r) => {
              const widthPct = (r.accuracy / maxAccuracy) * 100;
              const baselineLeftPct = (r.baseline_home_accuracy / maxAccuracy) * 100;
              const beats = r.accuracy > r.baseline_home_accuracy;
              return (
                <div key={r.season} className="flex items-center gap-3 font-mono text-xs">
                  <span className="w-20 shrink-0 text-muted">{r.season}</span>
                  <div className="relative flex-1 h-7 rounded bg-high overflow-hidden">
                    <div
                      className={`h-full transition-all ${beats ? "bg-neon" : "bg-error"}`}
                      style={{ width: `${widthPct}%` }}
                    />
                    <div
                      aria-label="baseline"
                      className="absolute top-0 bottom-0 w-[2px] bg-secondary/60"
                      style={{ left: `${baselineLeftPct}%` }}
                    />
                  </div>
                  <span className={`w-12 shrink-0 text-right tabular-nums ${beats ? "text-neon" : "text-error"}`}>
                    {pct(r.accuracy)}
                  </span>
                  <span className="w-16 shrink-0 text-right tabular-nums text-muted">
                    {r.scored}m
                  </span>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Calibration reliability */}
      {cal && cal.by_confidence.length > 0 && (
        <section className="card space-y-4">
          <h2 className="headline-section text-2xl md:text-3xl">
            {lang === "vi" ? "Độ tin cậy của xác suất" : "Calibration reliability"}
          </h2>
          <p className="text-secondary text-sm">
            {lang === "vi"
              ? "Khi model nói 70%, model có thật sự đúng ~70% các lần không? Nếu có, thanh neon trùng với vạch mờ bên phải."
              : "When the model says 70%, is it right ~70% of the time? If yes, the neon bar matches the faint marker on the right."}
          </p>
          <div className="overflow-x-auto">
            <table className="w-full font-mono text-sm">
              <thead className="text-muted">
                <tr className="border-b border-border">
                  <th className="label px-2 py-2 text-left">{lang === "vi" ? "Khoảng" : "Bin"}</th>
                  <th className="label px-2 py-2 text-right">N</th>
                  <th className="label px-2 py-2 text-right">{lang === "vi" ? "Dự đoán" : "Predicted"}</th>
                  <th className="label px-2 py-2 text-right">{lang === "vi" ? "Thực tế" : "Actual"}</th>
                  <th className="label px-2 py-2 text-left w-64">{lang === "vi" ? "Độ khớp" : "Reliability"}</th>
                </tr>
              </thead>
              <tbody>
                {cal.by_confidence.map((b) => {
                  const dpp = Math.round((b.actual_hit_rate - b.mean_predicted) * 100);
                  const cls = dpp >= 2 ? "text-neon" : dpp <= -2 ? "text-error" : "text-muted";
                  const predLeft = b.mean_predicted * 100;
                  const actLeft = b.actual_hit_rate * 100;
                  return (
                    <tr key={`${b.bin_lo}-${b.bin_hi}`} className="border-b border-border-muted">
                      <td className="px-2 py-3 text-primary">
                        {pct(b.bin_lo)}–{pct(b.bin_hi)}
                      </td>
                      <td className="px-2 py-3 tabular-nums text-right">{b.n}</td>
                      <td className="px-2 py-3 tabular-nums text-right text-secondary">{pct(b.mean_predicted)}</td>
                      <td className={`px-2 py-3 tabular-nums text-right ${cls}`}>
                        {pct(b.actual_hit_rate)}
                      </td>
                      <td className="px-2 py-3">
                        <div className="relative h-2 rounded-full bg-raised">
                          <div
                            className="absolute top-[-4px] h-4 w-[2px] bg-muted"
                            style={{ left: `${predLeft}%` }}
                          />
                          <div
                            className="absolute h-full rounded-full bg-neon"
                            style={{ left: 0, width: `${actLeft}%` }}
                          />
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* How the model works — short */}
      <section className="card space-y-4">
        <h2 className="headline-section text-2xl md:text-3xl">
          {lang === "vi" ? "Tại sao nó hoạt động" : "Why it works"}
        </h2>
        <div className="grid md:grid-cols-3 gap-4 text-sm">
          <div className="space-y-2">
            <p className="font-mono text-xs uppercase tracking-wide text-neon">
              1 · xG, {lang === "vi" ? "không phải tỉ số" : "not scores"}
            </p>
            <p className="text-secondary">
              {lang === "vi"
                ? "Sức mạnh đội bóng được ước lượng từ expected goals của từng trận gần đây — khử ngẫu nhiên, giữ lại chất lượng cú dứt điểm."
                : "Team strength is fit to recent match xG — noise-adjusted quality, not the 3-nil fluke last weekend."}
            </p>
          </div>
          <div className="space-y-2">
            <p className="font-mono text-xs uppercase tracking-wide text-neon">
              2 · Ensemble
            </p>
            <p className="text-secondary">
              {lang === "vi"
                ? "Poisson + Dixon-Coles kết hợp với Elo theo thời gian và XGBoost trên 21 feature. Blend 85/15 sau hiệu chỉnh nhiệt độ."
                : "Poisson + Dixon-Coles blended with time-aware Elo and an XGBoost classifier on 21 features. 85/15 final blend after temperature scaling."}
            </p>
          </div>
          <div className="space-y-2">
            <p className="font-mono text-xs uppercase tracking-wide text-neon">
              3 · {lang === "vi" ? "Không sửa được" : "Tamper-proof"}
            </p>
            <p className="text-secondary">
              {lang === "vi"
                ? "Mỗi dự đoán được SHA-256 hash trước kickoff và lưu ngay. Không thể sửa xác suất sau khi biết kết quả."
                : "Every prediction is SHA-256 hashed before kickoff and stored. No silent edits after the fact."}
            </p>
          </div>
        </div>
        <div>
          <Link
            href="/docs/model"
            className="font-mono text-xs uppercase tracking-wide text-secondary hover:text-neon transition-colors"
          >
            {lang === "vi" ? "Chi tiết toán học →" : "Full math writeup →"}
          </Link>
        </div>
      </section>

      {/* Commitment verification how-to */}
      <section className="card space-y-4">
        <h2 className="headline-section text-2xl md:text-3xl">
          {lang === "vi" ? "Cách tự kiểm tra" : "How to verify a prediction yourself"}
        </h2>
        <ol className="space-y-3 text-secondary text-sm list-decimal pl-5">
          <li>
            {lang === "vi"
              ? "Mở trang một trận trước giờ bóng lăn. Xem huy hiệu cam kết SHA-256 (commitment hash)."
              : "Open any match page before kickoff. Note the SHA-256 commitment hash shown in the commitment badge."}
          </li>
          <li>
            {lang === "vi"
              ? "Ghi lại xác suất H/D/A và top scoreline cùng với hash đó."
              : "Record the H/D/A probabilities and top scoreline alongside that hash."}
          </li>
          <li>
            {lang === "vi"
              ? "Sau khi hết trận, quay lại. Nếu xác suất đã thay đổi, hash sẽ không còn khớp — và bạn biết model đã bị sửa."
              : "After full-time, come back. If probabilities were edited post-hoc, the recomputed hash won't match the one you saved — you'll know."}
          </li>
          <li>
            {lang === "vi"
              ? "Công thức canonical đang được công bố trong repo GitHub: sorted-keys JSON, probs làm tròn 6 số thập phân, SHA-256."
              : "The canonical encoding is public in the GitHub repo: sorted-keys JSON, probs rounded to 6 dp, then SHA-256."}
          </li>
        </ol>
        <p className="font-mono text-[11px] text-muted">
          {lang === "vi"
            ? "Đây là điểm cốt lõi: lời khoác lác dễ, nhưng lời cam kết có chữ ký toán học thì không."
            : "This is the point: anyone can brag, but cryptographic pre-commitment makes bragging falsifiable."}
        </p>
      </section>

      {/* CTA */}
      <section className="card space-y-4 text-center">
        <h2 className="headline-section text-2xl md:text-3xl">
          {lang === "vi" ? "Sẵn sàng xem dự đoán tiếp theo?" : "Ready to see the next pick?"}
        </h2>
        <div className="flex items-center justify-center gap-3 flex-wrap">
          <Link
            href="/"
            className="inline-flex items-center rounded-full bg-neon px-5 py-2 font-mono text-sm uppercase tracking-wide text-on-neon font-semibold hover:opacity-90 transition-opacity"
          >
            {lang === "vi" ? "Trận sắp tới" : "Upcoming matches"}
          </Link>
          <Link
            href="/last-weekend"
            className="inline-flex items-center rounded-full border border-border px-5 py-2 font-mono text-sm uppercase tracking-wide text-secondary hover:border-neon hover:text-neon transition-colors"
          >
            {lang === "vi" ? "Hit/miss gần đây" : "Recent hits/misses"}
          </Link>
        </div>
      </section>
    </main>
  );
}
