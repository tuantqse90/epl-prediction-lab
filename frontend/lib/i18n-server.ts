import { cookies } from "next/headers";
import "../locales"; // side-effect: registerDicts
import { DEFAULT_LANG, type Lang, LANGS, t as tRaw } from "./i18n";

export async function getLang(): Promise<Lang> {
  const c = await cookies();
  const raw = c.get("lang")?.value;
  return (LANGS as readonly string[]).includes(raw ?? "") ? (raw as Lang) : DEFAULT_LANG;
}

export function tFor(lang: Lang) {
  return (key: string, vars?: Record<string, string | number>) => tRaw(lang, key, vars);
}
