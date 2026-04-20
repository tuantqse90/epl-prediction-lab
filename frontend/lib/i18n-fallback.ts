/**
 * tLang — 5-language pick helper with English fallback.
 *
 * Keeps the site predominantly EN/VI (curated by the team) while giving
 * TH/ZH/KO users a real translation where we have one. Components call:
 *
 *   const title = tLang(lang, {
 *     en: "Virtual bankroll · Kelly",
 *     vi: "Bankroll ảo · Kelly",
 *     th: "...",
 *     zh: "...",
 *     ko: "...",
 *   });
 *
 * If a locale key is missing, falls back to `en`. This lets us add partial
 * translations without crashing and lets the rest of the codebase migrate
 * incrementally from the `lang === "vi" ? ... : ...` binary pattern.
 */
import type { Lang } from "./i18n";

export function tLang<T>(lang: Lang, dict: Partial<Record<Lang, T>> & { en: T }): T {
  return dict[lang] ?? dict.en;
}
