import type { Markets } from "@/lib/api";
import type { Lang } from "@/lib/i18n";

function pct(x: number) {
  return `${Math.round(x * 100)}%`;
}

function MarketRow({
  label,
  yes,
  no,
}: {
  label: string;
  yes: number;
  no: number;
}) {
  const yesPct = Math.round(yes * 100);
  return (
    <div className="flex items-center gap-3 font-mono text-sm">
      <span className="w-20 shrink-0 text-secondary uppercase text-xs tracking-wide">
        {label}
      </span>
      <div className="flex-1 flex h-6 overflow-hidden rounded bg-high">
        <div
          className="flex items-center justify-center bg-neon text-on-neon font-semibold text-xs"
          style={{ width: `${yesPct}%` }}
          title={`Yes ${pct(yes)}`}
        >
          {yesPct >= 18 ? pct(yes) : ""}
        </div>
        <div
          className="flex items-center justify-center text-xs text-muted"
          style={{ width: `${100 - yesPct}%` }}
          title={`No ${pct(no)}`}
        >
          {yesPct < 82 ? pct(no) : ""}
        </div>
      </div>
    </div>
  );
}

export default function MarketsPanel({ markets, lang }: { markets: Markets; lang: Lang }) {
  const title = lang === "vi" ? "Các thị trường khác" : "Other markets";
  const subhead =
    lang === "vi"
      ? "Phân phối tỷ số Poisson suy ra O/U, BTTS, giữ sạch lưới. Cột neon = có / đúng, cột mờ = không."
      : "Derived from the Poisson scoreline matrix. Neon column = yes, muted column = no.";
  const labels = {
    over15: lang === "vi" ? "Over 1.5" : "Over 1.5",
    over25: lang === "vi" ? "Over 2.5" : "Over 2.5",
    over35: lang === "vi" ? "Over 3.5" : "Over 3.5",
    btts: "BTTS",
    home_cs: lang === "vi" ? "Chủ sạch lưới" : "Home CS",
    away_cs: lang === "vi" ? "Khách sạch lưới" : "Away CS",
  };

  return (
    <section className="card space-y-3">
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <h2 className="label">{title}</h2>
        <p className="text-[11px] text-muted max-w-md">{subhead}</p>
      </div>
      <div className="space-y-2">
        <MarketRow label={labels.over15} yes={markets.prob_over_1_5} no={1 - markets.prob_over_1_5} />
        <MarketRow label={labels.over25} yes={markets.prob_over_2_5} no={1 - markets.prob_over_2_5} />
        <MarketRow label={labels.over35} yes={markets.prob_over_3_5} no={1 - markets.prob_over_3_5} />
        <MarketRow label={labels.btts} yes={markets.prob_btts} no={1 - markets.prob_btts} />
        <MarketRow label={labels.home_cs} yes={markets.prob_home_clean_sheet} no={1 - markets.prob_home_clean_sheet} />
        <MarketRow label={labels.away_cs} yes={markets.prob_away_clean_sheet} no={1 - markets.prob_away_clean_sheet} />
      </div>
    </section>
  );
}
