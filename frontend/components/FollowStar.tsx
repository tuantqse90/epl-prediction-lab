"use client";

import { useEffect, useState } from "react";

import { readFavorites, toggleFavorite } from "@/lib/favorites";

export default function FollowStar({ slug, label }: { slug: string; label?: string }) {
  const [on, setOn] = useState(false);

  useEffect(() => {
    setOn(readFavorites().includes(slug));
    function sync() {
      setOn(readFavorites().includes(slug));
    }
    window.addEventListener("favorites-change", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("favorites-change", sync);
      window.removeEventListener("storage", sync);
    };
  }, [slug]);

  return (
    <button
      type="button"
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        setOn(toggleFavorite(slug));
      }}
      aria-label={on ? `Unfollow ${label ?? slug}` : `Follow ${label ?? slug}`}
      title={on ? "Unfollow" : "Follow"}
      className={
        "inline-flex items-center justify-center rounded-full h-6 w-6 text-sm transition-colors " +
        (on
          ? "bg-neon text-on-neon"
          : "border border-border text-muted hover:text-neon hover:border-neon")
      }
    >
      {on ? "★" : "☆"}
    </button>
  );
}
