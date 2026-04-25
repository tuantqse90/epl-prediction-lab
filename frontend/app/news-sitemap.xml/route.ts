// Google News sitemap — different schema from the regular sitemap.
// Lists every match URL whose story was generated in the last 48 h
// (Google News only crawls articles ≤ 48h old). Helps stories surface
// in Google News + Top Stories carousel.
//
// Reference: https://developers.google.com/search/docs/crawling-indexing/sitemaps/news-sitemap

import { NextResponse } from "next/server";

const SITE = "https://predictor.nullshift.sh";
const BASE =
  typeof window === "undefined"
    ? process.env.SERVER_API_URL ?? "http://localhost:8000"
    : process.env.NEXT_PUBLIC_API_URL ?? "";

type StoryRow = {
  match_id: number;
  kickoff: string;
  home_short: string;
  away_short: string;
  generated_at: string | null;
};

export const revalidate = 600;

function escapeXml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

export async function GET() {
  let stories: StoryRow[] = [];
  try {
    const res = await fetch(`${BASE}/api/stats/stories?limit=100`, {
      next: { revalidate: 600 },
    });
    if (res.ok) {
      const body = await res.json();
      stories = (body?.stories ?? []) as StoryRow[];
    }
  } catch {
    /* swallow — empty news sitemap better than 500 */
  }

  const cutoff = Date.now() - 48 * 60 * 60 * 1000;
  const fresh = stories.filter((s) => {
    const t = s.generated_at ? Date.parse(s.generated_at) : NaN;
    return Number.isFinite(t) && t >= cutoff;
  });

  const items = fresh
    .map((s) => {
      const url = `${SITE}/match/${s.match_id}`;
      const title = `${s.home_short} vs ${s.away_short} — match story`;
      const pubDate = (s.generated_at ?? new Date().toISOString()).slice(0, 19) + "+00:00";
      return `  <url>
    <loc>${url}</loc>
    <news:news>
      <news:publication>
        <news:name>EPL Prediction Lab</news:name>
        <news:language>vi</news:language>
      </news:publication>
      <news:publication_date>${pubDate}</news:publication_date>
      <news:title>${escapeXml(title)}</news:title>
    </news:news>
  </url>`;
    })
    .join("\n");

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
${items}
</urlset>`;

  return new NextResponse(xml, {
    headers: {
      "Content-Type": "application/xml; charset=utf-8",
      "Cache-Control": "public, max-age=0, s-maxage=600, stale-while-revalidate=1800",
    },
  });
}
