import Link from "next/link";

import { getLang } from "@/lib/i18n-server";
import { tLang } from "@/lib/i18n-fallback";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type ArbRow = {
  match_id: number;
  league_code: string | null;
  kickoff_time: string;
  home_short: string;
  away_short: string;
  profit_percent: number;
  home_source: string;
  draw_source: string;
  away_source: string;
  home_odds: number;
  draw_odds: number;
  away_odds: number;
  stake_home: number;
  stake_draw: number;
  stake_away: number;
};

type Response = { checked: number; opportunities: ArbRow[] };

async function fetchData(): Promise<Response | null> {
  try {
    const res = await fetch(
      `${BASE}/api/stats/arbs?horizon_days=14&min_profit_pct=0.2`,
      { next: { revalidate: 300 } },
    );
    if (!res.ok) return null;
    return (await res.json()) as Response;
  } catch {
    return null;
  }
}

function cleanSrc(s: string): string {
  return s.replace(/^(af:|odds-api:)/, "");
}

export default async function ArbsPage() {
  const lang = await getLang();
  const data = await fetchData();
  if (!data) return <main className="mx-auto max-w-3xl px-6 py-12"><div className="card text-error">—</div></main>;

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
      </Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">sharp · arbitrage</p>
        <h1 className="headline-section">
          {tLang(lang, {
            en: "Arbitrage opportunities — guaranteed profit across books",
            vi: "Cơ hội arbitrage — lãi chắc giữa các nhà cái",
            th: "โอกาส arbitrage",
            zh: "跨盘套利机会",
            ko: "무위험 차익거래 기회",
          })}
        </h1>
        <p className="max-w-2xl text-secondary">
          {tLang(lang, {
            en: `Scanned ${data.checked} upcoming fixtures. When Σ(1/best_odds_per_outcome) < 1 across books, staking proportionally yields a guaranteed return. Stake fractions below assume bankroll=1.`,
            vi: `Đã quét ${data.checked} trận. Khi Σ(1/best_odds) < 1 giữa các nhà cái, stake theo tỷ lệ ra lợi nhuận chắc chắn. Tỷ lệ stake dưới giả định bankroll=1.`,
            th: `สแกน ${data.checked} แมตช์ที่จะมาถึง`,
            zh: `扫描了 ${data.checked} 场即将开始的比赛`,
            ko: `다가오는 ${data.checked}개 경기 스캔`,
          })}
        </p>
      </header>

      {data.opportunities.length === 0 ? (
        <div className="card text-muted">
          {tLang(lang, {
            en: "No arb opportunities ≥ 0.2% profit right now. The 67 stored books are pretty efficient.",
            vi: "Không có cơ hội arb ≥ 0.2%. 67 nhà cái đang hiệu quả.",
            th: "ไม่มีโอกาส arb ตอนนี้",
            zh: "目前没有套利机会",
            ko: "현재 차익거래 기회 없음",
          })}
        </div>
      ) : (
        <section className="space-y-4">
          {data.opportunities.map((a) => (
            <div key={a.match_id} className="card space-y-3">
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <Link href={`/match/${a.match_id}`} className="font-display text-lg hover:text-neon">
                  {a.home_short} vs {a.away_short}
                </Link>
                <span className="font-mono text-[10px] text-muted">
                  {a.league_code} · {new Date(a.kickoff_time).toISOString().slice(5, 16).replace("T", " ")}
                </span>
                <span className="rounded-full bg-neon/15 px-3 py-0.5 font-mono text-sm text-neon">
                  +{a.profit_percent.toFixed(2)}% profit
                </span>
              </div>
              <table className="w-full text-xs font-mono">
                <thead className="text-[10px] uppercase tracking-wide text-muted">
                  <tr className="border-b border-border">
                    <th className="py-2 pr-3 text-left">Side</th>
                    <th className="py-2 pr-3 text-left">Book</th>
                    <th className="py-2 pr-3 text-right">Odds</th>
                    <th className="py-2 pr-3 text-right">Stake %</th>
                    <th className="py-2 pr-3 text-right">Returns</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-t border-border-muted">
                    <td className="py-1.5 pr-3">{a.home_short}</td>
                    <td className="py-1.5 pr-3 text-secondary">{cleanSrc(a.home_source)}</td>
                    <td className="py-1.5 pr-3 text-right tabular-nums">{a.home_odds.toFixed(2)}</td>
                    <td className="py-1.5 pr-3 text-right tabular-nums">{(a.stake_home * 100).toFixed(1)}%</td>
                    <td className="py-1.5 pr-3 text-right tabular-nums text-neon">
                      {(a.stake_home * a.home_odds * 100).toFixed(2)}
                    </td>
                  </tr>
                  <tr className="border-t border-border-muted">
                    <td className="py-1.5 pr-3">Draw</td>
                    <td className="py-1.5 pr-3 text-secondary">{cleanSrc(a.draw_source)}</td>
                    <td className="py-1.5 pr-3 text-right tabular-nums">{a.draw_odds.toFixed(2)}</td>
                    <td className="py-1.5 pr-3 text-right tabular-nums">{(a.stake_draw * 100).toFixed(1)}%</td>
                    <td className="py-1.5 pr-3 text-right tabular-nums text-neon">
                      {(a.stake_draw * a.draw_odds * 100).toFixed(2)}
                    </td>
                  </tr>
                  <tr className="border-t border-border-muted">
                    <td className="py-1.5 pr-3">{a.away_short}</td>
                    <td className="py-1.5 pr-3 text-secondary">{cleanSrc(a.away_source)}</td>
                    <td className="py-1.5 pr-3 text-right tabular-nums">{a.away_odds.toFixed(2)}</td>
                    <td className="py-1.5 pr-3 text-right tabular-nums">{(a.stake_away * 100).toFixed(1)}%</td>
                    <td className="py-1.5 pr-3 text-right tabular-nums text-neon">
                      {(a.stake_away * a.away_odds * 100).toFixed(2)}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          ))}
        </section>
      )}

      <section className="font-mono text-[11px] uppercase tracking-wide text-muted space-y-1">
        <p>• Stakes sum to 100% of bankroll; every outcome yields the same return.</p>
        <p>• Odds cached ~5 min. Books may limit or void arb-style betting.</p>
        <p>• This is an analytics surface, not a recommendation.</p>
      </section>
    </main>
  );
}
