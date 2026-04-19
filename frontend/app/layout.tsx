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
  return (
    <html lang={lang}>
      <head>
        {process.env.NEXT_PUBLIC_PLAUSIBLE_HOST && process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN && (
          <script
            defer
            data-domain={process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN}
            src={`${process.env.NEXT_PUBLIC_PLAUSIBLE_HOST}/js/script.js`}
          />
        )}
      </head>
      <body className="min-h-screen bg-surface text-primary">
        <LangProvider lang={lang}>
          <SiteHeader lang={lang} />
          {children}
        </LangProvider>
      </body>
    </html>
  );
}
