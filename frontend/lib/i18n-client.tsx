"use client";

import { createContext, useContext } from "react";
import "../locales"; // side-effect: registerDicts on the client bundle too
import { DEFAULT_LANG, type Lang, t as tRaw } from "./i18n";

const Ctx = createContext<Lang>(DEFAULT_LANG);

export function LangProvider({ lang, children }: { lang: Lang; children: React.ReactNode }) {
  return <Ctx.Provider value={lang}>{children}</Ctx.Provider>;
}

export function useLang(): Lang {
  return useContext(Ctx);
}

export function useT(): (key: string, vars?: Record<string, string | number>) => string {
  const lang = useLang();
  return (key, vars) => tRaw(lang, key, vars);
}
