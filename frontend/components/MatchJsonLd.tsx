import type { MatchOut } from "@/lib/types";
import { leagueByCode } from "@/lib/leagues";

// Schema.org SportsEvent for a match. Next.js App Router allows plain
// <script type="application/ld+json"> in server components, so no need to
// use the dedicated Head component.
export default function MatchJsonLd({ match, url }: { match: MatchOut; url: string }) {
  const league = leagueByCode(match.league_code);
  const leagueName = league?.name_en ?? "Football";

  const eventStatus =
    match.status === "live"
      ? "EventMovedOnline"
      : match.status === "final"
        ? "EventScheduled"
        : "EventScheduled";

  const ld = {
    "@context": "https://schema.org",
    "@type": "SportsEvent",
    name: `${match.home.name} vs ${match.away.name}`,
    startDate: match.kickoff_time,
    eventStatus: `https://schema.org/${eventStatus}`,
    sport: "Football",
    url,
    location: {
      "@type": "Place",
      name: `${match.home.name} home ground`,
    },
    homeTeam: {
      "@type": "SportsTeam",
      name: match.home.name,
    },
    awayTeam: {
      "@type": "SportsTeam",
      name: match.away.name,
    },
    superEvent: {
      "@type": "SportsEvent",
      name: `${leagueName} ${match.season}`,
    },
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(ld) }}
    />
  );
}
