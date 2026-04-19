import Link from "next/link";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type AdminStatus = {
  quota: {
    used_today: number | null;
    limit_day: number | null;
    fetched_at: string;
  } | null;
  ingest: {
    last_prediction: string | null;
    last_odds_capture: string | null;
    last_live_update: string | null;
    last_player_stats: string | null;
  };
  leagues: Array<{
    slug: string;
    short: string;
    emoji: string;
    matches_total: number;
    matches_final: number;
    matches_scheduled: number;
    matches_live: number;
    predictions_total: number;
  }>;
  recent_errors_15m: number;
  last_errors: Array<{ ts: number; path: string; error: string }>;
};

async function fetchStatus(): Promise<AdminStatus | null> {
  try {
    const res = await fetch(`${BASE}/api/admin/status`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

function fmtAge(iso: string | null): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  const diff = Date.now() - then;
  if (!Number.isFinite(diff) || diff < 0) return new Date(iso).toISOString();
  const m = Math.floor(diff / 60_000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ${m % 60}m ago`;
  const d = Math.floor(h / 24);
  return `${d}d ${h % 24}h ago`;
}

export default async function AdminPage() {
  const s = await fetchStatus();

  if (!s) {
    return (
      <main className="mx-auto max-w-5xl px-6 py-12">
        <div className="card text-error">Failed to load admin status.</div>
      </main>
    );
  }

  const q = s.quota;
  const quotaPct = q?.limit_day && q.used_today !== null
    ? (q.used_today / q.limit_day) * 100
    : null;

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">← Back</Link>

      <header className="space-y-2">
        <h1 className="headline-section">Admin · status</h1>
        <p className="text-secondary text-sm">
          Live operational snapshot. No auth — don&apos;t share the URL.
        </p>
      </header>

      {/* API-Football quota */}
      <section className="card space-y-3">
        <h2 className="label">API-Football quota</h2>
        {q && q.limit_day !== null ? (
          <>
            <div className="flex items-baseline justify-between">
              <p className="stat text-neon">{q.used_today} <span className="text-muted text-base font-mono">/ {q.limit_day}</span></p>
              <p className="font-mono text-xs text-muted">fetched {fmtAge(q.fetched_at)}</p>
            </div>
            <div className="h-2 rounded-full bg-high overflow-hidden">
              <div
                className="h-full bg-neon transition-all"
                style={{ width: `${Math.min(100, quotaPct ?? 0)}%` }}
              />
            </div>
          </>
        ) : (
          <p className="text-muted text-sm">Quota unavailable (API_FOOTBALL_KEY not set or endpoint unreachable).</p>
        )}
      </section>

      {/* Ingest freshness */}
      <section className="card space-y-3">
        <h2 className="label">Ingest freshness</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono text-sm">
          <div>
            <p className="text-xs text-muted">Last prediction</p>
            <p>{fmtAge(s.ingest.last_prediction)}</p>
          </div>
          <div>
            <p className="text-xs text-muted">Last odds capture</p>
            <p>{fmtAge(s.ingest.last_odds_capture)}</p>
          </div>
          <div>
            <p className="text-xs text-muted">Last live update</p>
            <p>{fmtAge(s.ingest.last_live_update)}</p>
          </div>
          <div>
            <p className="text-xs text-muted">Last player stats</p>
            <p>{fmtAge(s.ingest.last_player_stats)}</p>
          </div>
        </div>
      </section>

      {/* Recent errors */}
      <section className="card space-y-3">
        <h2 className="label">Recent errors (15 min)</h2>
        <p className={`stat ${s.recent_errors_15m > 0 ? "text-error" : "text-neon"}`}>
          {s.recent_errors_15m}
        </p>
        {s.last_errors.length > 0 && (
          <ul className="space-y-1 font-mono text-xs">
            {s.last_errors.slice(-5).reverse().map((e, i) => (
              <li key={i} className="flex justify-between gap-2 text-muted">
                <span className="text-error">{e.error}</span>
                <span className="truncate">{e.path}</span>
                <span>{new Date(e.ts * 1000).toLocaleTimeString()}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Per-league counts */}
      <section className="card p-0 overflow-x-auto">
        <table className="w-full font-mono text-sm">
          <thead className="text-muted">
            <tr className="border-b border-border">
              {["League", "Total", "Final", "Scheduled", "Live", "Predictions"].map((h) => (
                <th key={h} className="label px-3 py-3 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {s.leagues.map((lg) => (
              <tr key={lg.slug} className="border-b border-border-muted hover:bg-high">
                <td className="px-3 py-2">{lg.emoji} {lg.short}</td>
                <td className="px-3 py-2 tabular-nums">{lg.matches_total}</td>
                <td className="px-3 py-2 tabular-nums text-secondary">{lg.matches_final}</td>
                <td className="px-3 py-2 tabular-nums text-muted">{lg.matches_scheduled}</td>
                <td className={`px-3 py-2 tabular-nums ${lg.matches_live > 0 ? "text-neon" : "text-muted"}`}>
                  {lg.matches_live}
                </td>
                <td className="px-3 py-2 tabular-nums">{lg.predictions_total}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
