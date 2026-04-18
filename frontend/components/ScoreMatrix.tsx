import type { Lang } from "@/lib/i18n";
import { t } from "@/lib/i18n";
import type { PredictionOut } from "@/lib/types";
import { modelVersionToRho, scoreMatrix } from "@/lib/poisson";

const MAX_GOALS = 5;

/** Blend `#161616` → `#E0FF32` by the given 0-1 alpha. Smooth ramp without
 *  relying on color-mix (wider browser support). */
function blend(alpha: number): string {
  const a = Math.max(0, Math.min(1, alpha));
  const base = [22, 22, 22];        // #161616 raised surface
  const neon = [224, 255, 50];      // #E0FF32
  const rgb = base.map((b, i) => Math.round(b + (neon[i] - b) * a));
  return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
}

function pct(x: number) {
  if (x < 0.005) return "";
  if (x < 0.1) return `${(x * 100).toFixed(1)}%`;
  return `${Math.round(x * 100)}%`;
}

export default function ScoreMatrix({
  prediction,
  lang = "vi",
  homeShort,
  awayShort,
}: {
  prediction: PredictionOut;
  lang?: Lang;
  homeShort?: string;
  awayShort?: string;
}) {
  const rho = modelVersionToRho(prediction.model_version);
  const m = scoreMatrix(
    prediction.expected_home_goals,
    prediction.expected_away_goals,
    rho,
    MAX_GOALS,
  );

  let max = 0;
  let maxIJ = [0, 0];
  for (let i = 0; i <= MAX_GOALS; i++) {
    for (let j = 0; j <= MAX_GOALS; j++) {
      if (m[i][j] > max) {
        max = m[i][j];
        maxIJ = [i, j];
      }
    }
  }

  const home = homeShort ?? t(lang, "detail.home");
  const away = awayShort ?? t(lang, "detail.away");

  return (
    <section className="card space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display font-semibold uppercase tracking-tight text-lg">
            {t(lang, "detail.scoreMatrix.title")}
          </h2>
          <p className="mt-1 text-xs text-muted font-mono">
            {t(lang, "detail.scoreMatrix.top")} · {home} {maxIJ[0]}–{maxIJ[1]} {away}
          </p>
        </div>
        <div className="text-right">
          <p className="font-mono text-xs text-muted uppercase tracking-wide">
            {t(lang, "detail.home")} / {t(lang, "detail.away")}
          </p>
          <p className="font-mono text-lg tabular-nums text-secondary">
            λ {prediction.expected_home_goals.toFixed(2)} · {prediction.expected_away_goals.toFixed(2)}
          </p>
        </div>
      </div>

      <div className="overflow-x-auto">
        <div
          className="inline-grid gap-[3px] rounded-lg p-[3px] bg-border-muted"
          style={{
            gridTemplateColumns: `auto repeat(${MAX_GOALS + 1}, minmax(3rem, 1fr))`,
          }}
        >
          {/* corner */}
          <div className="bg-raised px-2 py-3" />
          {/* away header: cell 0..5 + team name label spanning visually with the numbers */}
          {Array.from({ length: MAX_GOALS + 1 }, (_, j) => (
            <div
              key={`ah-${j}`}
              className="bg-raised px-2 py-3 text-center font-mono text-sm font-semibold tabular-nums text-secondary"
            >
              {j}
            </div>
          ))}

          {Array.from({ length: MAX_GOALS + 1 }, (_, i) => (
            <>
              <div
                key={`hh-${i}`}
                className="bg-raised px-2 py-3 text-center font-mono text-sm font-semibold tabular-nums text-secondary"
              >
                {i}
              </div>
              {Array.from({ length: MAX_GOALS + 1 }, (_, j) => {
                const p = m[i][j];
                const alpha = max > 0 ? p / max : 0;
                const isTop = i === maxIJ[0] && j === maxIJ[1];
                const dark = alpha > 0.55;
                const textClass = dark ? "text-on-neon" : "text-secondary";
                const tip = `${home} ${i} – ${j} ${away} · ${(p * 100).toFixed(2)}%`;
                return (
                  <div
                    key={`c-${i}-${j}`}
                    title={tip}
                    aria-label={tip}
                    className={`relative flex items-center justify-center py-3 text-center font-mono text-xs tabular-nums transition-colors cursor-help ${textClass}`}
                    style={{
                      backgroundColor: blend(alpha),
                      ...(isTop
                        ? {
                            outline: "2px solid #E0FF32",
                            outlineOffset: "-2px",
                            boxShadow: "0 0 20px rgba(224,255,50,0.5)",
                          }
                        : null),
                    }}
                  >
                    <span className={isTop ? "font-semibold text-sm" : ""}>{pct(p)}</span>
                  </div>
                );
              })}
            </>
          ))}
        </div>

        {/* axis labels */}
        <div className="mt-2 flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.12em] text-muted">
          <span className="pl-10">
            ↓ {home} {t(lang, "detail.home").toLowerCase()}
          </span>
          <span>
            {away} {t(lang, "detail.away").toLowerCase()} →
          </span>
        </div>
      </div>

      {/* legend */}
      <div className="flex items-center gap-3 font-mono text-[10px] text-muted">
        <span>0%</span>
        <div
          className="h-2 flex-1 rounded-full"
          style={{
            background: `linear-gradient(to right, ${blend(0)}, ${blend(0.5)}, ${blend(1)})`,
          }}
        />
        <span>{Math.round(max * 100)}%</span>
      </div>

      <p className="text-muted text-xs leading-relaxed">
        {t(lang, "detail.scoreMatrix.footer", {
          lamH: prediction.expected_home_goals.toFixed(2),
          lamA: prediction.expected_away_goals.toFixed(2),
          rho: rho.toFixed(2),
        })}
      </p>
    </section>
  );
}
