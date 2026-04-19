import type { Metadata } from "next";

import SiteHeader from "@/components/SiteHeader";
import { LangProvider } from "@/lib/i18n-client";
import { getLang } from "@/lib/i18n-server";

import "./globals.css";

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
    alternateLocale: ["en_GB"],
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
        {plausibleHost && plausibleDomain && (
          <script
            defer
            data-domain={plausibleDomain}
            src={`${plausibleHost}/js/script.js`}
          />
        )}
        <LangProvider lang={lang}>
          <SiteHeader lang={lang} />
          {children}
        </LangProvider>
      </body>
    </html>
  );
}
