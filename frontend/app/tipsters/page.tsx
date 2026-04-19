import Link from "next/link";

import { getLang, tFor } from "@/lib/i18n-server";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type LeaderRow = {
  rank: number;
  handle: string;
  picks: number;
  settled: number;
  correct: number;
  accuracy: number;
  mean_log_loss: number;
};

async function fetchLB(days: number): Promise<LeaderRow[]> {
  const res = await fetch(`${BASE}/api/tipsters/leaderboard?days=${days}&min_picks=3`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export default async function TipstersPage({
  searchParams,
}: {
  searchParams: Promise<{ days?: string }>;
}) {
  const sp = await searchParams;
  const days = Number(sp.days ?? "30");
  const lang = await getLang();
  const t = tFor(lang);
  const rows = await fetchLB(days);

  const WINDOWS = [7, 30, 90] as const;

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>

      <header className="space-y-2">
        <h1 className="headline-section">
          {lang === "vi" ? "Bảng xếp hạng tipster" : "Tipster leaderboard"}
        </h1>
        <p className="text-secondary max-w-2xl">
          {lang === "vi"
            ? "Rank theo log-loss (thấp = tốt). Submit pick mỗi trận từ trang match detail để leo lên bảng."
            : "Ranked by log-loss (lower = better). Submit a pick on any match detail page to join."}
        </p>
      </header>

      <nav className="flex gap-2">
        {WINDOWS.map((d) => (
          <Link
            key={d}
            href={`/tipsters?days=${d}`}
            className={
              "rounded-full px-3 py-1 font-mono text-xs uppercase tracking-wide border " +
              (days === d
                ? "border-neon bg-neon text-on-neon"
                : "border-border text-secondary hover:border-neon hover:text-neon")
            }
          >
            last {d}d
          </Link>
        ))}
      </nav>

      {rows.length === 0 ? (
        <div className="card text-muted">
          {lang === "vi" ? "Chưa có ai submit pick đủ ngưỡng 3 trận." : "No tipsters with ≥3 settled picks yet."}
        </div>
      ) : (
        <div className="card p-0 overflow-x-auto">
          <table className="w-full font-mono text-sm">
            <thead className="text-muted">
              <tr className="border-b border-border">
                {["#", "Tipster", "Picks", "Acc", "Log-loss"].map((h) => (
                  <th key={h} className="label px-3 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.handle} className="border-b border-border-muted">
                  <td className="px-3 py-2 text-muted tabular-nums">{r.rank}</td>
                  <td className="px-3 py-2 text-primary">{r.handle}</td>
                  <td className="px-3 py-2 tabular-nums">{r.settled}</td>
                  <td className="px-3 py-2 tabular-nums text-neon">
                    {Math.round(r.accuracy * 100)}%
                  </td>
                  <td className="px-3 py-2 tabular-nums">{r.mean_log_loss.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-[11px] text-muted">
        Scoring: confidence is treated as your probability on the chosen outcome,
        with the remainder split evenly over the other two. Uniform baseline = 1.099.
      </p>
    </main>
  );
}
