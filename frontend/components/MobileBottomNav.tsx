"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// Fixed bottom nav on mobile only. 5 quick-nav icons for the top surfaces.
// Desktop users stay on the dropdown menus in the header.

const ITEMS: Array<{ href: string; icon: string; label: string }> = [
  { href: "/", icon: "⚽", label: "Home" },
  { href: "/table", icon: "Σ", label: "Table" },
  { href: "/arbs", icon: "¤", label: "Arbs" },
  { href: "/watchlist", icon: "★", label: "Watch" },
  { href: "/my-picks", icon: "◐", label: "Picks" },
];

export default function MobileBottomNav() {
  const pathname = usePathname();
  if (pathname?.startsWith("/embed")) return null;

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 md:hidden border-t border-border/60 bg-surface/95 backdrop-blur"
      aria-label="Primary"
    >
      <ul className="flex items-stretch">
        {ITEMS.map((it) => {
          const active = pathname === it.href;
          return (
            <li key={it.href} className="flex-1">
              <Link
                href={it.href}
                className={`flex flex-col items-center gap-1 py-2 font-mono text-[10px] uppercase tracking-wider ${
                  active ? "text-neon" : "text-secondary hover:text-neon"
                }`}
              >
                <span aria-hidden className="text-base leading-none">{it.icon}</span>
                <span>{it.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
