import type { Lang } from "@/lib/i18n";
import { t } from "@/lib/i18n";
import type { PredictionOut } from "@/lib/types";

type Outcome = "H" | "D" | "A";

function winner(p: PredictionOut): Outcome {
  const { p_home_win, p_draw, p_away_win } = p;
  if (p_home_win >= p_draw && p_home_win >= p_away_win) return "H";
  if (p_away_win >= p_draw) return "A";
  return "D";
}

function pct(x: number) {
  return `${Math.round(x * 100)}%`;
}

export default function PredictionBar({
  prediction,
  lang = "vi",
}: {
  prediction: PredictionOut;
  lang?: Lang;
}) {
  const w = winner(prediction);
  const segs: { key: Outcome; value: number; label: string }[] = [
    { key: "H", value: prediction.p_home_win, label: t(lang, "detail.home") },
    { key: "D", value: prediction.p_draw, label: t(lang, "detail.draw") },
    { key: "A", value: prediction.p_away_win, label: t(lang, "detail.away") },
  ];

  return (
    <div className="space-y-2">
      <div className="flex h-2 w-full overflow-hidden rounded-full bg-raised">
        {segs.map((s) => (
          <div
            key={s.key}
            className={s.key === w ? "bg-neon" : "bg-high"}
            style={{ width: `${s.value * 100}%` }}
          />
        ))}
      </div>
      <div className="flex justify-between font-mono text-xs tabular-nums text-secondary">
        {segs.map((s) => (
          <span key={s.key} className={s.key === w ? "text-neon" : ""}>
            {s.label} {pct(s.value)}
          </span>
        ))}
      </div>
    </div>
  );
}
