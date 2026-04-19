"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getMatch } from "@/lib/api";
import { type BetslipEntry, readSlip, removePick } from "@/lib/betslip";
import type { MatchOut } from "@/lib/types";

type Hydrated = BetslipEntry & {
  match: MatchOut | null;
};

type Settled = "win" | "loss" | "pending";

function settle(entry: Hydrated): { status: Settled; pnl: number } {
  const m = entry.match;
  if (!m || m.status !== "final" || m.home_goals == null || m.away_goals == null) {
    return { status: "pending", pnl: 0 };
  }
  const actual = m.home_goals > m.away_goals ? "H"
    : m.home_goals < m.away_goals ? "A"
    : "D";
  if (actual === entry.outcome) {
    return { status: "win", pnl: entry.stake * (entry.odds - 1) };
  }
  return { status: "loss", pnl: -entry.stake };
}

export default function BetslipPage() {
  const [entries, setEntries] = useState<BetslipEntry[]>([]);
  const [hydrated, setHydrated] = useState<Hydrated[]>([]);

  useEffect(() => {
    function load() { setEntries(readSlip()); }
    load();
    window.addEventListener("betslip-change", load);
    window.addEventListener("storage", load);
    return () => {
      window.removeEventListener("betslip-change", load);
      window.removeEventListener("storage", load);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    Promise.all(
      entries.map(async (e) => {
        try {
          const m = await getMatch(e.match_id);
          return { ...e, match: m };
        } catch {
          return { ...e, match: null };
        }
      }),
    ).then((r) => {
      if (!cancelled) setHydrated(r);
    });
    return () => { cancelled = true; };
  }, [entries]);

  if (entries.length === 0) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-12 space-y-6">
        <Link href="/" className="btn-ghost text-sm">← Back</Link>
        <h1 className="headline-section">Your betslip</h1>
        <div className="card text-muted">
          Empty. Add picks from the odds panel on any match page.
        </div>
      </main>
    );
  }

  const settled = hydrated.map((e) => ({ entry: e, ...settle(e) }));
  const totalPnl = settled.reduce((s, x) => s + x.pnl, 0);
  const totalStake = settled.reduce((s, x) => s + x.entry.stake, 0);
  const decided = settled.filter((x) => x.status !== "pending");
  const wins = decided.filter((x) => x.status === "win").length;

  return (
    <main className="mx-auto max-w-4xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">← Back</Link>

      <header className="space-y-2">
        <h1 className="headline-section">Your betslip</h1>
        <p className="text-secondary">
          Saved locally in your browser · {entries.length} pick{entries.length === 1 ? "" : "s"}.
        </p>
      </header>

      <section className="card grid grid-cols-2 md:grid-cols-4 gap-6">
        <div>
          <p className="label">Picks</p>
          <p className="stat">{entries.length}</p>
        </div>
        <div>
          <p className="label">Settled</p>
          <p className="stat">{decided.length}</p>
        </div>
        <div>
          <p className="label">Hit rate</p>
          <p className="stat">{decided.length ? `${Math.round((wins / decided.length) * 100)}%` : "—"}</p>
        </div>
        <div>
          <p className="label">P&amp;L</p>
          <p className={`stat ${totalPnl > 0 ? "text-neon" : totalPnl < 0 ? "text-error" : ""}`}>
            {totalPnl >= 0 ? "+" : ""}{totalPnl.toFixed(2)}u
          </p>
        </div>
      </section>

      <section className="card p-0 overflow-x-auto">
        <table className="w-full font-mono text-sm">
          <thead className="text-muted">
            <tr className="border-b border-border">
              {["Match", "Pick", "Odds", "Status", "P&L", ""].map((h) => (
                <th key={h} className="label px-3 py-3 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {settled.map(({ entry, status, pnl }) => {
              const m = entry.match;
              const label = m ? `${m.home.short_name} vs ${m.away.short_name}` : `#${entry.match_id}`;
              const sideLabel = entry.outcome === "H"
                ? m ? m.home.short_name : "Home"
                : entry.outcome === "A"
                ? m ? m.away.short_name : "Away"
                : "Draw";
              const statusColor =
                status === "win" ? "text-neon" : status === "loss" ? "text-error" : "text-muted";
              return (
                <tr key={`${entry.match_id}-${entry.outcome}`} className="border-b border-border-muted">
                  <td className="px-3 py-2">
                    {m ? (
                      <Link href={`/match/${m.id}`} className="hover:text-neon">
                        {label}
                      </Link>
                    ) : label}
                  </td>
                  <td className="px-3 py-2">{sideLabel}</td>
                  <td className="px-3 py-2 tabular-nums">{entry.odds.toFixed(2)}</td>
                  <td className={`px-3 py-2 uppercase ${statusColor}`}>{status}</td>
                  <td className={`px-3 py-2 tabular-nums ${statusColor}`}>
                    {status === "pending" ? "—" : (pnl >= 0 ? "+" : "") + pnl.toFixed(2) + "u"}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => removePick(entry.match_id, entry.outcome)}
                      className="text-muted hover:text-error"
                      aria-label="Remove"
                    >
                      ×
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <p className="text-[11px] text-muted">
        Stake fixed at 1 unit per pick. Data stays in this browser — clearing site storage wipes the slip.
      </p>
    </main>
  );
}
