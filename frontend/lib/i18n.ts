export const LANGS = ["en", "vi"] as const;
export type Lang = (typeof LANGS)[number];
export const DEFAULT_LANG: Lang = "vi";

// Deeply nested keys would be nicer; flat string keys keep the dict grep-able.
export type Dict = Record<string, string>;

export function t(lang: Lang, key: keyof typeof import("../locales/en").default | string, vars?: Record<string, string | number>): string {
  // Dynamic imports prevent a runtime mismatch between server and client bundles.
  // We resolve synchronously via pre-imported dicts; see `locales/index.ts`.
  const dict = __dicts[lang] ?? __dicts[DEFAULT_LANG];
  let s = dict[key as string] ?? key;
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, String(v));
  return s as string;
}

// Injected via locales/index.ts. Avoids top-level async imports.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export let __dicts: Record<Lang, Dict> = {} as any;
export function registerDicts(dicts: Record<Lang, Dict>) {
  __dicts = dicts;
}
