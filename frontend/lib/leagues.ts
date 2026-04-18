export type LeagueSlug = "epl" | "laliga" | "seriea" | "bundesliga" | "ligue1";

export type League = {
  slug: LeagueSlug;
  code: string;          // soccerdata league code
  short: string;
  name_en: string;
  name_vi: string;
  emoji: string;
};

export const LEAGUES: League[] = [
  { slug: "epl",        code: "ENG-Premier League", short: "EPL",       name_en: "Premier League", name_vi: "Ngoại hạng Anh", emoji: "🏴󠁧󠁢󠁥󠁮󠁧󠁿" },
  { slug: "laliga",     code: "ESP-La Liga",        short: "LaLiga",    name_en: "La Liga",        name_vi: "La Liga",        emoji: "🇪🇸" },
  { slug: "seriea",     code: "ITA-Serie A",        short: "Serie A",   name_en: "Serie A",        name_vi: "Serie A",        emoji: "🇮🇹" },
  { slug: "bundesliga", code: "GER-Bundesliga",     short: "Bundesliga",name_en: "Bundesliga",     name_vi: "Bundesliga",     emoji: "🇩🇪" },
  { slug: "ligue1",     code: "FRA-Ligue 1",        short: "Ligue 1",   name_en: "Ligue 1",        name_vi: "Ligue 1",        emoji: "🇫🇷" },
];

export const DEFAULT_LEAGUE: LeagueSlug = "epl";

export const BY_SLUG: Record<string, League> = Object.fromEntries(
  LEAGUES.map((l) => [l.slug, l]),
);

export const BY_CODE: Record<string, League> = Object.fromEntries(
  LEAGUES.map((l) => [l.code, l]),
);

export function getLeague(slug: string): League {
  return BY_SLUG[slug] ?? BY_SLUG[DEFAULT_LEAGUE];
}

export function leagueByCode(code: string | null | undefined): League | undefined {
  return code ? BY_CODE[code] : undefined;
}
