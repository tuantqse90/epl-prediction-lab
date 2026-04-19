"use client";

import { useEffect, useState, type ReactNode } from "react";

type Tab = { id: string; label: string; node: ReactNode };

// Server renders every tab's content; we toggle visibility client-side.
// Keeps SSR/SEO friendly (every panel in HTML) while letting users pick
// which section is on-screen. Selected tab also syncs to the URL hash
// so /match/X#markets deep-links into the right view.
export default function MatchTabs({ tabs, defaultTab }: { tabs: Tab[]; defaultTab?: string }) {
  const fallback = defaultTab ?? tabs[0]?.id;
  const [active, setActive] = useState<string>(fallback);

  // Hash sync: on mount, adopt hash if it matches a tab id. Subsequent
  // clicks update the hash without jumping.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const raw = window.location.hash.replace("#", "");
    if (raw && tabs.some((t) => t.id === raw)) {
      setActive(raw);
    }
    function onHash() {
      const h = window.location.hash.replace("#", "");
      if (h && tabs.some((t) => t.id === h)) setActive(h);
    }
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, [tabs]);

  function pick(id: string) {
    setActive(id);
    if (typeof window !== "undefined") {
      // Replace instead of push so back button doesn't cycle through tabs.
      window.history.replaceState(null, "", `#${id}`);
    }
  }

  return (
    <div className="space-y-6">
      <nav
        className="sticky top-[58px] z-30 flex gap-1 overflow-x-auto -mx-6 px-6 py-2 border-b border-border/40 bg-surface/85 backdrop-blur supports-[backdrop-filter]:bg-surface/70"
        role="tablist"
      >
        {tabs.map((tab) => {
          const on = tab.id === active;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={on}
              onClick={() => pick(tab.id)}
              className={
                "shrink-0 rounded-full px-4 py-1.5 font-mono text-xs uppercase tracking-wider transition-colors " +
                (on
                  ? "bg-neon text-on-neon"
                  : "text-secondary hover:text-neon")
              }
            >
              {tab.label}
            </button>
          );
        })}
      </nav>
      {tabs.map((tab) => (
        <div
          key={tab.id}
          role="tabpanel"
          aria-hidden={tab.id !== active}
          className={tab.id === active ? "space-y-6" : "hidden"}
        >
          {tab.node}
        </div>
      ))}
    </div>
  );
}
