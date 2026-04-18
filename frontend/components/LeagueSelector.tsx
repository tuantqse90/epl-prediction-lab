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
      className="bg-raised border border-border rounded-full px-3 py-1 text-xs font-mono uppercase tracking-wide text-secondary hover:border-neon focus:outline-none focus:border-neon"
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
