import Link from "next/link";

import LangToggle from "./LangToggle";
import LeagueSelector from "./LeagueSelector";
import MobileNavDrawer from "./MobileNavDrawer";
import NavLinks from "./NavLinks";
import SearchModal from "./SearchModal";
import ThemeToggle from "./ThemeToggle";
import type { Lang } from "@/lib/i18n";
import { getLeagueSlug } from "@/lib/i18n-server";

export default async function SiteHeader({ lang }: { lang: Lang }) {
  const league = await getLeagueSlug();
  return (
    <header className="sticky top-0 z-40 border-b border-border/40 bg-surface/85 backdrop-blur supports-[backdrop-filter]:bg-surface/70">
      {/* Neon accent stripe — 1px gradient along the very top edge. */}
      <div aria-hidden className="h-px bg-gradient-to-r from-transparent via-neon/55 to-transparent" />
      <nav className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-6 py-3 text-sm">
        {/* Logo + ping dot to signal 'live service' */}
        <Link
          href="/"
          className="group flex items-center gap-2 font-display font-semibold uppercase tracking-tight shrink-0"
          aria-label="Prediction Lab home"
        >
          <span aria-hidden className="relative inline-flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full rounded-full bg-neon opacity-70 animate-ping" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-neon" />
          </span>
          <span className="group-hover:text-neon transition-colors">Prediction Lab</span>
        </Link>

        {/* Center nav — 4 dropdown groups on desktop only. On mobile the
            MobileBottomNav takes over: the nav groups overlap the league
            selector in a 375-px viewport otherwise. */}
        <div className="relative hidden md:flex items-center gap-5 font-mono min-w-0 px-2 -mx-2">
          <NavLinks lang={lang} />
        </div>

        {/* Right controls. On mobile we keep only league + lang so the
            header doesn't crowd; search/theme are secondary and only
            appear ≥ md. */}
        <div className="flex items-center gap-2 shrink-0">
          <LeagueSelector current={league} />
          <span aria-hidden className="hidden md:inline h-4 w-px bg-border" />
          <span className="hidden md:inline-flex"><SearchModal /></span>
          <span aria-hidden className="hidden md:inline h-4 w-px bg-border" />
          <span className="hidden md:inline-flex"><ThemeToggle /></span>
          <span aria-hidden className="hidden md:inline h-4 w-px bg-border" />
          <LangToggle />
          <MobileNavDrawer />
        </div>
      </nav>
    </header>
  );
}
