"use client";

import { useState } from "react";

import { addPick } from "@/lib/my-picks";
import { useLang } from "@/lib/i18n-client";
import { tLang } from "@/lib/i18n-fallback";

export default function LogPickButton({
  matchId,
  defaultOutcome = "H",
  defaultOdds,
  homeShort,
  awayShort,
}: {
  matchId: number;
  defaultOutcome?: "H" | "D" | "A";
  defaultOdds?: number;
  homeShort: string;
  awayShort: string;
}) {
  const lang = useLang();
  const [open, setOpen] = useState(false);
  const [outcome, setOutcome] = useState<"H" | "D" | "A">(defaultOutcome);
  const [odds, setOdds] = useState<string>(
    defaultOdds ? defaultOdds.toFixed(2) : "",
  );
  const [stake, setStake] = useState<string>("1");
  const [done, setDone] = useState(false);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const o = parseFloat(odds);
    const s = parseFloat(stake);
    if (!(o > 1) || !(s > 0)) return;
    addPick({ match_id: matchId, outcome, odds: o, stake: s });
    setDone(true);
    setTimeout(() => {
      setDone(false);
      setOpen(false);
    }, 1200);
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="btn-ghost text-xs"
      >
        {tLang(lang, {
          en: "+ Log this as my pick",
          vi: "+ Ghi vào Picks của tôi",
          th: "+ เพิ่มลงพิกของฉัน",
          zh: "+ 记录为我的选择",
          ko: "+ 내 픽에 추가",
        })}
      </button>
    );
  }

  return (
    <form onSubmit={submit} className="card space-y-3">
      <p className="font-mono text-[10px] uppercase tracking-wide text-neon">
        {tLang(lang, { en: "Log pick", vi: "Ghi pick", th: "บันทึกพิก", zh: "记录选择", ko: "픽 기록" })}
      </p>
      <div className="flex gap-2">
        {(["H", "D", "A"] as const).map((o) => (
          <button
            key={o}
            type="button"
            onClick={() => setOutcome(o)}
            className={`flex-1 rounded px-3 py-2 font-mono text-xs uppercase tracking-wide border ${
              outcome === o
                ? "border-neon bg-neon text-on-neon"
                : "border-border text-secondary"
            }`}
          >
            {o === "H" ? homeShort : o === "A" ? awayShort : "Draw"}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2">
        <label className="space-y-1">
          <span className="label">Odds</span>
          <input
            type="number"
            step="0.01"
            min="1.01"
            value={odds}
            onChange={(e) => setOdds(e.target.value)}
            className="w-full rounded border border-border bg-raised px-2 py-1 font-mono text-sm"
            placeholder="2.10"
            required
          />
        </label>
        <label className="space-y-1">
          <span className="label">Stake</span>
          <input
            type="number"
            step="0.1"
            min="0.1"
            value={stake}
            onChange={(e) => setStake(e.target.value)}
            className="w-full rounded border border-border bg-raised px-2 py-1 font-mono text-sm"
            required
          />
        </label>
      </div>
      <div className="flex gap-2">
        <button type="submit" className="btn-primary text-xs flex-1">
          {done
            ? tLang(lang, { en: "✓ Saved", vi: "✓ Đã lưu", th: "✓ บันทึก", zh: "✓ 已保存", ko: "✓ 저장됨" })
            : tLang(lang, { en: "Save", vi: "Lưu", th: "บันทึก", zh: "保存", ko: "저장" })}
        </button>
        <button type="button" onClick={() => setOpen(false)} className="btn-ghost text-xs">
          {tLang(lang, { en: "Cancel", vi: "Huỷ", th: "ยกเลิก", zh: "取消", ko: "취소" })}
        </button>
      </div>
    </form>
  );
}
