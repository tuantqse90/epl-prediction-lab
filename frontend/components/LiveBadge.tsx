import type { Lang } from "@/lib/i18n";

export default function LiveBadge({
  minute,
  period,
  lang,
}: {
  minute: number;
  period?: string | null;
  lang: Lang;
}) {
  // Half time → pause badge, no pulsing dot.
  if (period === "HT") {
    const label = lang === "vi" ? "NGHỈ GIỮA HIỆP" : "HALF TIME";
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-secondary/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-secondary">
        <span className="h-2 w-2 rounded-full bg-secondary" />
        {label}
      </span>
    );
  }

  // Default: in-play (1H / 2H / ET / LIVE) — pulsing red.
  const label = lang === "vi" ? "TRỰC TIẾP" : "LIVE";
  return (
    <span className="relative inline-flex items-center gap-1 rounded-full bg-error/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-error">
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-error opacity-75" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-error" />
      </span>
      {label} · {minute}&apos;
    </span>
  );
}
