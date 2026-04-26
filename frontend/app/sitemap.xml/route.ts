// Sitemap index — Next 15's generateSitemaps() emits per-shard
// /sitemap/[id].xml but doesn't auto-create the index that Google
// actually wants at /sitemap.xml. This route hand-builds it.
//
// Shard layout (matches frontend/app/sitemap.ts):
//   /sitemap/0.xml   static routes
//   /sitemap/1.xml   league shard 0 (EPL)
//   /sitemap/2.xml   league shard 1 (La Liga)
//   /sitemap/3.xml   league shard 2 (Serie A)
//   /sitemap/4.xml   league shard 3 (Bundesliga)
//   /sitemap/5.xml   league shard 4 (Ligue 1)

import { NextResponse } from "next/server";
import { LEAGUES } from "@/lib/leagues";

const SITE = "https://predictor.nullshift.sh";

export const revalidate = 3600;

export async function GET() {
  const now = new Date().toISOString();
  const shards = [0, ...LEAGUES.map((_, i) => i + 1)];
  const items = shards
    .map(
      (id) =>
        `  <sitemap><loc>${SITE}/sitemap/${id}.xml</loc><lastmod>${now}</lastmod></sitemap>`,
    )
    .join("\n");
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${items}
</sitemapindex>`;
  return new NextResponse(xml, {
    headers: {
      "Content-Type": "application/xml; charset=utf-8",
      "Cache-Control": "public, max-age=0, s-maxage=3600, stale-while-revalidate=600",
    },
  });
}
