import type { MetadataRoute } from "next";

const SITE = "https://predictor.nullshift.sh";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        // Personal / write / billing / admin surfaces shouldn't be in
        // the index. Embed routes get their own iframe contexts and
        // also shouldn't show up as standalone search results.
        disallow: [
          "/admin",
          "/admin/*",
          "/billing",
          "/api/*",
          "/embed",
          "/embed/*",
          "/embed-docs",
          "/api-docs",
          "/_next/",
        ],
      },
    ],
    sitemap: `${SITE}/sitemap.xml`,
    host: SITE,
  };
}
