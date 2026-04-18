import type { Lang } from "@/lib/i18n";
import { t } from "@/lib/i18n";
import type { PredictionOut } from "@/lib/types";

export default function CommitmentBadge({
  prediction,
  lang = "vi",
  compact = false,
}: {
  prediction: PredictionOut;
  lang?: Lang;
  compact?: boolean;
}) {
  const hash = prediction.commitment_hash;
  if (!hash) return null;

  const shortHash = `${hash.slice(0, 10)}…${hash.slice(-6)}`;

  if (compact) {
    return (
      <span className="font-mono text-[10px] text-muted">
        {t(lang, "fp.title").toLowerCase()} · {shortHash}
      </span>
    );
  }

  return (
    <section className="card space-y-2 font-mono text-xs">
      <div className="flex items-baseline justify-between">
        <span className="text-secondary">{t(lang, "fp.title")}</span>
        <span className="label text-neon">{t(lang, "fp.badge")}</span>
      </div>
      <div className="break-all text-secondary">{hash}</div>
      <p className="text-muted leading-relaxed">{t(lang, "fp.explain")}</p>
    </section>
  );
}
