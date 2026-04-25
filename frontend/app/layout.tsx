import type { Metadata } from "next";
import { headers } from "next/headers";

import InstallPrompt from "@/components/InstallPrompt";
import MobileBottomNav from "@/components/MobileBottomNav";
import PageViewTracker from "@/components/PageViewTracker";
import ShortcutsModal from "@/components/ShortcutsModal";
import SiteHeader from "@/components/SiteHeader";
import { LangProvider } from "@/lib/i18n-client";
import type { Lang } from "@/lib/i18n";
import { getLang } from "@/lib/i18n-server";
import { alternatesFor, organizationLd, websiteLd } from "@/lib/seo";

import "./globals.css";


async function ChromeOrEmbed({
  lang,
  children,
}: {
  lang: Lang;
  children: React.ReactNode;
}) {
  // Embed routes skip SiteHeader so partner iframes render just the card,
  // not the whole site chrome. Next 15 middleware sets x-next-pathname
  // for us; fall back to x-url / referer for safety.
  const hdr = await headers();
  const pathname = hdr.get("x-pathname") ?? "";
  const isEmbed = pathname.startsWith("/embed") || pathname.includes("/embed/");
  return (
    <>
      {!isEmbed && <SiteHeader lang={lang} />}
      {children}
      {!isEmbed && (
        <footer className="mx-auto max-w-6xl px-6 py-8 mt-12 border-t border-border/30 font-mono text-[10px] uppercase tracking-wider text-muted flex flex-wrap gap-x-4 gap-y-2">
          <a href="/methodology" className="hover:text-neon">methodology</a>
          <a href="/glossary" className="hover:text-neon">glossary</a>
          <a href="/calibration" className="hover:text-neon">calibration</a>
          <a href="/api-docs" className="hover:text-neon">api</a>
          <a href="/embed-docs" className="hover:text-neon">embed</a>
          <a href="/press-kit" className="hover:text-neon">press</a>
          <a href="/changelog" className="hover:text-neon">changelog</a>
          <a href="/pricing" className="hover:text-neon">pricing</a>
          <a href="/discord" className="hover:text-neon">discord</a>
          <a href="https://ko-fi.com/predictor" target="_blank" rel="noopener" className="hover:text-neon">☕ tip</a>
          <span className="flex-1" />
          <a href="/privacy" className="hover:text-neon">privacy</a>
          <a href="/terms" className="hover:text-neon">terms</a>
          <a href="/ops" className="hover:text-neon">status</a>
        </footer>
      )}
      {!isEmbed && <MobileBottomNav />}
      {!isEmbed && <InstallPrompt />}
      {!isEmbed && <ShortcutsModal />}
      {!isEmbed && <PageViewTracker />}
    </>
  );
}

const SITE = "https://predictor.nullshift.sh";

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: {
    default: "EPL Prediction Lab",
    template: "%s · EPL Prediction Lab",
  },
  description:
    "xG-driven Poisson + Dixon-Coles predictions for every Premier League match, with market-edge value bets and plain-language reasoning.",
  applicationName: "EPL Prediction Lab",
  keywords: ["EPL", "Premier League", "prediction", "xG", "Poisson", "Dixon-Coles", "value bets"],
  openGraph: {
    type: "website",
    url: SITE,
    siteName: "EPL Prediction Lab",
    title: "EPL Prediction Lab",
    description: "Poisson + Dixon-Coles predictions, value bets, and reasoning for every EPL match.",
    locale: "vi_VN",
    alternateLocale: ["en_GB", "th_TH", "zh_CN", "ko_KR"],
  },
  twitter: {
    card: "summary_large_image",
    title: "EPL Prediction Lab",
    description: "Poisson + Dixon-Coles predictions and value bets for every EPL match.",
  },
  robots: {
    index: true,
    follow: true,
  },
  alternates: alternatesFor("/"),
  appleWebApp: {
    capable: true,
    title: "EPL Lab",
    statusBarStyle: "black-translucent",
  },
  formatDetection: {
    telephone: false,
    email: false,
    address: false,
  },
};

export const viewport = {
  themeColor: "#000000",
  // Let mobile Safari fill the full viewport (including notch) without
  // extra white bars when the user installs the PWA.
  viewportFit: "cover" as const,
  width: "device-width",
  initialScale: 1,
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const lang = await getLang();
  const plausibleHost = process.env.NEXT_PUBLIC_PLAUSIBLE_HOST;
  const plausibleDomain = process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN;
  return (
    <html lang={lang}>
      {/* Do NOT hand-render <head> — Next App Router injects stylesheet
          links into its own auto-managed head. A manual <head/> sibling
          ships an empty head on first paint, then React hydration races
          with the injected link and the CSS briefly/permanently vanishes. */}
      <body className="min-h-screen bg-surface text-primary">
        {/* Theme bootstrap — runs synchronously before React hydrates so
            light-mode users don't see a flash of dark. Reads the same
            localStorage key the ThemeToggle writes. */}
        <script
          dangerouslySetInnerHTML={{
            __html:
              "(function(){try{var t=localStorage.getItem('epl-lab:theme');" +
              "if(t==='light')document.documentElement.dataset.theme='light';}catch(e){}})();",
          }}
        />
        {/* Organization + WebSite/SearchAction JSON-LD — emitted once at
            the root so Google can build a knowledge-panel + sitelinks
            search box without scraping per-page. */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationLd()) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteLd()) }}
        />
        {plausibleHost && plausibleDomain && (
          <script
            defer
            data-domain={plausibleDomain}
            src={`${plausibleHost}/js/script.js`}
          />
        )}
        <LangProvider lang={lang}>
          <ChromeOrEmbed lang={lang}>{children}</ChromeOrEmbed>
        </LangProvider>
      </body>
    </html>
  );
}
