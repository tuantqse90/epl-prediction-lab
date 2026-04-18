import type { MetadataRoute } from "next";

import { listMatches } from "@/lib/api";

const SITE = "https://predictor.nullshift.sh";
const TEAM_SLUGS = [
  "arsenal", "aston-villa", "bournemouth", "brentford", "brighton",
  "burnley", "chelsea", "crystal-palace", "everton", "fulham",
  "leeds", "liverpool", "manchester-city", "manchester-united",
  "newcastle-united", "nottingham-forest", "sunderland", "tottenham",
  "west-ham", "wolverhampton-wanderers",
];

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const staticEntries: MetadataRoute.Sitemap = [
    { url: `${SITE}/`, changeFrequency: "daily", priority: 1.0, lastModified: now },
    { url: `${SITE}/table`, changeFrequency: "daily", priority: 0.8, lastModified: now },
    { url: `${SITE}/stats`, changeFrequency: "weekly", priority: 0.7, lastModified: now },
    { url: `${SITE}/last-weekend`, changeFrequency: "weekly", priority: 0.7, lastModified: now },
    { url: `${SITE}/scorers`, changeFrequency: "weekly", priority: 0.6, lastModified: now },
  ];
  const teamEntries = TEAM_SLUGS.map((slug) => ({
    url: `${SITE}/teams/${slug}`,
    changeFrequency: "weekly" as const,
    priority: 0.6,
    lastModified: now,
  }));

  let matchEntries: MetadataRoute.Sitemap = [];
  try {
    const upcoming = await listMatches({ upcomingOnly: true, limit: 30 });
    matchEntries = upcoming.map((m) => ({
      url: `${SITE}/match/${m.id}`,
      changeFrequency: "daily" as const,
      priority: 0.8,
      lastModified: new Date(m.kickoff_time),
    }));
  } catch {
    // sitemap should never 500 even if api is temporarily unavailable
  }

  return [...staticEntries, ...teamEntries, ...matchEntries];
}
