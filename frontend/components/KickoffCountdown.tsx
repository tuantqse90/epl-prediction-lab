"use client";

import { useEffect, useState } from "react";

import type { Lang } from "@/lib/i18n";

type Unit = "d" | "h" | "m";

function delta(ms: number): { value: number; unit: Unit; past: boolean } {
  const abs = Math.abs(ms);
  const mins = Math.floor(abs / 60000);
  const past = ms < 0;
  if (mins < 60) return { value: mins, unit: "m", past };
  if (mins < 60 * 24) return { value: Math.floor(mins / 60), unit: "h", past };
  return { value: Math.floor(mins / 60 / 24), unit: "d", past };
}

// Locale → (unit labels + "starts in N" / "ended N ago" templates).
// Keeping it inline so the component stays one file; five entries is cheap.
const COPY: Record<Lang, {
  unit: Record<Unit, string>;
  future: (n: number, unit: string) => string;
  past: (n: number, unit: string) => string;
}> = {
  vi: {
    unit: { d: "ngày", h: "giờ", m: "phút" },
    future: (n, u) => `bắt đầu sau ${n} ${u}`,
    past:   (n, u) => `kết thúc ${n} ${u} trước`,
  },
  en: {
    unit: { d: "d", h: "h", m: "m" },
    future: (n, u) => `in ${n}${u}`,
    past:   (n, u) => `${n}${u} ago`,
  },
  th: {
    unit: { d: "วัน", h: "ชม.", m: "นาที" },
    future: (n, u) => `เริ่มในอีก ${n} ${u}`,
    past:   (n, u) => `จบไปแล้ว ${n} ${u}`,
  },
  zh: {
    unit: { d: "天", h: "小时", m: "分钟" },
    future: (n, u) => `${n}${u}后开始`,
    past:   (n, u) => `${n}${u}前结束`,
  },
  ko: {
    unit: { d: "일", h: "시간", m: "분" },
    future: (n, u) => `${n}${u} 후 시작`,
    past:   (n, u) => `${n}${u} 전 종료`,
  },
};

function label(iso: string, lang: Lang): string {
  const diff = new Date(iso).getTime() - Date.now();
  const d = delta(diff);
  const copy = COPY[lang] ?? COPY.en;
  const unit = copy.unit[d.unit];
  return d.past ? copy.past(d.value, unit) : copy.future(d.value, unit);
}

export default function KickoffCountdown({ iso, lang }: { iso: string; lang: Lang }) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 60_000);
    return () => clearInterval(id);
  }, []);
  return (
    <span key={tick} className="font-mono text-[10px] text-neon tabular-nums">
      {label(iso, lang)}
    </span>
  );
}
