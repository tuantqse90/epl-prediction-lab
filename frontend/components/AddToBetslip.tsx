"use client";

import { useEffect, useState } from "react";

import { hasPick, togglePick } from "@/lib/betslip";

export default function AddToBetslip({
  matchId,
  outcome,
  odds,
  label,
}: {
  matchId: number;
  outcome: "H" | "D" | "A";
  odds: number;
  label?: string;
}) {
  const [on, setOn] = useState(false);

  useEffect(() => {
    setOn(hasPick(matchId, outcome));
    function sync() { setOn(hasPick(matchId, outcome)); }
    window.addEventListener("betslip-change", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("betslip-change", sync);
      window.removeEventListener("storage", sync);
    };
  }, [matchId, outcome]);

  return (
    <button
      type="button"
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        setOn(togglePick({ match_id: matchId, outcome, odds }));
      }}
      className={
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-wide transition-colors " +
        (on
          ? "bg-neon text-on-neon"
          : "border border-border text-secondary hover:border-neon hover:text-neon")
      }
      aria-pressed={on}
      title={on ? "Remove from betslip" : "Add to betslip"}
    >
      {on ? "✓ in slip" : `+ ${label ?? "slip"}`}
    </button>
  );
}
