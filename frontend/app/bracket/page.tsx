"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useLang } from "@/lib/i18n-client";
import { tLang } from "@/lib/i18n-fallback";

type TeamOdds = {
  team_slug: string;
  team_short: string;
  p_semi_win: number;
  p_final_win: number;
  p_lift_trophy: number;
};

type Response = {
  competition: string;
  n_simulations: number;
  teams: TeamOdds[];
};

type Comp = "UCL" | "UEL";

export default function BracketPage() {
  const lang = useLang();
  const [comp, setComp] = useState<Comp>("UCL");
  const [data, setData] = useState<Response | null>(null);

  useEffect(() => {
    setData(null);
    fetch(`/api/stats/bracket?competition=${comp}&n=5000`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setData(d));
  }, [comp]);

  const pct = (x: number) =>
    x >= 0.995 ? ">99%" : x <= 0.005 ? "<1%" : `${(x * 100).toFixed(1)}%`;

  return (
    <main className="mx-auto max-w-4xl px-6 py-12 space-y-8">
      <Link href="/europe" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Europe", vi: "← Europe", th: "← Europe", zh: "← Europe", ko: "← Europe" })}
      </Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">europe · bracket monte carlo</p>
        <h1 className="headline-section">
          {tLang(lang, {
            en: "Who lifts the trophy?",
            vi: "Ai nâng cúp?",
            th: "ใครจะยกถ้วย?",
            zh: "谁将捧杯?",
            ko: "누가 트로피를 들까?",
          })}
        </h1>
        <p className="max-w-2xl text-secondary">
          {tLang(lang, {
            en: "Monte Carlo through the remaining knockout rounds. Each 2-leg tie simulated from per-match Poisson λ; penalty shootouts resolved 50/50. Final currently coin-flip (no λ until semi winners known).",
            vi: "Monte Carlo qua các vòng knockout còn lại. Mỗi lượt 2 chân jim từ λ Poisson; penalty 50/50. Chung kết hiện coin-flip (chưa có λ đến khi biết đội vào).",
            th: "Monte Carlo ผ่านรอบน็อคเอาท์",
            zh: "蒙特卡洛模拟剩余淘汰赛",
            ko: "남은 녹아웃 몬테카를로",
          })}
        </p>
      </header>

      <nav className="flex gap-2">
        {(["UCL", "UEL"] as Comp[]).map((c) => (
          <button
            key={c}
            onClick={() => setComp(c)}
            className={`rounded-full px-3 py-1 font-mono text-xs uppercase tracking-wide border ${
              comp === c
                ? "border-neon bg-neon text-on-neon"
                : "border-border text-secondary hover:border-neon hover:text-neon"
            }`}
          >
            {c === "UCL" ? "⭐ Champions League" : "🏆 Europa League"}
          </button>
        ))}
      </nav>

      {!data ? (
        <div className="card text-muted">Loading…</div>
      ) : data.teams.length === 0 ? (
        <div className="card text-muted">
          {tLang(lang, {
            en: "No upcoming 2-leg ties found for this competition. Run the European ingest + predict_upcoming.",
            vi: "Chưa có lượt 2-chân nào sắp diễn ra.",
            th: "ไม่มีคู่รอบน็อคเอาท์",
            zh: "无即将进行的淘汰赛",
            ko: "예정된 녹아웃 경기 없음",
          })}
        </div>
      ) : (
        <section className="card p-0 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-[10px] uppercase tracking-wide text-muted">
              <tr className="border-b border-border">
                <th className="px-3 py-3 text-left">
                  {tLang(lang, { en: "Team", vi: "Đội", th: "ทีม", zh: "球队", ko: "팀" })}
                </th>
                <th className="px-3 py-3 text-right">
                  {tLang(lang, { en: "P(advance)", vi: "P(vào CK)", th: "P(เข้าถึง)", zh: "P(晋级)", ko: "P(진출)" })}
                </th>
                <th className="px-3 py-3 text-right">
                  {tLang(lang, { en: "P(win final | advance)", vi: "P(thắng CK | vào)", th: "P(ชนะ CK)", zh: "P(夺冠)", ko: "P(결승 승)" })}
                </th>
                <th className="px-3 py-3 text-right text-neon">
                  {tLang(lang, { en: "P(lift trophy)", vi: "P(vô địch)", th: "P(แชมป์)", zh: "P(捧杯)", ko: "P(우승)" })}
                </th>
              </tr>
            </thead>
            <tbody>
              {data.teams.map((t) => (
                <tr key={t.team_slug} className="border-t border-border-muted">
                  <td className="px-3 py-2 font-display uppercase tracking-tighter">{t.team_short}</td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">{pct(Number(t.p_semi_win))}</td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">{pct(t.p_final_win)}</td>
                  <td className={`px-3 py-2 text-right font-mono tabular-nums ${t.p_lift_trophy > 0.3 ? "text-neon" : ""}`}>
                    {pct(t.p_lift_trophy)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <section className="font-mono text-[11px] uppercase tracking-wide text-muted space-y-1">
        <p>• {data?.n_simulations.toLocaleString() ?? "—"} simulations · seed 42 · stable across refreshes</p>
        <p>• P(lift trophy) = P(advance from semi) × P(win final) — final is neutral 50/50 until semi winners known.</p>
      </section>
    </main>
  );
}
