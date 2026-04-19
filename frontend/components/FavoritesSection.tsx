"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { readFavorites } from "@/lib/favorites";
import type { MatchOut } from "@/lib/types";
import TeamLogo from "./TeamLogo";

// Shown above the generic fixtures grid IF the user has favorites AND
// any of the listed matches involves a favorite team. Pure client render
// — server doesn't know the user's favorites.
export default function FavoritesSection({ matches }: { matches: MatchOut[] }) {
  const [favs, setFavs] = useState<string[]>([]);

  useEffect(() => {
    setFavs(readFavorites());
    function sync() {
      setFavs(readFavorites());
    }
    window.addEventListener("favorites-change", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("favorites-change", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  if (favs.length === 0) return null;

  const rows = matches.filter(
    (m) => favs.includes(m.home.slug) || favs.includes(m.away.slug),
  );
  if (rows.length === 0) return null;

  return (
    <section className="card space-y-3">
      <h2 className="label">Your teams · {rows.length} upcoming</h2>
      <ul className="divide-y divide-border/60">
        {rows.slice(0, 8).map((m) => (
          <li key={m.id}>
            <Link
              href={`/match/${m.id}`}
              className="flex items-center justify-between gap-3 py-2 text-sm hover:text-neon transition-colors"
            >
              <span className="flex items-center gap-2 min-w-0">
                <TeamLogo slug={m.home.slug} name={m.home.name} size={16} />
                <span className={favs.includes(m.home.slug) ? "text-neon" : ""}>{m.home.short_name}</span>
                <span className="text-muted mx-1">vs</span>
                <span className={favs.includes(m.away.slug) ? "text-neon" : ""}>{m.away.short_name}</span>
                <TeamLogo slug={m.away.slug} name={m.away.name} size={16} />
              </span>
              <span className="font-mono text-xs text-muted shrink-0">
                {new Date(m.kickoff_time).toISOString().slice(5, 16).replace("T", " ")}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
