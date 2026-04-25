"use client";

import { useEffect, useState } from "react";

import type { Lang } from "@/lib/i18n";

// FIFA World Cup 2026 — group-stage opener, Mexico City, 11 Jun 2026 20:00 UTC.
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

type Copy = {
  tag: string;
  title: string;
  where: string;
  when: string;
  until: string;
  dLabel: string;
  hLabel: string;
  mLabel: string;
  sLabel: string;
  toKickoff: string;
  hosts: string;
};

function copy(lang: Lang): Copy {
  switch (lang) {
    case "vi":
      return {
        tag: "Sắp khai mạc",
        title: "World Cup 2026",
        where: "Mexico · United States · Canada",
        when: "11 Jun 2026 · 20:00 UTC",
        until: "còn",
        dLabel: "ngày",
        hLabel: "giờ",
        mLabel: "phút",
        sLabel: "giây",
        toKickoff: "đến tiếng còi khai mạc",
        hosts: "48 đội · 16 thành phố · 104 trận",
      };
    case "th":
      return {
        tag: "เริ่มเร็วๆ นี้",
        title: "ฟุตบอลโลก 2026",
        where: "Mexico · United States · Canada",
        when: "11 Jun 2026 · 20:00 UTC",
        until: "เหลืออีก",
        dLabel: "วัน",
        hLabel: "ชม.",
        mLabel: "นาที",
        sLabel: "วินาที",
        toKickoff: "จนถึงนัดเปิดสนาม",
        hosts: "48 ทีม · 16 เมือง · 104 นัด",
      };
    case "zh":
      return {
        tag: "即将开赛",
        title: "2026 世界杯",
        where: "墨西哥 · 美国 · 加拿大",
        when: "2026年6月11日 · 20:00 UTC",
        until: "还有",
        dLabel: "天",
        hLabel: "时",
        mLabel: "分",
        sLabel: "秒",
        toKickoff: "揭幕战",
        hosts: "48 队 · 16 城市 · 104 场",
      };
    case "ko":
      return {
        tag: "곧 개막",
        title: "2026 월드컵",
        where: "Mexico · United States · Canada",
        when: "2026년 6월 11일 · 20:00 UTC",
        until: "남은 시간",
        dLabel: "일",
        hLabel: "시",
        mLabel: "분",
        sLabel: "초",
        toKickoff: "개막전까지",
        hosts: "48개 팀 · 16개 도시 · 104 경기",
      };
    default:
      return {
        tag: "kicking off",
        title: "World Cup 2026",
        where: "Mexico · United States · Canada",
        when: "11 Jun 2026 · 20:00 UTC",
        until: "in",
        dLabel: "days",
        hLabel: "hours",
        mLabel: "min",
        sLabel: "sec",
        toKickoff: "to first whistle",
        hosts: "48 teams · 16 cities · 104 matches",
      };
  }
}

function Cell({
  value,
  label,
  live,
}: {
  value: string;
  label: string;
  live?: boolean;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-w-[72px] md:min-w-[120px]">
      <span
        className="font-display text-5xl md:text-7xl lg:text-8xl font-semibold tabular-nums leading-none text-neon drop-shadow-[0_0_16px_rgba(224,255,50,0.35)]"
        suppressHydrationWarning={live}
      >
        {value}
      </span>
      <span className="mt-1 md:mt-2 font-mono text-[10px] md:text-xs uppercase tracking-[0.22em] text-muted">
        {label}
      </span>
    </div>
  );
}

export default function WorldCupCountdown({ lang }: { lang: Lang }) {
  const [r, setR] = useState<Remaining>(() => diff(Date.now()));
  const [cursor, setCursor] = useState(true);
  const c = copy(lang);

  useEffect(() => {
    const tick = () => setR(diff(Date.now()));
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    const id = window.setInterval(() => setCursor((cur) => !cur), 550);
    return () => window.clearInterval(id);
  }, []);

  const windowMs = 365 * 86_400_000;
  const filled = Math.max(0, Math.min(1, 1 - r.totalMs / windowMs));
  const pctText = `${Math.round(filled * 100)}%`;

  return (
    <section
      aria-label="World Cup 2026 countdown"
      data-wc-banner
      className="relative overflow-hidden rounded-2xl border border-neon/40 bg-black"
    >
      {/* Layer 1: stadium-pitch stripes (alternating dark greens) evokes a
          turf backdrop without photo assets. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "repeating-linear-gradient(90deg, rgba(20,40,15,0.55) 0 60px, rgba(8,16,5,0.55) 60px 120px)",
        }}
      />
      {/* Layer 2: neon goal-net diagonal mesh. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.09]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(45deg, #E0FF32 0 1px, transparent 1px 14px), " +
            "repeating-linear-gradient(-45deg, #E0FF32 0 1px, transparent 1px 14px)",
        }}
      />
      {/* Layer 3: radial glow from top-right (stadium floodlight). */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(closest-side at 85% -10%, rgba(224,255,50,0.32), transparent 55%), " +
            "radial-gradient(closest-side at -5% 110%, rgba(224,255,50,0.15), transparent 55%)",
        }}
      />
      {/* Layer 4: inline trophy silhouette, right side desktop only. Abstract
          cup shape — two handles, body, stem, wide base — to feel tournament-y
          without copying the actual FIFA World Cup trophy. */}
      <svg
        aria-hidden
        viewBox="0 0 160 220"
        className="pointer-events-none absolute -right-4 top-1/2 -translate-y-1/2 h-[220px] w-[160px] opacity-25 hidden lg:block"
        fill="none"
        stroke="#E0FF32"
        strokeWidth="2.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      >
        {/* cup body */}
        <path d="M50 30 H110 V70 Q110 120 80 130 Q50 120 50 70 Z" />
        {/* left handle */}
        <path d="M50 50 Q30 55 30 75 Q30 95 50 95" />
        {/* right handle */}
        <path d="M110 50 Q130 55 130 75 Q130 95 110 95" />
        {/* stem */}
        <path d="M80 130 V155" />
        {/* base platform */}
        <path d="M55 155 H105 V170 H55 Z" />
        {/* base steps */}
        <path d="M45 170 H115 V180 H45 Z" />
        <path d="M35 180 H125 V195 H35 Z" />
        {/* six tiny stars floating */}
        <g strokeWidth="1.5" opacity="0.9">
          <circle cx="25" cy="25" r="1.5" fill="#E0FF32" />
          <circle cx="135" cy="35" r="1.5" fill="#E0FF32" />
          <circle cx="15" cy="100" r="1.5" fill="#E0FF32" />
          <circle cx="145" cy="110" r="1.5" fill="#E0FF32" />
          <circle cx="30" cy="170" r="1.5" fill="#E0FF32" />
          <circle cx="130" cy="180" r="1.5" fill="#E0FF32" />
        </g>
      </svg>
      {/* Layer 5: host-flag ribbon on the left, desktop only. */}
      <div
        aria-hidden
        className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 hidden xl:flex flex-col gap-3 text-5xl opacity-30"
      >
        <span>🇲🇽</span>
        <span>🇺🇸</span>
        <span>🇨🇦</span>
      </div>

      <div className="relative px-5 py-7 md:px-10 md:py-10 space-y-6">
        {/* Top row: live tag + flags + kickoff line */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.22em] text-neon">
            <span className="relative inline-flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full rounded-full bg-neon opacity-75 animate-ping" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-neon" />
            </span>
            <span>{c.tag}</span>
            <span className="ml-2 text-xl leading-none" aria-hidden>🇲🇽 🇺🇸 🇨🇦</span>
          </div>
          <span className="font-mono text-[10px] text-muted uppercase tracking-wide">
            FIFA · {c.when}
          </span>
        </div>

        {/* Hero row: left title + right countdown */}
        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6 lg:gap-10">
          <div className="space-y-2">
            <h2 className="font-display text-4xl md:text-5xl lg:text-6xl xl:text-7xl font-semibold uppercase tracking-tighter leading-[0.92] text-neon">
              {c.title}
              <span className={`ml-1 inline-block ${cursor ? "opacity-100" : "opacity-0"}`}>▌</span>
            </h2>
            <p className="font-mono text-xs md:text-sm uppercase tracking-[0.2em] text-secondary">
              {c.where}
            </p>
            <p className="font-mono text-[11px] md:text-xs text-neon/60">
              ⚽ {c.hosts}
            </p>
            <p className="font-mono text-[11px] md:text-xs text-muted">
              <span className="text-neon/70">{c.until}</span>  ·  {c.toKickoff}
            </p>
          </div>
          <div className="flex items-end gap-3 md:gap-5">
            <Cell value={String(r.days)} label={c.dLabel} live />
            <span className="font-display text-4xl md:text-6xl text-muted pb-2" aria-hidden>:</span>
            <Cell value={pad(r.hours)} label={c.hLabel} live />
            <span className="font-display text-4xl md:text-6xl text-muted pb-2 hidden sm:inline" aria-hidden>:</span>
            <div className="hidden sm:block">
              <Cell value={pad(r.minutes)} label={c.mLabel} live />
            </div>
            <span className="font-display text-4xl md:text-6xl text-muted pb-2 hidden md:inline" aria-hidden>:</span>
            <div className="hidden md:block">
              <Cell value={pad(r.seconds)} label={c.sLabel} live />
            </div>
          </div>
        </div>

        {/* Bottom row: progress bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.2em] text-muted">
            <span>progress toward kickoff</span>
            <span className="tabular-nums text-neon" suppressHydrationWarning>
              {pctText}
            </span>
          </div>
          <div className="relative h-2 rounded-full bg-high overflow-hidden">
            <div
              className="absolute inset-y-0 left-0 bg-neon shadow-[0_0_12px_rgba(224,255,50,0.8)] transition-[width] duration-1000 ease-linear"
              style={{ width: `${(filled * 100).toFixed(3)}%` }}
              suppressHydrationWarning
            />
          </div>
        </div>
      </div>
    </section>
  );
}
