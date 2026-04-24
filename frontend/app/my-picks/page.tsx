"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import MyPicksVsModel from "@/components/MyPicksVsModel";
import {
  readPicks, removePick, settlePick, summary,
  type MyPick,
} from "@/lib/my-picks";
import { useLang } from "@/lib/i18n-client";
import { tLang } from "@/lib/i18n-fallback";

type MatchMeta = {
  id: number;
  home: { short_name: string; slug: string };
  away: { short_name: string; slug: string };
  status: string;
  home_goals: number | null;
  away_goals: number | null;
  kickoff_time: string;
};

export default function MyPicksPage() {
  const lang = useLang();
  const [picks, setPicks] = useState<MyPick[]>([]);
  const [meta, setMeta] = useState<Record<number, MatchMeta>>({});

  useEffect(() => {
    const load = () => setPicks(readPicks());
    load();
    window.addEventListener("my-picks-change", load);
    return () => window.removeEventListener("my-picks-change", load);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      const ids = Array.from(new Set(picks.map((p) => p.match_id)));
      const entries = await Promise.all(
        ids.map(async (id) => {
          try {
            const res = await fetch(`/api/matches/${id}`);
            if (!res.ok) return null;
            return [id, (await res.json()) as MatchMeta] as const;
          } catch {
            return null;
          }
        }),
      );
      if (cancelled) return;
      const out: Record<number, MatchMeta> = {};
      for (const e of entries) if (e) out[e[0]] = e[1];
      setMeta(out);
    }
    if (picks.length > 0) run();
    return () => { cancelled = true; };
  }, [picks]);

  function autoSettle(p: MyPick) {
    const m = meta[p.match_id];
    if (!m || m.status !== "final" || m.home_goals == null || m.away_goals == null) return;
    const actual: "H" | "D" | "A" =
      m.home_goals > m.away_goals ? "H" : m.home_goals < m.away_goals ? "A" : "D";
    settlePick(p.id, p.outcome === actual);
  }

  const s = summary(picks);

  if (picks.length === 0) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12 space-y-6">
        <Link href="/" className="btn-ghost text-sm">
          {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
        </Link>
        <h1 className="headline-section">
          {tLang(lang, { en: "My picks", vi: "Picks của tôi", th: "พิกของฉัน", zh: "我的选择", ko: "내 픽" })}
        </h1>
        <div className="card space-y-3">
          <p className="text-secondary">
            {tLang(lang, {
              en: "Empty. Open any match, pick an outcome + enter the odds you got, and it lands here. No login — saved in your browser.",
              vi: "Trống. Mở trận, chọn kết quả + nhập odds bạn đặt, sẽ vào đây. Không login — lưu trình duyệt.",
              th: "ว่างเปล่า เปิดแมตช์, เลือกผล + กรอก odds ที่วาง",
              zh: "空。打开比赛,选择结果 + 输入你的赔率,保存在这里。",
              ko: "비어 있음. 경기를 열고 결과 선택 + 배당 입력",
            })}
          </p>
          <div className="flex gap-3 pt-2">
            <Link href="/" className="btn-primary text-sm">
              {tLang(lang, { en: "Browse matches", vi: "Xem trận", th: "ดูแมตช์", zh: "浏览比赛", ko: "경기 보기" })}
            </Link>
            <Link href="/sync" className="btn-ghost text-sm">
              {tLang(lang, { en: "Sync across devices", vi: "Sync thiết bị", th: "ซิงค์", zh: "跨设备同步", ko: "기기 동기화" })}
            </Link>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
      </Link>

      <header className="space-y-2">
        <p className="font-mono text-xs text-muted">
          {tLang(lang, { en: "Personal ledger · localStorage only", vi: "Sổ cá nhân · localStorage", th: "บันทึกส่วนตัว", zh: "个人记录", ko: "개인 기록" })}
        </p>
        <h1 className="headline-section">
          {tLang(lang, { en: "My picks", vi: "Picks của tôi", th: "พิกของฉัน", zh: "我的选择", ko: "내 픽" })}
        </h1>
      </header>

      <section className="card grid grid-cols-2 md:grid-cols-5 gap-4">
        <div>
          <p className="label">Total</p>
          <p className="stat">{s.total}</p>
        </div>
        <div>
          <p className="label">Settled</p>
          <p className="stat">{s.settled}</p>
        </div>
        <div>
          <p className="label">{tLang(lang, { en: "Hits", vi: "Trúng", th: "ถูก", zh: "中", ko: "적중" })}</p>
          <p className="stat text-neon">{s.hits}</p>
        </div>
        <div>
          <p className="label">P&amp;L</p>
          <p className={`stat ${s.pnl > 0 ? "text-neon" : s.pnl < 0 ? "text-error" : ""}`}>
            {s.pnl > 0 ? "+" : ""}{s.pnl.toFixed(2)}u
          </p>
        </div>
        <div>
          <p className="label">ROI</p>
          <p className={`stat ${s.roi > 0 ? "text-neon" : s.roi < 0 ? "text-error" : ""}`}>
            {s.roi > 0 ? "+" : ""}{s.roi.toFixed(1)}%
          </p>
        </div>
      </section>

      <MyPicksVsModel picks={picks} meta={meta as any} />

      <section className="card p-0 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-[10px] uppercase tracking-wide text-muted">
            <tr className="border-b border-border">
              <th className="px-3 py-3 text-left">
                {tLang(lang, { en: "Placed", vi: "Ngày", th: "วันที่", zh: "日期", ko: "날짜" })}
              </th>
              <th className="px-3 py-3 text-left">
                {tLang(lang, { en: "Match", vi: "Trận", th: "แมตช์", zh: "比赛", ko: "경기" })}
              </th>
              <th className="px-3 py-3 text-left">Pick</th>
              <th className="px-3 py-3 text-right">Odds</th>
              <th className="px-3 py-3 text-right">Stake</th>
              <th className="px-3 py-3 text-center">Status</th>
              <th className="px-3 py-3 text-right">P&amp;L</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {picks
              .slice()
              .sort((a, b) => b.placed_at.localeCompare(a.placed_at))
              .map((p) => {
                const m = meta[p.match_id];
                if (m && !p.settled) autoSettle(p);
                const pickLabel = m
                  ? p.outcome === "H" ? m.home.short_name
                    : p.outcome === "A" ? m.away.short_name
                    : "Draw"
                  : p.outcome;
                return (
                  <tr key={p.id} className="border-t border-border-muted">
                    <td className="px-3 py-2 font-mono text-xs text-muted">{p.placed_at.slice(0, 10)}</td>
                    <td className="px-3 py-2">
                      {m ? (
                        <Link href={`/match/${p.match_id}`} className="hover:text-neon">
                          {m.home.short_name} vs {m.away.short_name}
                        </Link>
                      ) : (
                        `#${p.match_id}`
                      )}
                    </td>
                    <td className="px-3 py-2 font-mono">{pickLabel}</td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums">{p.odds.toFixed(2)}</td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums">{p.stake}u</td>
                    <td className="px-3 py-2 text-center">
                      {!p.settled ? (
                        <span className="font-mono text-[10px] uppercase text-muted">
                          {tLang(lang, { en: "pending", vi: "chờ", th: "รอ", zh: "待定", ko: "대기" })}
                        </span>
                      ) : p.hit ? (
                        <span className="font-mono text-[10px] uppercase text-neon">HIT</span>
                      ) : (
                        <span className="font-mono text-[10px] uppercase text-error">MISS</span>
                      )}
                    </td>
                    <td
                      className={`px-3 py-2 text-right font-mono tabular-nums ${
                        p.pnl == null ? "text-muted" : p.pnl > 0 ? "text-neon" : "text-error"
                      }`}
                    >
                      {p.pnl == null ? "—" : `${p.pnl > 0 ? "+" : ""}${p.pnl.toFixed(2)}`}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <button
                        onClick={() => removePick(p.id)}
                        className="text-muted hover:text-error text-xs"
                        aria-label="Remove"
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                );
              })}
          </tbody>
        </table>
      </section>

      <p className="font-mono text-[11px] uppercase tracking-wide text-muted">
        {tLang(lang, {
          en: "Picks auto-settle when the match hits final. Remove a pick = ✕. All saved in your browser only.",
          vi: "Picks tự settle khi trận FT. Bấm ✕ để xoá. Chỉ lưu trong trình duyệt.",
          th: "พิกจะ auto-settle เมื่อแมตช์จบ",
          zh: "比赛结束后自动结算",
          ko: "경기 종료 시 자동 정산",
        })}
      </p>
    </main>
  );
}
