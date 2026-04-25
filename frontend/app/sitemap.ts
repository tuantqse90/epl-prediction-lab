import type { MetadataRoute } from "next";

import { listMatches } from "@/lib/api";
import { LEAGUES } from "@/lib/leagues";

const SITE = "https://predictor.nullshift.sh";

// Next.js renders one sitemap per entry returned here. Sitemap index is
// generated automatically at /sitemap.xml pointing to /sitemap/0.xml,
// /sitemap/1.xml, etc. We dedicate:
//   id=0  → static routes + generic pages
//   id=1..N → one sitemap per league, listing its match + team URLs
export async function generateSitemaps() {
  return [{ id: 0 }, ...LEAGUES.map((_, i) => ({ id: i + 1 }))];
}

export default async function sitemap({
  id,
}: {
  id: number;
}): Promise<MetadataRoute.Sitemap> {
  const now = new Date();

  if (id === 0) {
    return [
      { url: `${SITE}/`,                     changeFrequency: "daily",  priority: 1.0, lastModified: now },
      { url: `${SITE}/proof`,                changeFrequency: "weekly", priority: 0.9, lastModified: now },
      { url: `${SITE}/table`,                changeFrequency: "daily",  priority: 0.8, lastModified: now },
      { url: `${SITE}/last-weekend`,         changeFrequency: "daily",  priority: 0.8, lastModified: now },
      { url: `${SITE}/last-weekend?days=14`, changeFrequency: "daily",  priority: 0.6, lastModified: now },
      { url: `${SITE}/last-weekend?days=30`, changeFrequency: "daily",  priority: 0.6, lastModified: now },
      { url: `${SITE}/stats`,                changeFrequency: "weekly", priority: 0.7, lastModified: now },
      { url: `${SITE}/scorers`,              changeFrequency: "weekly", priority: 0.6, lastModified: now },
      { url: `${SITE}/history`,              changeFrequency: "weekly", priority: 0.5, lastModified: now },
      { url: `${SITE}/roi`,                  changeFrequency: "weekly", priority: 0.5, lastModified: now },
      { url: `${SITE}/docs/model`,           changeFrequency: "monthly",priority: 0.5, lastModified: now },
      { url: `${SITE}/blog`,                 changeFrequency: "weekly", priority: 0.7, lastModified: now },
      { url: `${SITE}/blog/xgb-weight-jump`, changeFrequency: "monthly",priority: 0.6, lastModified: now },
      { url: `${SITE}/blog/dixon-coles-rho`, changeFrequency: "monthly",priority: 0.6, lastModified: now },
      { url: `${SITE}/blog/all-time-gap`,    changeFrequency: "monthly",priority: 0.6, lastModified: now },
      { url: `${SITE}/leagues`,              changeFrequency: "weekly", priority: 0.7, lastModified: now },
      { url: `${SITE}/leagues/epl`,          changeFrequency: "daily",  priority: 0.8, lastModified: now },
      { url: `${SITE}/leagues/laliga`,       changeFrequency: "daily",  priority: 0.8, lastModified: now },
      { url: `${SITE}/leagues/seriea`,       changeFrequency: "daily",  priority: 0.8, lastModified: now },
      { url: `${SITE}/leagues/bundesliga`,   changeFrequency: "daily",  priority: 0.8, lastModified: now },
      { url: `${SITE}/leagues/ligue1`,       changeFrequency: "daily",  priority: 0.8, lastModified: now },
      { url: `${SITE}/europe`,               changeFrequency: "daily",  priority: 0.9, lastModified: now },
      { url: `${SITE}/about`,                changeFrequency: "monthly",priority: 0.5, lastModified: now },
      { url: `${SITE}/faq`,                  changeFrequency: "monthly",priority: 0.6, lastModified: now },
      { url: `${SITE}/glossary`,             changeFrequency: "monthly",priority: 0.6, lastModified: now },
      { url: `${SITE}/methodology`,          changeFrequency: "monthly",priority: 0.7, lastModified: now },
      { url: `${SITE}/changelog`,            changeFrequency: "weekly", priority: 0.4, lastModified: now },
      { url: `${SITE}/press-kit`,            changeFrequency: "monthly",priority: 0.5, lastModified: now },
      { url: `${SITE}/calibration`,          changeFrequency: "weekly", priority: 0.7, lastModified: now },
      { url: `${SITE}/equity-curve`,         changeFrequency: "weekly", priority: 0.7, lastModified: now },
      { url: `${SITE}/title-race`,           changeFrequency: "weekly", priority: 0.8, lastModified: now },
      { url: `${SITE}/relegation`,           changeFrequency: "weekly", priority: 0.7, lastModified: now },
      { url: `${SITE}/scorers-race`,         changeFrequency: "weekly", priority: 0.7, lastModified: now },
      { url: `${SITE}/power-rankings`,       changeFrequency: "weekly", priority: 0.7, lastModified: now },
      { url: `${SITE}/arbs`,                 changeFrequency: "daily",  priority: 0.6, lastModified: now },
      { url: `${SITE}/middles`,              changeFrequency: "daily",  priority: 0.5, lastModified: now },
      { url: `${SITE}/kelly-explorer`,       changeFrequency: "weekly", priority: 0.5, lastModified: now },
      { url: `${SITE}/pricing`,              changeFrequency: "monthly",priority: 0.6, lastModified: now },
      { url: `${SITE}/billing`,              changeFrequency: "monthly",priority: 0.3, lastModified: now },
      { url: `${SITE}/stories`,              changeFrequency: "daily",  priority: 0.8, lastModified: now },
      { url: `${SITE}/discord`,              changeFrequency: "monthly",priority: 0.4, lastModified: now },
    ];
  }

  const lg = LEAGUES[id - 1];
  if (!lg) return [];

  let matches: Awaited<ReturnType<typeof listMatches>> = [];
  try {
    // Pull both upcoming and recent finals so Google can find match pages
    // for both future fixtures and result-carrying post-match URLs.
    const [upcoming, recent] = await Promise.all([
      listMatches({ upcomingOnly: true, limit: 200, league: lg.slug }),
      listMatches({ upcomingOnly: false, limit: 200, league: lg.slug }),
    ]);
    const seen = new Set<number>();
    for (const m of [...upcoming, ...recent]) {
      if (!seen.has(m.id)) {
        seen.add(m.id);
        matches.push(m);
      }
    }
  } catch {
    /* sitemap must never throw */
  }

  const matchEntries = matches.map((m) => ({
    url: `${SITE}/match/${m.id}`,
    changeFrequency: "daily" as const,
    priority: 0.7,
    lastModified: new Date(m.kickoff_time),
  }));

  // Also list unique team URLs observed in this league's matches.
  const teamSlugs = new Set<string>();
  for (const m of matches) {
    teamSlugs.add(m.home.slug);
    teamSlugs.add(m.away.slug);
  }
  const teamEntries = Array.from(teamSlugs).map((slug) => ({
    url: `${SITE}/teams/${slug}`,
    changeFrequency: "weekly" as const,
    priority: 0.5,
    lastModified: now,
  }));

  return [...matchEntries, ...teamEntries];
}
