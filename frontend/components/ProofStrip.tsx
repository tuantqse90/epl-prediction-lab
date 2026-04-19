import type { Lang } from "@/lib/i18n";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

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

type RecentHit = { hit: boolean };

async function fetchComparison(league?: string, days = 30): Promise<Comparison | null> {
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

async function fetchRecentHits(league?: string, days = 30): Promise<RecentHit[]> {
  const qs = new URLSearchParams({ days: String(days) });
  if (league) qs.set("league", league);
  try {
    const res = await fetch(`${BASE}/api/stats/recent?${qs}`, { cache: "no-store" });
    if (!res.ok) return [];
    const body = await res.json();
    return (body.matches ?? []).slice(0, 10).map((m: { hit: boolean }) => ({ hit: m.hit }));
  } catch {
    return [];
  }
}

function pct(x: number) {
  return `${(x * 100).toFixed(1)}%`;
}

// Four-row bar chart showing model beats naive baselines and matches the
// market. Home page hero — first thing the user sees after the headline.
export default async function ProofStrip({ league, lang }: { league?: string; lang: Lang }) {
  const [data, recent] = await Promise.all([
    fetchComparison(league, 30),
    fetchRecentHits(league, 30),
  ]);
  if (!data || data.scored < 10) return null;

  const rows = [
    { key: "model", label: lang === "vi" ? "MODEL" : "Model", value: data.model_accuracy, accent: true },
    { key: "bk", label: lang === "vi" ? "NHÀ CÁI" : "Bookmakers", value: data.bookmaker_accuracy },
    { key: "home", label: lang === "vi" ? "LUÔN CHỦ NHÀ" : "Always Home", value: data.home_baseline_accuracy },
    { key: "rand", label: lang === "vi" ? "NGẪU NHIÊN" : "Random", value: data.uniform_baseline_accuracy },
  ];
  const max = Math.max(0.6, ...rows.map((r) => r.value));

  const footer = lang === "vi"
    ? `${data.days} ngày · ${data.scored} trận đã chấm điểm · log-loss ${data.model_log_loss.toFixed(3)}`
    : `Last ${data.days}d · ${data.scored} matches scored · log-loss ${data.model_log_loss.toFixed(3)}`;

  return (
    <section className="card space-y-3">
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <h2 className="label">
          {lang === "vi" ? "Mô hình vs baseline" : "Model vs baselines"}
        </h2>
        <span className="font-mono text-[11px] text-muted">{footer}</span>
      </div>
      {recent.length >= 5 && (
        <div className="flex items-center gap-3 text-xs font-mono">
          <span className="text-muted uppercase tracking-wide">
            {lang === "vi" ? "10 dự đoán gần nhất" : "Last 10 picks"}
          </span>
          <div className="flex items-center gap-1">
            {recent.map((r, i) => (
              <span
                key={i}
                className={`h-3 w-3 rounded-full ${r.hit ? "bg-neon" : "bg-error"}`}
                aria-label={r.hit ? "hit" : "miss"}
              />
            ))}
          </div>
          <span className="text-neon tabular-nums">
            {recent.filter((r) => r.hit).length}/{recent.length}
          </span>
        </div>
      )}

      <div className="space-y-2 font-mono text-xs">
        {rows.map((r) => {
          const width = Math.min(100, (r.value / max) * 100);
          return (
            <div key={r.key} className="flex items-center gap-3">
              <span className={`w-24 shrink-0 uppercase tracking-wide ${r.accent ? "text-neon" : "text-secondary"}`}>
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
    </section>
  );
}
