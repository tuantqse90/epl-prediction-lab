import Link from "next/link";

import { getLang, getLeagueSlug } from "@/lib/i18n-server";
import { tLang } from "@/lib/i18n-fallback";
import { getLeague, type LeagueSlug } from "@/lib/leagues";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type P = {
  rank: number;
  player_name: string;
  team_slug: string;
  team_short: string;
  league_code: string;
  goals: number;
  xg: number;
  games: number;
  team_remaining: number;
  xg_per_match: number;
  projected: number;
  gap_to_leader: number;
  photo_url: string | null;
};

type Response = { league_code: string; season: string; players: P[] };

const LEAGUE_CODE: Record<LeagueSlug, string> = {
  all: "ENG-Premier League",
  epl: "ENG-Premier League",
  laliga: "ESP-La Liga",
  seriea: "ITA-Serie A",
  bundesliga: "GER-Bundesliga",
  ligue1: "FRA-Ligue 1",
};

const TROPHY_NAME: Record<string, { en: string; vi: string }> = {
  "ENG-Premier League": { en: "Golden Boot", vi: "Chiếc giày vàng EPL" },
  "ESP-La Liga": { en: "Pichichi", vi: "Pichichi" },
  "ITA-Serie A": { en: "Capocannoniere", vi: "Capocannoniere" },
  "GER-Bundesliga": { en: "Torschützenkönig", vi: "Vua phá lưới Bundesliga" },
  "FRA-Ligue 1": { en: "Soulier d'Or", vi: "Chiếc giày vàng Ligue 1" },
};

async function fetchData(leagueCode: string): Promise<Response | null> {
  const qs = new URLSearchParams({ league: leagueCode, season: "2025-26", limit: "20" });
  try {
    const res = await fetch(`${BASE}/api/stats/top-scorer-race?${qs}`, { next: { revalidate: 600 } });
    if (!res.ok) return null;
    return (await res.json()) as Response;
  } catch {
    return null;
  }
}

export default async function ScorersRacePage() {
  const lang = await getLang();
  const leagueSlug = (await getLeagueSlug()) as LeagueSlug;
  const leagueCode = LEAGUE_CODE[leagueSlug] ?? "ENG-Premier League";
  const leagueInfo = getLeague(leagueSlug === "all" ? "epl" : leagueSlug);
  const data = await fetchData(leagueCode);
  const trophyName = tLang(lang, {
    en: TROPHY_NAME[leagueCode]?.en ?? "Top scorer",
    vi: TROPHY_NAME[leagueCode]?.vi ?? "Vua phá lưới",
    th: TROPHY_NAME[leagueCode]?.en ?? "",
    zh: TROPHY_NAME[leagueCode]?.en ?? "",
    ko: TROPHY_NAME[leagueCode]?.en ?? "",
  });

  if (!data || data.players.length === 0) {
    return <main className="mx-auto max-w-3xl px-6 py-12"><div className="card text-muted">—</div></main>;
  }

  const leagueLabel = lang === "vi" ? leagueInfo.name_vi : leagueInfo.name_en;
  const leader = data.players[0];

  return (
    <main className="mx-auto max-w-4xl px-6 py-12 space-y-10">
      <Link href="/scorers" className="btn-ghost text-sm">
        {tLang(lang, { en: "← All scorers", vi: "← Tất cả vua phá lưới", th: "← รายชื่อทั้งหมด", zh: "← 所有射手", ko: "← 전체 득점왕" })}
      </Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">
          {leagueInfo.emoji} {leagueLabel} · {data.season}
        </p>
        <h1 className="headline-section">
          {tLang(lang, {
            en: `${trophyName} projection`,
            vi: `Dự đoán ${trophyName}`,
            th: `พยากรณ์ ${trophyName}`,
            zh: `${trophyName} 预测`,
            ko: `${trophyName} 예측`,
          })}
        </h1>
        <p className="max-w-2xl text-secondary">
          {tLang(lang, {
            en: "Projected end-of-season goals = current goals + (xG/match × team fixtures remaining). Naive but directional — scoring rate is noisier than xG variance accounts for.",
            vi: "Dự đoán bàn cuối mùa = hiện tại + (xG/trận × số trận còn lại của đội). Đơn giản nhưng mang tính xu hướng — tỷ lệ ghi bàn biến động cao hơn xG cho phép.",
            th: "ประตูปลายฤดู = ปัจจุบัน + (xG/แมตช์ × แมตช์ที่เหลือ)",
            zh: "赛季末进球预测 = 当前进球 + (xG/场 × 剩余场次)",
            ko: "시즌말 골 예상 = 현재 골 + (xG/경기 × 남은 경기)",
          })}
        </p>
      </header>

      {/* Leader card */}
      <section className="card flex items-center justify-between gap-6 flex-wrap">
        <div className="flex items-center gap-4">
          {leader.photo_url ? (
            <img
              src={leader.photo_url}
              alt={leader.player_name}
              className="w-16 h-16 rounded-full object-cover bg-raised"
            />
          ) : (
            <div className="w-16 h-16 rounded-full bg-raised grid place-items-center font-mono text-muted">
              ?
            </div>
          )}
          <div>
            <p className="font-mono text-[10px] uppercase tracking-wide text-neon">
              {tLang(lang, { en: "Most likely winner", vi: "Khả năng đoạt cao nhất", th: "ผู้นำที่น่าจะเป็น", zh: "最可能获得者", ko: "가장 유력한 수상" })}
            </p>
            <p className="font-display text-2xl font-bold tracking-tighter">
              {leader.player_name}
            </p>
            <p className="font-mono text-xs text-muted">{leader.team_short}</p>
          </div>
        </div>
        <div className="flex gap-6 font-mono">
          <div>
            <p className="label">{tLang(lang, { en: "Goals", vi: "Bàn", th: "ประตู", zh: "进球", ko: "골" })}</p>
            <p className="stat">{leader.goals}</p>
          </div>
          <div>
            <p className="label">{tLang(lang, { en: "Projected", vi: "Dự đoán", th: "พยากรณ์", zh: "预计", ko: "예상" })}</p>
            <p className="stat text-neon">{leader.projected.toFixed(1)}</p>
          </div>
        </div>
      </section>

      {/* Full table */}
      <section className="card p-0 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-[10px] uppercase tracking-wide text-muted">
            <tr className="border-b border-border">
              <th className="px-3 py-3 text-left">#</th>
              <th className="px-3 py-3 text-left">
                {tLang(lang, { en: "Player", vi: "Cầu thủ", th: "ผู้เล่น", zh: "球员", ko: "선수" })}
              </th>
              <th className="px-3 py-3 text-left">
                {tLang(lang, { en: "Team", vi: "CLB", th: "ทีม", zh: "球队", ko: "팀" })}
              </th>
              <th className="px-3 py-3 text-right">
                {tLang(lang, { en: "G", vi: "Bàn", th: "ป", zh: "进", ko: "골" })}
              </th>
              <th className="px-3 py-3 text-right">xG</th>
              <th className="px-3 py-3 text-right">
                {tLang(lang, { en: "Rem", vi: "Còn", th: "เหลือ", zh: "剩", ko: "잔여" })}
              </th>
              <th className="px-3 py-3 text-right text-neon">
                {tLang(lang, { en: "Projected", vi: "Dự đoán", th: "ปลายฤดู", zh: "预计", ko: "예상" })}
              </th>
              <th className="px-3 py-3 text-right">Gap</th>
            </tr>
          </thead>
          <tbody>
            {data.players.map((p) => (
              <tr key={`${p.player_name}-${p.team_slug}`} className="border-t border-border-muted">
                <td className="px-3 py-2 font-mono tabular-nums text-muted">{p.rank}</td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    {p.photo_url ? (
                      <img src={p.photo_url} alt={p.player_name} className="w-6 h-6 rounded-full object-cover" />
                    ) : null}
                    <span className="font-display">{p.player_name}</span>
                  </div>
                </td>
                <td className="px-3 py-2 font-mono text-xs text-muted">{p.team_short}</td>
                <td className="px-3 py-2 text-right font-mono tabular-nums">{p.goals}</td>
                <td className="px-3 py-2 text-right font-mono tabular-nums text-muted">
                  {p.xg.toFixed(1)}
                </td>
                <td className="px-3 py-2 text-right font-mono tabular-nums text-muted">{p.team_remaining}</td>
                <td className="px-3 py-2 text-right font-mono tabular-nums text-neon">
                  {p.projected.toFixed(1)}
                </td>
                <td className={`px-3 py-2 text-right font-mono tabular-nums ${p.gap_to_leader === 0 ? "text-neon" : "text-muted"}`}>
                  {p.gap_to_leader === 0 ? "—" : p.gap_to_leader.toFixed(1)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="font-mono text-[11px] uppercase tracking-wide text-muted space-y-1">
        <p>• projected = goals + (xG/match × team fixtures remaining)</p>
        <p>• gap_to_leader = projected − leader.projected (always ≤ 0 for rank 2+)</p>
        <p>• cache 10 min; data from Understat (xG) + DB scheduled-match count</p>
      </section>
    </main>
  );
}
