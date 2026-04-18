"use client";

import { useEffect, useState } from "react";

function delta(ms: number): { value: number; unit: "d" | "h" | "m"; past: boolean } {
  const abs = Math.abs(ms);
  const mins = Math.floor(abs / 60000);
  const past = ms < 0;
  if (mins < 60) return { value: mins, unit: "m", past };
  if (mins < 60 * 24) return { value: Math.floor(mins / 60), unit: "h", past };
  return { value: Math.floor(mins / 60 / 24), unit: "d", past };
}

function label(iso: string, lang: "vi" | "en"): string {
  const diff = new Date(iso).getTime() - Date.now();
  const d = delta(diff);
  if (lang === "vi") {
    const unit = d.unit === "d" ? "ngày" : d.unit === "h" ? "giờ" : "phút";
    return d.past ? `kết thúc ${d.value} ${unit} trước` : `bắt đầu sau ${d.value} ${unit}`;
  }
  const unit = d.unit === "d" ? "d" : d.unit === "h" ? "h" : "m";
  return d.past ? `${d.value}${unit} ago` : `in ${d.value}${unit}`;
}

export default function KickoffCountdown({ iso, lang }: { iso: string; lang: "vi" | "en" }) {
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
