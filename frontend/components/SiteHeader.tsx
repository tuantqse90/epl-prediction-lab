import Link from "next/link";

import LangToggle from "./LangToggle";
import LeagueSelector from "./LeagueSelector";
import type { Lang } from "@/lib/i18n";
import { getLeagueSlug, tFor } from "@/lib/i18n-server";

export default async function SiteHeader({ lang }: { lang: Lang }) {
  const t = tFor(lang);
  const league = await getLeagueSlug();
  return (
    <header className="sticky top-0 z-40 border-b border-border/40 bg-surface/85 backdrop-blur supports-[backdrop-filter]:bg-surface/70">
    <nav className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4 text-sm">
      <Link href="/" className="font-display font-semibold uppercase tracking-tight shrink-0">
        Prediction Lab
      </Link>
      <div className="flex items-center gap-3 md:gap-5 font-mono overflow-x-auto">
        <LeagueSelector current={league} />
        <Link href="/" className="text-secondary hover:text-neon transition-colors whitespace-nowrap">
          {t("nav.fixtures")}
        </Link>
        <Link href="/table" className="text-secondary hover:text-neon transition-colors whitespace-nowrap">
          {t("nav.table")}
        </Link>
        <Link href="/last-weekend" className="text-secondary hover:text-neon transition-colors whitespace-nowrap">
          {t("nav.recent")}
        </Link>
        <Link href="/scorers" className="text-secondary hover:text-neon transition-colors whitespace-nowrap">
          {t("nav.scorers")}
        </Link>
        <Link href="/stats" className="text-secondary hover:text-neon transition-colors whitespace-nowrap">
          {t("nav.stats")}
        </Link>
        <LangToggle />
      </div>
    </nav>
    </header>
  );
}
