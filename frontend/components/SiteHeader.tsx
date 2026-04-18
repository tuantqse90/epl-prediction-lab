import Link from "next/link";
import LangToggle from "./LangToggle";
import { tFor } from "@/lib/i18n-server";
import type { Lang } from "@/lib/i18n";

export default function SiteHeader({ lang }: { lang: Lang }) {
  const t = tFor(lang);
  return (
    <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4 text-sm">
      <Link href="/" className="font-display font-semibold uppercase tracking-tight">
        EPL Lab
      </Link>
      <div className="flex items-center gap-6 font-mono">
        <Link href="/" className="text-secondary hover:text-neon transition-colors">
          {t("nav.fixtures")}
        </Link>
        <Link href="/table" className="text-secondary hover:text-neon transition-colors">
          {t("nav.table")}
        </Link>
        <Link href="/last-weekend" className="text-secondary hover:text-neon transition-colors">
          {t("nav.recent")}
        </Link>
        <Link href="/scorers" className="text-secondary hover:text-neon transition-colors">
          {t("nav.scorers")}
        </Link>
        <Link href="/stats" className="text-secondary hover:text-neon transition-colors">
          {t("nav.stats")}
        </Link>
        <LangToggle />
      </div>
    </nav>
  );
}
