"use client";

// Client-side tax-adjusted P&L preview. Reads the current /api/stats/roi
// response (we refetch in-place on jurisdiction change) and shows the
// P&L after the selected jurisdiction's tax rule.

import { useEffect, useState } from "react";

import { useLang } from "@/lib/i18n-client";
import { tLang } from "@/lib/i18n-fallback";

type Jurisdiction = "none" | "en" | "vn" | "eu" | "us";

const TAX_TABLE: Record<Jurisdiction, { wins_tax: number; stake_tax: number; label_en: string; label_vi: string }> = {
  none: { wins_tax: 0,    stake_tax: 0,    label_en: "No tax",             label_vi: "Không thuế" },
  en:   { wins_tax: 0,    stake_tax: 0,    label_en: "UK (no punter tax)", label_vi: "Anh (không thuế)" },
  eu:   { wins_tax: 0,    stake_tax: 0.05, label_en: "EU (5% stake tax)",  label_vi: "EU (5% thuế cược)" },
  vn:   { wins_tax: 0.10, stake_tax: 0,    label_en: "VN (10% wins)",      label_vi: "VN (10% thắng)" },
  us:   { wins_tax: 0.24, stake_tax: 0,    label_en: "US (24% wins)",      label_vi: "US (24% thắng)" },
};

function applyTax(pnl: number, totalStaked: number, j: Jurisdiction): number {
  const r = TAX_TABLE[j];
  let out = pnl - r.stake_tax * totalStaked;
  if (out > 0) out = out * (1 - r.wins_tax);
  return out;
}

export default function TaxToggle({ threshold, season }: { threshold: number; season: string }) {
  const lang = useLang();
  const [j, setJ] = useState<Jurisdiction>("none");
  const [pnl, setPnl] = useState<number | null>(null);
  const [bets, setBets] = useState(0);

  useEffect(() => {
    fetch(`/api/stats/roi?threshold=${threshold}&season=${encodeURIComponent(season)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        setPnl(d.total_pnl ?? 0);
        setBets(d.total_bets ?? 0);
      });
  }, [threshold, season]);

  if (pnl == null) return null;

  const staked = bets;    // 1u per bet
  const adjusted = applyTax(pnl, staked, j);
  const adjustedRoi = staked > 0 ? (adjusted / staked) * 100 : 0;

  return (
    <section className="card space-y-3">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <h2 className="label">
          {tLang(lang, {
            en: "Tax-adjusted ROI",
            vi: "ROI sau thuế",
            th: "ROI หลังหักภาษี",
            zh: "税后 ROI",
            ko: "세후 ROI",
          })}
        </h2>
        <select
          value={j}
          onChange={(e) => setJ(e.target.value as Jurisdiction)}
          className="bg-raised border border-border rounded px-2 py-1 font-mono text-xs"
        >
          {(Object.keys(TAX_TABLE) as Jurisdiction[]).map((k) => (
            <option key={k} value={k}>
              {lang === "vi" ? TAX_TABLE[k].label_vi : TAX_TABLE[k].label_en}
            </option>
          ))}
        </select>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div>
          <p className="label">{tLang(lang, { en: "Raw P&L", vi: "P&L gốc", th: "P&L ดิบ", zh: "原始", ko: "원본" })}</p>
          <p className={`stat ${pnl > 0 ? "text-neon" : pnl < 0 ? "text-error" : ""}`}>
            {pnl > 0 ? "+" : ""}{pnl.toFixed(2)}u
          </p>
        </div>
        <div>
          <p className="label">
            {tLang(lang, { en: "After tax", vi: "Sau thuế", th: "หลังภาษี", zh: "税后", ko: "세후" })}
          </p>
          <p className={`stat ${adjusted > 0 ? "text-neon" : adjusted < 0 ? "text-error" : ""}`}>
            {adjusted > 0 ? "+" : ""}{adjusted.toFixed(2)}u
          </p>
        </div>
        <div>
          <p className="label">
            {tLang(lang, { en: "ROI after", vi: "ROI sau", th: "ROI หลัง", zh: "ROI 税后", ko: "세후 ROI" })}
          </p>
          <p className={`stat ${adjustedRoi > 0 ? "text-neon" : "text-error"}`}>
            {adjustedRoi > 0 ? "+" : ""}{adjustedRoi.toFixed(1)}%
          </p>
        </div>
      </div>
    </section>
  );
}
