import type { Lang } from "./i18n";

// Timezone chosen per UI locale — every user sees kickoffs in their own
// wall-clock time. Prevents default-browser-TZ hydration mismatch and keeps
// Telegram/OG previews consistent across locales.
const TZ_BY_LANG: Record<Lang, string> = {
  vi: "Asia/Ho_Chi_Minh",
  en: "Europe/London",
  th: "Asia/Bangkok",
  zh: "Asia/Shanghai",
  ko: "Asia/Seoul",
};

const LOCALE_BY_LANG: Record<Lang, string> = {
  vi: "vi-VN",
  en: "en-GB",
  th: "th-TH",
  zh: "zh-CN",
  ko: "ko-KR",
};

export function tzFor(lang: Lang): string {
  return TZ_BY_LANG[lang] ?? TZ_BY_LANG.en;
}

export function localeFor(lang: Lang): string {
  return LOCALE_BY_LANG[lang] ?? LOCALE_BY_LANG.en;
}

export function formatKickoff(iso: string | Date, lang: Lang): string {
  const d = typeof iso === "string" ? new Date(iso) : iso;
  return d.toLocaleString(localeFor(lang), {
    weekday: "short",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: tzFor(lang),
  });
}

export function formatShortDate(iso: string | Date, lang: Lang): string {
  const d = typeof iso === "string" ? new Date(iso) : iso;
  return d.toLocaleString(localeFor(lang), {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: tzFor(lang),
  });
}

export function formatDateOnly(iso: string | Date, lang: Lang): string {
  const d = typeof iso === "string" ? new Date(iso) : iso;
  return d.toLocaleDateString(localeFor(lang), {
    weekday: "short",
    day: "2-digit",
    month: "short",
    timeZone: tzFor(lang),
  });
}
