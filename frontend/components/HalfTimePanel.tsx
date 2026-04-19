import type { HalfTimePredictions } from "@/lib/api";
import type { Lang } from "@/lib/i18n";

function pct(x: number) {
  return `${Math.round(x * 100)}%`;
}

function label(o: "H" | "D" | "A", home: string, away: string) {
  return o === "H" ? home : o === "A" ? away : "Draw";
}

export default function HalfTimePanel({
  data,
  homeShort,
  awayShort,
  lang,
}: {
  data: HalfTimePredictions;
  homeShort: string;
  awayShort: string;
  lang: Lang;
}) {
  const title = lang === "vi" ? "Hiệp 1" : "Half-time";
  const htftLabel = lang === "vi" ? "HT / FT (top 5)" : "HT / FT (top 5)";
  const ctlabel = lang === "vi" ? "Tỷ số HT nhiều khả năng" : "Most likely HT score";

  return (
    <section className="card space-y-4">
      <h2 className="label">{title}</h2>

      {/* HT winner bar */}
      <div className="grid grid-cols-3 gap-3 text-center">
        <div>
          <p className="label text-[10px]">{label("H", homeShort, awayShort)}</p>
          <p className="stat text-neon">{pct(data.p_home_lead)}</p>
        </div>
        <div>
          <p className="label text-[10px]">{label("D", homeShort, awayShort)}</p>
          <p className="stat text-secondary">{pct(data.p_draw)}</p>
        </div>
        <div>
          <p className="label text-[10px]">{label("A", homeShort, awayShort)}</p>
          <p className="stat">{pct(data.p_away_lead)}</p>
        </div>
      </div>

      {/* Top HT scorelines */}
      {data.top_scorelines.length > 0 && (
        <div>
          <p className="label text-[10px] mb-1">{ctlabel}</p>
          <ul className="flex flex-wrap gap-2 font-mono text-sm">
            {data.top_scorelines.map(([h, a, p]) => (
              <li
                key={`${h}-${a}`}
                className="rounded bg-high px-2 py-1 tabular-nums"
              >
                {h}–{a} <span className="text-muted text-xs">{pct(p)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* HT/FT grid top 5 */}
      <div>
        <p className="label text-[10px] mb-1">{htftLabel}</p>
        <ul className="space-y-1 text-sm font-mono">
          {data.htft.slice(0, 5).map((r, i) => (
            <li key={i} className="flex items-center gap-3">
              <span className="text-muted w-10 shrink-0">
                {label(r.ht, homeShort, awayShort)}
              </span>
              <span className="text-muted">/</span>
              <span className="text-primary w-10 shrink-0">
                {label(r.ft, homeShort, awayShort)}
              </span>
              <span className="flex-1 h-2 rounded bg-high overflow-hidden">
                <span
                  className="block h-full bg-neon"
                  style={{ width: `${Math.min(100, r.p * 100 / Math.max(...data.htft.map((x) => x.p)) * 100)}%` }}
                />
              </span>
              <span className="w-12 text-right tabular-nums text-neon">
                {pct(r.p)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
