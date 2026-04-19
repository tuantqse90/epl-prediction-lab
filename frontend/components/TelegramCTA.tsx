import type { Lang } from "@/lib/i18n";

const CHANNEL_URL = "https://t.me/worldcup_predictor";

export default function TelegramCTA({
  lang,
  compact = false,
}: {
  lang: Lang;
  compact?: boolean;
}) {
  const title = lang === "vi" ? "Nhận dự đoán qua Telegram" : "Predictions on Telegram";
  const blurb =
    lang === "vi"
      ? "Top kèo giá trị + khuyến nghị tự tin + goal alerts trực tiếp."
      : "Weekly value bets, confidence picks, and live goal alerts.";
  const cta = lang === "vi" ? "Theo kênh" : "Join channel";

  if (compact) {
    return (
      <a
        href={CHANNEL_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 rounded-full bg-neon px-3 py-1 font-mono text-xs uppercase tracking-wide text-on-neon hover:bg-neon-dim transition-colors"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
          <path d="M9.9 15.1 9.75 19.35c.36 0 .52-.15.71-.34l1.7-1.63 3.53 2.58c.65.36 1.1.17 1.27-.6l2.3-10.77c.22-.98-.35-1.36-.98-1.12L3.3 11.6c-.96.38-.95.92-.17 1.16l4.08 1.27 9.47-5.96c.45-.3.86-.13.52.17" />
        </svg>
        {cta}
      </a>
    );
  }

  return (
    <a
      href={CHANNEL_URL}
      target="_blank"
      rel="noopener noreferrer"
      className="card flex items-center gap-4 hover:border-neon transition-colors group"
    >
      <span
        className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-neon text-on-neon"
        aria-hidden
      >
        <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
          <path d="M9.9 15.1 9.75 19.35c.36 0 .52-.15.71-.34l1.7-1.63 3.53 2.58c.65.36 1.1.17 1.27-.6l2.3-10.77c.22-.98-.35-1.36-.98-1.12L3.3 11.6c-.96.38-.95.92-.17 1.16l4.08 1.27 9.47-5.96c.45-.3.86-.13.52.17" />
        </svg>
      </span>
      <div className="flex-1 min-w-0">
        <p className="font-display font-semibold uppercase tracking-tight text-lg">
          {title}
        </p>
        <p className="text-secondary text-sm">{blurb}</p>
      </div>
      <span className="rounded-full bg-neon px-3 py-1 font-mono text-xs uppercase tracking-wide text-on-neon group-hover:bg-neon-dim transition-colors">
        {cta} →
      </span>
    </a>
  );
}
