"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useLang } from "@/lib/i18n-client";
import { tLang } from "@/lib/i18n-fallback";

type LiveEdgeRow = {
  match_id: number;
  league_code: string | null;
  home_short: string;
  away_short: string;
  home_goals: number;
  away_goals: number;
  minute: number;
  p_home_win: number;
  p_draw: number;
  p_away_win: number;
  best_home: number | null;
  best_draw: number | null;
  best_away: number | null;
  best_edge_pp: number;
  best_edge_outcome: "H" | "D" | "A";
  best_edge_odds: number;
  best_edge_source: string | null;
};

export default function LivePage() {
  const lang = useLang();
  const [rows, setRows] = useState<LiveEdgeRow[]>([]);
  const [checkedAt, setCheckedAt] = useState<string>("");

  async function load() {
    const res = await fetch("/api/live-edge?min_edge_pp=2");
    if (!res.ok) return;
    const body = await res.json();
    setRows(body.matches);
    setCheckedAt(new Date(body.as_of).toLocaleTimeString());
  }

  useEffect(() => {
    load();
    const iv = setInterval(load, 20_000);
    return () => clearInterval(iv);
  }, []);

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
      </Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">
          in-play · value bets · refresh 20s · <span className="text-neon">{checkedAt || "—"}</span>
        </p>
        <h1 className="headline-section">
          {tLang(lang, {
            en: "Live edge — value bets right now",
            vi: "Live edge — giá trị đang có",
            th: "Live edge",
            zh: "实时 edge — 当前价值盘",
            ko: "라이브 엣지",
          })}
        </h1>
        <p className="max-w-2xl text-secondary">
          {tLang(lang, {
            en: "Re-derives P(H/D/A) every 20s from pre-match λ + current score + minute. Compares to best-of-books live 1X2 odds. Shows every live match where model edge ≥ 2pp.",
            vi: "Tính lại P(H/D/A) mỗi 20s từ λ gốc + tỷ số hiện tại + phút. So với best-odds live 1X2. Hiện mọi trận live có edge ≥ 2pp.",
            th: "คำนวณ P(H/D/A) ใหม่ทุก 20 วิ",
            zh: "每 20 秒重算 P(H/D/A)",
            ko: "20초마다 P(H/D/A) 재계산",
          })}
        </p>
      </header>

      {rows.length === 0 ? (
        <div className="card text-muted">
          {tLang(lang, {
            en: "No in-play value bets right now. Matches need to be live + have live odds + edge ≥ 2pp.",
            vi: "Không có live edge ≥ 2pp. Cần có trận đang live + odds live + edge đủ lớn.",
            th: "ไม่มีการเดิมพันค่าในเวลาจริง",
            zh: "暂无实时价值盘",
            ko: "현재 라이브 가치 베팅 없음",
          })}
        </div>
      ) : (
        <section className="space-y-3">
          {rows.map((r) => {
            const sideLabel =
              r.best_edge_outcome === "H" ? r.home_short
              : r.best_edge_outcome === "A" ? r.away_short
              : "Draw";
            return (
              <Link
                key={r.match_id}
                href={`/match/${r.match_id}`}
                className="card block hover:border-neon transition-colors"
              >
                <div className="flex flex-wrap items-baseline gap-3 justify-between">
                  <span className="font-display text-lg">
                    {r.home_short} <span className="text-neon tabular-nums">{r.home_goals}-{r.away_goals}</span> {r.away_short}
                  </span>
                  <span className="font-mono text-xs text-error">
                    LIVE {r.minute}'
                  </span>
                  <span className="font-mono text-[10px] text-muted">
                    {r.league_code}
                  </span>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-3 font-mono text-sm">
                  <span className="inline-flex items-center gap-2 rounded-full bg-neon/15 px-3 py-1 text-neon">
                    ✓ {sideLabel} · {Math.round(
                      r.best_edge_outcome === "H" ? r.p_home_win * 100
                      : r.best_edge_outcome === "A" ? r.p_away_win * 100
                      : r.p_draw * 100,
                    )}%
                  </span>
                  <span className="text-muted">@ {r.best_edge_odds.toFixed(2)} · {r.best_edge_source?.replace(/^(af:|odds-api:)/, "")}</span>
                  <span className="text-neon font-semibold ml-auto">+{r.best_edge_pp.toFixed(1)}% edge</span>
                </div>
                <div className="mt-2 flex items-stretch font-mono text-[10px]">
                  <div className="bg-secondary/20 py-1 text-center" style={{ width: `${r.p_home_win * 100}%` }}>
                    {Math.round(r.p_home_win * 100)}%
                  </div>
                  <div className="bg-muted/20 py-1 text-center" style={{ width: `${r.p_draw * 100}%` }}>
                    {Math.round(r.p_draw * 100)}%
                  </div>
                  <div className="bg-secondary/20 py-1 text-center" style={{ width: `${r.p_away_win * 100}%` }}>
                    {Math.round(r.p_away_win * 100)}%
                  </div>
                </div>
              </Link>
            );
          })}
        </section>
      )}

      <p className="font-mono text-[11px] uppercase tracking-wide text-muted">
        • Edge = p_live × best_odds − 1 · threshold 2pp · page auto-refreshes every 20s.
      </p>
    </main>
  );
}
