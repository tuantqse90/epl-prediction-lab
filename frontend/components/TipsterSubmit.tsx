"use client";

import { useEffect, useState } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";
const HANDLE_KEY = "epl-lab:tipster-handle";

export default function TipsterSubmit({
  matchId,
  homeShort,
  awayShort,
}: {
  matchId: number;
  homeShort: string;
  awayShort: string;
}) {
  const [handle, setHandle] = useState("");
  const [pick, setPick] = useState<"H" | "D" | "A" | null>(null);
  const [confidence, setConfidence] = useState(0.5);
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const stored = window.localStorage.getItem(HANDLE_KEY);
    if (stored) setHandle(stored);
  }, []);

  async function submit() {
    setError(null);
    const h = handle.trim();
    if (!/^[A-Za-z0-9_\-.]{2,24}$/.test(h)) {
      setError("Handle must be 2-24 chars (alnum/._-)");
      return;
    }
    if (!pick) {
      setError("Pick a side");
      return;
    }
    try {
      const res = await fetch(`${BASE}/api/tipsters/picks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ handle: h, match_id: matchId, pick, confidence }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setError(body?.detail ?? `submit failed (${res.status})`);
        return;
      }
      window.localStorage.setItem(HANDLE_KEY, h);
      setSubmitted(`@${h} — ${pick} @ ${Math.round(confidence * 100)}%`);
    } catch {
      setError("Network error");
    }
  }

  if (submitted) {
    return (
      <section className="card space-y-2">
        <p className="label">Your pick submitted</p>
        <p className="font-mono text-sm text-neon">{submitted}</p>
        <a href="/tipsters" className="btn-ghost text-xs">View leaderboard →</a>
      </section>
    );
  }

  return (
    <section className="card space-y-3">
      <div className="flex items-baseline justify-between">
        <h2 className="label">Submit your pick</h2>
        <a href="/tipsters" className="font-mono text-xs text-muted hover:text-neon">leaderboard →</a>
      </div>

      <input
        type="text"
        value={handle}
        onChange={(e) => setHandle(e.target.value)}
        placeholder="your_handle"
        className="w-full rounded border border-border bg-raised px-3 py-2 font-mono text-sm outline-none focus:border-neon"
        maxLength={24}
      />

      <div className="grid grid-cols-3 gap-2">
        {(["H", "D", "A"] as const).map((p) => {
          const label = p === "H" ? homeShort : p === "A" ? awayShort : "Draw";
          return (
            <button
              key={p}
              type="button"
              onClick={() => setPick(p)}
              className={
                "rounded py-2 font-mono text-sm uppercase " +
                (pick === p
                  ? "bg-neon text-on-neon"
                  : "border border-border text-secondary hover:border-neon hover:text-neon")
              }
            >
              {label}
            </button>
          );
        })}
      </div>

      <label className="flex items-center gap-2 font-mono text-xs">
        <span className="text-muted w-20 shrink-0">Confidence</span>
        <input
          type="range"
          min={0.35}
          max={0.95}
          step={0.05}
          value={confidence}
          onChange={(e) => setConfidence(Number(e.target.value))}
          className="flex-1 accent-[#E0FF32]"
        />
        <span className="w-10 text-right tabular-nums text-neon">{Math.round(confidence * 100)}%</span>
      </label>

      {error && <p className="font-mono text-xs text-error">{error}</p>}

      <button
        type="button"
        onClick={submit}
        disabled={!pick}
        className="btn-primary disabled:opacity-50"
      >
        Submit
      </button>
    </section>
  );
}
