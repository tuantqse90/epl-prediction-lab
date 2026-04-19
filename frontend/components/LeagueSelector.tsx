"use client";

import { useRouter } from "next/navigation";
import { LEAGUES, type LeagueSlug } from "@/lib/leagues";

export default function LeagueSelector({ current }: { current: LeagueSlug }) {
  const router = useRouter();

  function set(slug: LeagueSlug) {
    if (typeof document !== "undefined") {
      document.cookie = `league=${slug};path=/;max-age=${60 * 60 * 24 * 365};samesite=lax`;
    }
    router.refresh();
  }

  return (
    <select
      value={current}
      onChange={(e) => set(e.target.value as LeagueSlug)}
      className="bg-raised/60 border border-border rounded-full pl-3 pr-7 py-1 text-xs font-mono uppercase tracking-wider text-primary hover:border-neon hover:bg-raised focus:border-neon appearance-none bg-no-repeat bg-[position:right_0.6rem_center]"
      style={{
        backgroundImage:
          "url(\"data:image/svg+xml;charset=UTF-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 10 10' fill='none'%3E%3Cpath d='M2 4l3 3 3-3' stroke='%23E0FF32' stroke-width='1.4' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E\")",
      }}
      aria-label="League"
    >
      {LEAGUES.map((l) => (
        <option key={l.slug} value={l.slug} className="bg-surface">
          {l.emoji} {l.short}
        </option>
      ))}
    </select>
  );
}
