// SEO helpers — hreflang + canonical + structured-data builders.
//
// We don't run path-prefixed locales (no /vi/match/123 vs /en/match/123);
// the language is cookie + Accept-Language driven. To still signal multi-
// language coverage to Google, we expose every page in 5 alternate
// languages with the SAME canonical URL but different `lang` query param.
// Google treats those as language variants of the same canonical.

const SITE = "https://predictor.nullshift.sh";

const LOCALES: { lang: string; tag: string }[] = [
  { lang: "vi", tag: "vi-VN" },
  { lang: "en", tag: "en-GB" },
  { lang: "th", tag: "th-TH" },
  { lang: "zh", tag: "zh-CN" },
  { lang: "ko", tag: "ko-KR" },
];

/**
 * Build `alternates` for Next's `metadata.alternates`. Pass the canonical
 * path (no host, no trailing slash unless intentional) — e.g. "/match/123",
 * "/stories", "/" for the root.
 */
export function alternatesFor(path: string): {
  canonical: string;
  languages: Record<string, string>;
} {
  const canonical = path.startsWith("/") ? path : `/${path}`;
  const languages: Record<string, string> = {};
  for (const { lang, tag } of LOCALES) {
    const sep = canonical.includes("?") ? "&" : "?";
    languages[tag] = `${SITE}${canonical}${sep}lang=${lang}`;
  }
  // x-default for Google's hreflang convention — points at canonical.
  languages["x-default"] = `${SITE}${canonical}`;
  return { canonical: `${SITE}${canonical}`, languages };
}

/** Organization JSON-LD — emits once on the root layout. */
export function organizationLd() {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: "EPL Prediction Lab",
    url: SITE,
    logo: `${SITE}/icon`,
    sameAs: [
      // Add socials here as they come online (X, FB, etc).
    ],
  };
}

/** WebSite + SearchAction LD — enables Google sitelinks search box. */
export function websiteLd() {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "EPL Prediction Lab",
    url: SITE,
    potentialAction: {
      "@type": "SearchAction",
      target: {
        "@type": "EntryPoint",
        urlTemplate: `${SITE}/search?q={search_term_string}`,
      },
      "query-input": "required name=search_term_string",
    },
  };
}

/** BreadcrumbList LD — pass [{ name, path }] in order; auto-prefixes SITE. */
export function breadcrumbLd(items: { name: string; path: string }[]) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((it, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: it.name,
      item: it.path.startsWith("http") ? it.path : `${SITE}${it.path}`,
    })),
  };
}
