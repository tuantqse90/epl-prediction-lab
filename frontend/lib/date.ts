import type { Lang } from "./i18n";

// Timezone chosen per UI locale — VN users see their wall-clock time,
// EN users see London kickoff time (EPL home). Avoids the default-browser-TZ
// hydration mismatch and means Telegram/OG previews are consistent globally.
export function tzFor(lang: Lang): string {
  return lang === "vi" ? "Asia/Ho_Chi_Minh" : "Europe/London";
}

export function localeFor(lang: Lang): string {
  return lang === "vi" ? "vi-VN" : "en-GB";
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
