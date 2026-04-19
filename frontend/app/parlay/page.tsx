"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getMatch } from "@/lib/api";
import { readSlip, removePick, type BetslipEntry } from "@/lib/betslip";
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

  if (entries.length === 0) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12 space-y-6">
        <Link href="/" className="btn-ghost text-sm">← Back</Link>
        <h1 className="headline-section">Parlay calculator</h1>
        <div className="card text-muted">
          Add picks from odds panels to build a parlay.
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
      <Link href="/" className="btn-ghost text-sm">← Back</Link>
      <header className="space-y-2">
        <h1 className="headline-section">Parlay calculator</h1>
        <p className="text-secondary">
          Combines your betslip legs independently. Parlays from multi-market on the
          <em> same </em> match are correlated — model this externally.
        </p>
      </header>

      <section className="card grid grid-cols-2 md:grid-cols-4 gap-6">
        <div>
          <p className="label">Legs</p>
          <p className="stat">{legs.length}</p>
        </div>
        <div>
          <p className="label">Model P(all)</p>
          <p className="stat text-neon">{combinedProb != null ? `${(combinedProb * 100).toFixed(1)}%` : "—"}</p>
        </div>
        <div>
          <p className="label">Combined odds</p>
          <p className="stat">{combinedOdds.toFixed(2)}</p>
        </div>
        <div>
          <p className="label">Expected value</p>
          <p className={`stat ${expectedValue != null && expectedValue > 0 ? "text-neon" : expectedValue != null && expectedValue < 0 ? "text-error" : ""}`}>
            {expectedValue != null ? `${expectedValue >= 0 ? "+" : ""}${(expectedValue * 100).toFixed(1)}%` : "—"}
          </p>
        </div>
      </section>

      {combinedProb != null && expectedValue! > 0 && (
        <section className="card">
          <p className="label">Kelly stake (fractional, capped 25%)</p>
          <p className="stat text-neon">{(combinedStake * 100).toFixed(1)}%</p>
          <p className="text-[11px] text-muted">
            Share of bankroll to wager on this parlay. Full Kelly is brutal on estimate error
            — fractional cap protects you.
          </p>
        </section>
      )}

      <section className="card p-0 overflow-x-auto">
        <table className="w-full font-mono text-sm">
          <thead className="text-muted">
            <tr className="border-b border-border">
              {["Match", "Pick", "Odds", "Model P", ""].map((h) => (
                <th key={h} className="label px-3 py-3 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {legs.map((l) => {
              const m = l.match;
              const mp = l.model_p;
              const label = m ? `${m.home.short_name} vs ${m.away.short_name}` : `#${l.match_id}`;
              const sideLabel = l.outcome === "H"
                ? m?.home.short_name ?? "Home"
                : l.outcome === "A"
                ? m?.away.short_name ?? "Away"
                : "Draw";
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
                      aria-label="Remove"
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
