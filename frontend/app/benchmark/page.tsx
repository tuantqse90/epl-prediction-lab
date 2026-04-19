import Link from "next/link";

import { getLang, getLeagueSlug, leagueForApi, tFor } from "@/lib/i18n-server";
import { getLeague } from "@/lib/leagues";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type Accuracy = {
  season: string;
  scored: number;
  correct: number;
  accuracy: number;
  baseline_home_accuracy: number;
  mean_log_loss: number;
  uniform_log_loss: number;
};

type RecentWindow = {
  days: number;
  scored: number;
  correct: number;
  accuracy: number;
  mean_log_loss: number;
};

async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

function pct(x: number) {
  return `${Math.round(x * 100)}%`;
}

function Tile({
  label,
  accuracy,
  matches,
  accent = false,
}: {
  label: string;
  accuracy: number | null;
  matches: number | null;
  accent?: boolean;
}) {
  return (
    <div className="card">
      <p className="label">{label}</p>
      <p className={`stat ${accent ? "text-neon" : ""}`}>
        {accuracy != null ? pct(accuracy) : "—"}
      </p>
      <p className="text-xs text-muted tabular-nums">
        {matches != null ? `${matches} matches` : "pending"}
      </p>
    </div>
  );
}

export default async function BenchmarkPage() {
  const lang = await getLang();
  const t = tFor(lang);
  const league = await getLeagueSlug();
  const info = getLeague(league);
  const leagueParam = leagueForApi(league);
  const qs = leagueParam ? `&league=${leagueParam}` : "";

  const [day7, day30, day90, season] = await Promise.all([
    fetchJson<RecentWindow>(`/api/stats/recent?days=7${qs}`),
    fetchJson<RecentWindow>(`/api/stats/recent?days=30${qs}`),
    fetchJson<RecentWindow>(`/api/stats/recent?days=90${qs}`),
    fetchJson<Accuracy>(`/api/stats/accuracy?season=2025-26${leagueParam ? `&league=${leagueParam}` : ""}`),
  ]);

  const uniform = 1 / 3;
  const leagueLabel = lang === "vi" ? info.name_vi : info.name_en;

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>

      <header className="space-y-2">
        <p className="font-mono text-xs text-muted">{info.emoji} {leagueLabel}</p>
        <h1 className="headline-section">
          {lang === "vi" ? "Mô hình so với baseline" : "Model vs baseline"}
        </h1>
        <p className="text-secondary max-w-2xl">
          {lang === "vi"
            ? "Model phải vượt baseline 'luôn chọn chủ nhà' và 'đoán đều' (33.3%) mới đáng tin. Bảng dưới so sánh rolling 7/30/90 ngày + toàn mùa."
            : "To be useful, the model must beat both always-pick-home and uniform-random (33.3%). Rolling 7/30/90-day comparisons below."}
        </p>
      </header>

      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Tile label="Last 7d" accuracy={day7?.accuracy ?? null} matches={day7?.scored ?? null} accent />
        <Tile label="Last 30d" accuracy={day30?.accuracy ?? null} matches={day30?.scored ?? null} accent />
        <Tile label="Last 90d" accuracy={day90?.accuracy ?? null} matches={day90?.scored ?? null} />
        <Tile label="Full season" accuracy={season?.accuracy ?? null} matches={season?.scored ?? null} />
      </section>

      {season && season.scored > 0 && (
        <section className="card space-y-4">
          <h2 className="label">Season benchmark</h2>
          <div className="space-y-3 font-mono text-sm">
            <BenchmarkRow
              label="Model"
              value={season.accuracy}
              target={season.accuracy}
              max={0.7}
              color="bg-neon"
            />
            <BenchmarkRow
              label="Always Home"
              value={season.baseline_home_accuracy}
              target={season.accuracy}
              max={0.7}
              color="bg-secondary"
            />
            <BenchmarkRow
              label="Uniform (33%)"
              value={uniform}
              target={season.accuracy}
              max={0.7}
              color="bg-muted"
            />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2 border-t border-border">
            <div>
              <p className="label">Log-loss (model)</p>
              <p className="stat text-neon">{season.mean_log_loss.toFixed(3)}</p>
            </div>
            <div>
              <p className="label">Log-loss (uniform)</p>
              <p className="stat">{season.uniform_log_loss.toFixed(3)}</p>
            </div>
            <div>
              <p className="label">Δ vs uniform</p>
              <p className={`stat ${season.mean_log_loss < season.uniform_log_loss ? "text-neon" : "text-error"}`}>
                {(season.mean_log_loss - season.uniform_log_loss).toFixed(3)}
              </p>
            </div>
            <div>
              <p className="label">Beat home baseline</p>
              <p className={`stat ${season.accuracy > season.baseline_home_accuracy ? "text-neon" : "text-error"}`}>
                {season.accuracy > season.baseline_home_accuracy ? "✓" : "✗"}
              </p>
            </div>
          </div>
        </section>
      )}

      <section className="card text-[11px] text-muted">
        Log-loss scores raw probabilities, not just the argmax. Lower is better.
        Uniform-random = 1.099. A model only matters if its log-loss sits below
        that and its accuracy sits above baseline-home.
      </section>
    </main>
  );
}

function BenchmarkRow({
  label, value, max, color,
}: {
  label: string;
  value: number;
  target: number;
  max: number;
  color: string;
}) {
  const width = Math.min(100, (value / max) * 100);
  return (
    <div className="flex items-center gap-3">
      <span className="w-28 shrink-0 text-secondary uppercase text-xs tracking-wide">{label}</span>
      <div className="flex-1 h-6 rounded bg-high overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${width}%` }} />
      </div>
      <span className="w-12 text-right tabular-nums text-primary">{pct(value)}</span>
    </div>
  );
}
