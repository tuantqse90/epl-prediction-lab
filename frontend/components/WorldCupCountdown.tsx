"use client";

import { useEffect, useState } from "react";

import type { Lang } from "@/lib/i18n";

// FIFA World Cup 2026 — group stage opener, Mexico City, 11 Jun 2026 20:00 UTC.
const KICKOFF_UTC = Date.UTC(2026, 5, 11, 20, 0, 0);

type Remaining = {
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
  totalMs: number;
};

function diff(now: number): Remaining {
  const totalMs = Math.max(0, KICKOFF_UTC - now);
  const seconds = Math.floor(totalMs / 1000) % 60;
  const minutes = Math.floor(totalMs / 60_000) % 60;
  const hours = Math.floor(totalMs / 3_600_000) % 24;
  const days = Math.floor(totalMs / 86_400_000);
  return { days, hours, minutes, seconds, totalMs };
}

const pad = (n: number, w = 2) => String(n).padStart(w, "0");

export default function WorldCupCountdown({ lang }: { lang: Lang }) {
  const [r, setR] = useState<Remaining>(() => diff(Date.now()));
  const [cursor, setCursor] = useState(true);

  useEffect(() => {
    const tick = () => setR(diff(Date.now()));
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    const id = window.setInterval(() => setCursor((c) => !c), 550);
    return () => window.clearInterval(id);
  }, []);

  // Progress bar: measure from tournament announcement (~1 year before kickoff)
  // so the bar fills gradually. Pure aesthetic, not load-bearing.
  const windowMs = 365 * 86_400_000;
  const filled = Math.max(0, Math.min(1, 1 - r.totalMs / windowMs));
  const bars = 24;
  const filledCount = Math.round(filled * bars);
  const bar = "█".repeat(filledCount) + "░".repeat(Math.max(0, bars - filledCount));

  const label =
    lang === "vi" ? "World Cup 2026 · Mexico City"
    : lang === "th" ? "ฟุตบอลโลก 2026 · Mexico City"
    : lang === "zh" ? "2026 世界杯 · 墨西哥城"
    : lang === "ko" ? "2026 월드컵 · 멕시코시티"
    : "World Cup 2026 · Mexico City";

  const kickoff =
    lang === "vi" ? "khai mạc" : "kickoff";

  return (
    <section
      aria-label="World Cup 2026 countdown"
      className="relative overflow-hidden rounded-xl border border-neon/30 bg-black/60 font-mono text-xs md:text-sm"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(closest-side at 0% 50%, rgba(224,255,50,0.18), transparent 55%)",
        }}
      />
      <div className="relative flex flex-wrap items-center gap-3 md:gap-6 p-3 md:p-4">
        <div className="flex items-center gap-2">
          <span className="text-neon">▶</span>
          <span className="text-neon uppercase tracking-[0.18em] font-semibold">
            {label}
          </span>
        </div>

        <span className="hidden md:inline text-muted">·</span>

        <div className="flex items-baseline gap-1 tabular-nums" suppressHydrationWarning>
          <span className="text-neon text-lg md:text-2xl font-semibold">{r.days}</span>
          <span className="text-muted uppercase text-[10px] tracking-wider">d</span>
          <span className="text-neon text-lg md:text-2xl font-semibold ml-2">
            {pad(r.hours)}
          </span>
          <span className="text-muted uppercase text-[10px] tracking-wider">h</span>
          <span className="text-neon text-lg md:text-2xl font-semibold ml-2">
            {pad(r.minutes)}
          </span>
          <span className="text-muted uppercase text-[10px] tracking-wider">m</span>
          <span className="text-neon text-lg md:text-2xl font-semibold ml-2">
            {pad(r.seconds)}
          </span>
          <span className="text-muted uppercase text-[10px] tracking-wider">s</span>
          <span className={`ml-1 text-neon ${cursor ? "opacity-100" : "opacity-0"}`}>_</span>
        </div>

        <span className="hidden md:inline text-muted">·</span>

        <span className="text-muted uppercase tracking-wide">
          {lang === "vi" ? "đến" : "until"} {kickoff}
        </span>

        <span
          className="hidden lg:inline-flex items-center gap-2 ml-auto"
          suppressHydrationWarning
        >
          <span className="text-muted">[</span>
          <span className="text-neon">{bar}</span>
          <span className="text-muted">]</span>
          <span className="text-muted tabular-nums">{Math.round(filled * 100)}%</span>
        </span>
      </div>
    </section>
  );
}
