import type { Lang } from "@/lib/i18n";
import type { LiveStats } from "@/lib/types";

type Props = {
  stats: LiveStats | null | undefined;
  homeShort: string;
  awayShort: string;
  lang: Lang;
};

// Each row displays home | bar | away. The bar is colored neon on the
// leading side, secondary on the trailing side — classic stats-panel feel.
// Numeric cells fall back to "—" so we don't render blanks.
function StatRow({
  label,
  home,
  away,
  asPct,
}: {
  label: string;
  home?: number | string | null;
  away?: number | string | null;
  asPct?: boolean;
}) {
  const h = home == null ? null : Number(home);
  const a = away == null ? null : Number(away);
  const hasBoth = h != null && !Number.isNaN(h) && a != null && !Number.isNaN(a);
  const total = hasBoth ? (h as number) + (a as number) : 0;
  const leftPct = hasBoth && total > 0 ? ((h as number) / total) * 100 : 50;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-2 font-mono text-xs">
        <span className="tabular-nums text-primary min-w-[2.5rem] text-left">
          {home == null ? "—" : asPct ? `${home}%` : home}
        </span>
        <span className="text-[10px] uppercase tracking-[0.18em] text-muted">{label}</span>
        <span className="tabular-nums text-primary min-w-[2.5rem] text-right">
          {away == null ? "—" : asPct ? `${away}%` : away}
        </span>
      </div>
      <div className="relative h-1.5 rounded-full bg-high overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 bg-neon"
          style={{ width: `${leftPct.toFixed(1)}%` }}
        />
        <div
          className="absolute inset-y-0 right-0 bg-secondary/40"
          style={{ width: `${(100 - leftPct).toFixed(1)}%` }}
        />
      </div>
    </div>
  );
}

export default function LiveStatsPanel({ stats, homeShort, awayShort, lang }: Props) {
  const h = stats?.home ?? null;
  const a = stats?.away ?? null;
  if (!h && !a) return null;

  const rows: Array<{ label: string; home: number | string | null | undefined; away: number | string | null | undefined; asPct?: boolean }> = [
    { label: lang === "vi" ? "KIỂM SOÁT" : "POSSESSION", home: h?.possession_pct, away: a?.possession_pct, asPct: true },
    { label: lang === "vi" ? "CÚ SÚT" : "SHOTS", home: h?.shots_total, away: a?.shots_total },
    { label: lang === "vi" ? "TRÚNG ĐÍCH" : "ON TARGET", home: h?.shots_on, away: a?.shots_on },
    { label: lang === "vi" ? "PHẠT GÓC" : "CORNERS", home: h?.corners, away: a?.corners },
    { label: lang === "vi" ? "PHẠM LỖI" : "FOULS", home: h?.fouls, away: a?.fouls },
    { label: lang === "vi" ? "VIỆT VỊ" : "OFFSIDES", home: h?.offsides, away: a?.offsides },
    { label: lang === "vi" ? "CHUYỀN" : "PASS %", home: h?.passes_pct, away: a?.passes_pct, asPct: true },
    { label: lang === "vi" ? "CỨU THUA" : "SAVES", home: h?.saves, away: a?.saves },
  ];

  return (
    <section className="card space-y-4">
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="font-display font-semibold uppercase tracking-tight text-lg">
          {lang === "vi" ? "Thông số trận đấu" : "Match stats"}
        </h3>
        <div className="flex items-baseline gap-2 font-mono text-[10px] uppercase tracking-[0.15em]">
          <span className="text-neon">{homeShort}</span>
          <span className="text-muted">vs</span>
          <span className="text-primary">{awayShort}</span>
        </div>
      </div>
      <div className="space-y-3">
        {rows.map((r) => (
          <StatRow key={r.label} {...r} />
        ))}
      </div>
    </section>
  );
}
