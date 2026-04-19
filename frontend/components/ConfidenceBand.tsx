"use client";

import { useEffect, useState } from "react";

import { getCI, type PredictionCI } from "@/lib/api";
import type { Lang } from "@/lib/i18n";

// Renders the bootstrap CI band under each outcome percentage. Fetches
// client-side so the match detail page can paint instantly — the band
// fades in once the 1.8-s (cold) bootstrap resolves; cached hits feel
// instantaneous anyway.
export default function ConfidenceBand({
  matchId,
  lang,
}: {
  matchId: number;
  lang: Lang;
}) {
  const [ci, setCi] = useState<PredictionCI | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getCI(matchId)
      .then((v) => {
        if (!cancelled) {
          setCi(v);
          setLoaded(true);
        }
      })
      .catch(() => setLoaded(true));
    return () => {
      cancelled = true;
    };
  }, [matchId]);

  if (!loaded) {
    // Reserve vertical space so content above doesn't reflow when band lands.
    return <div className="h-[18px]" aria-hidden />;
  }
  if (!ci) return null;

  const pct = (x: number) => `${Math.round(x * 100)}%`;
  const cells = [
    [ci.p_home_low, ci.p_home_high],
    [ci.p_draw_low, ci.p_draw_high],
    [ci.p_away_low, ci.p_away_high],
  ] as const;

  return (
    <div className="animate-in fade-in grid grid-cols-3 gap-4 text-center">
      {cells.map(([lo, hi], i) => (
        <p key={i} className="font-mono text-[10px] text-muted">
          {pct(lo)}–{pct(hi)}
        </p>
      ))}
      <p className="col-span-3 font-mono text-[11px] text-muted text-center">
        {lang === "vi" ? "Khoảng tin cậy 68%" : "68% confidence range"} · bootstrap n={ci.n_samples}
      </p>
    </div>
  );
}
