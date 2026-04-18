import { cookies } from "next/headers";
import "../locales"; // side-effect: registerDicts
import { DEFAULT_LANG, type Lang, LANGS, t as tRaw } from "./i18n";
import { DEFAULT_LEAGUE, type LeagueSlug, LEAGUES } from "./leagues";

export async function getLang(): Promise<Lang> {
  const c = await cookies();
  const raw = c.get("lang")?.value;
  return (LANGS as readonly string[]).includes(raw ?? "") ? (raw as Lang) : DEFAULT_LANG;
}

export async function getLeagueSlug(): Promise<LeagueSlug> {
  const c = await cookies();
  const raw = c.get("league")?.value as LeagueSlug | undefined;
  if (raw && LEAGUES.some((l) => l.slug === raw)) return raw;
  return DEFAULT_LEAGUE;
}

export function tFor(lang: Lang) {
  return (key: string, vars?: Record<string, string | number>) => tRaw(lang, key, vars);
}
