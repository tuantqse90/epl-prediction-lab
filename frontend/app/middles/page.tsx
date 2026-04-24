import Link from "next/link";

import { getLang } from "@/lib/i18n-server";
import { tLang } from "@/lib/i18n-fallback";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type MiddleRow = {
  match_id: number;
  league_code: string | null;
  kickoff_time: string;
  home_short: string;
  away_short: string;
  middle_low: number;
  middle_high: number;
  source_over: string;
  source_under: string;
  odds_over: number;
  odds_under: number;
  middle_pnl: number;
  miss_pnl_low: number;
  miss_pnl_high: number;
};

type Response = { checked: number; opportunities: MiddleRow[] };

async function fetchData(): Promise<Response | null> {
  try {
    const res = await fetch(`${BASE}/api/stats/middles?min_middle_pnl=0.3`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) return null;
    return (await res.json()) as Response;
  } catch {
    return null;
  }
}

export default async function MiddlesPage() {
  const lang = await getLang();
  const data = await fetchData();
  if (!data) return <main className="mx-auto max-w-3xl px-6 py-12"><div className="card text-error">—</div></main>;

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
      </Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">sharp · O/U middles</p>
        <h1 className="headline-section">
          {tLang(lang, {
            en: "O/U middles — exact scoreline cashes both sides",
            vi: "O/U middles — tỷ số chính xác ăn cả 2 bên",
            th: "O/U middles",
            zh: "大小球夹心",
            ko: "O/U 미들",
          })}
        </h1>
        <p className="max-w-2xl text-secondary">
          {tLang(lang, {
            en: `Scanned ${data.checked} fixtures. A middle is Over X @ book A + Under Y @ book B where X < Y. If the total lands STRICTLY between, both bets win. Outside the window, exactly one wins.`,
            vi: `Đã quét ${data.checked} trận. Middle = Over X nhà A + Under Y nhà B, X < Y. Nếu tổng bàn nằm giữa, ăn cả. Ngoài window, 1 bên ăn 1 bên thua.`,
            th: `สแกน ${data.checked} แมตช์`,
            zh: `扫描 ${data.checked} 场`,
            ko: `${data.checked}개 경기 스캔`,
          })}
        </p>
      </header>

      {data.opportunities.length === 0 ? (
        <div className="card text-muted">
          {tLang(lang, {
            en: "No attractive middles right now. OU books tend to track each other tightly.",
            vi: "Không có middle hấp dẫn.",
            th: "ไม่มี middle",
            zh: "无可用 middle",
            ko: "미들 없음",
          })}
        </div>
      ) : (
        <section className="card p-0 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-[10px] uppercase tracking-wide text-muted">
              <tr className="border-b border-border">
                <th className="px-3 py-3 text-left">Match</th>
                <th className="px-3 py-3 text-center">Middle band</th>
                <th className="px-3 py-3 text-left">Over @</th>
                <th className="px-3 py-3 text-left">Under @</th>
                <th className="px-3 py-3 text-right">Middle P&amp;L</th>
                <th className="px-3 py-3 text-right">Miss low</th>
                <th className="px-3 py-3 text-right">Miss high</th>
              </tr>
            </thead>
            <tbody>
              {data.opportunities.slice(0, 30).map((m, i) => (
                <tr key={`${m.match_id}-${i}`} className="border-t border-border-muted">
                  <td className="px-3 py-2">
                    <Link href={`/match/${m.match_id}`} className="hover:text-neon">
                      {m.home_short} vs {m.away_short}
                    </Link>
                  </td>
                  <td className="px-3 py-2 text-center font-mono tabular-nums">
                    {m.middle_low} → {m.middle_high}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">
                    {m.source_over.replace(/^(af:|odds-api:)/, "")} <span className="text-muted">@{m.odds_over.toFixed(2)}</span>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">
                    {m.source_under.replace(/^(af:|odds-api:)/, "")} <span className="text-muted">@{m.odds_under.toFixed(2)}</span>
                  </td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums text-neon">
                    +{m.middle_pnl.toFixed(2)}u
                  </td>
                  <td className={`px-3 py-2 text-right font-mono tabular-nums ${m.miss_pnl_low < 0 ? "text-error" : "text-neon"}`}>
                    {m.miss_pnl_low >= 0 ? "+" : ""}{m.miss_pnl_low.toFixed(2)}u
                  </td>
                  <td className={`px-3 py-2 text-right font-mono tabular-nums ${m.miss_pnl_high < 0 ? "text-error" : "text-neon"}`}>
                    {m.miss_pnl_high >= 0 ? "+" : ""}{m.miss_pnl_high.toFixed(2)}u
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <section className="font-mono text-[11px] uppercase tracking-wide text-muted space-y-1">
        <p>• P&L values assume 1u on each side, 2u total staked.</p>
        <p>• Middle profit positive ⇒ total must land in the band for max gain.</p>
      </section>
    </main>
  );
}
