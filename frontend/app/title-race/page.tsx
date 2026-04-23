import Link from "next/link";

import TeamLogo from "@/components/TeamLogo";
import { getLang, getLeagueSlug } from "@/lib/i18n-server";
import { tLang } from "@/lib/i18n-fallback";
import { getLeague, type LeagueSlug } from "@/lib/leagues";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type TeamSummary = {
  slug: string;
  short_name: string;
  name: string;
  played: number;
  points: number;
  gd: number;
  gf: number;
  p_champions: number;
  p_top_four: number;
  p_relegate: number;
  mean_points: number;
  position_histogram: number[];
};

type Response = {
  league_code: string;
  season: string;
  n_teams: number;
  n_simulations: number;
  remaining_fixtures: number;
  teams: TeamSummary[];
};

async function fetchData(leagueCode: string): Promise<Response | null> {
  const qs = new URLSearchParams({ league: leagueCode, season: "2025-26", n: "5000" });
  try {
    const res = await fetch(`${BASE}/api/stats/title-race?${qs}`, { next: { revalidate: 600 } });
    if (!res.ok) return null;
    return (await res.json()) as Response;
  } catch {
    return null;
  }
}

const LEAGUE_CODE_BY_SLUG: Record<LeagueSlug, string> = {
  all: "ENG-Premier League",
  epl: "ENG-Premier League",
  laliga: "ESP-La Liga",
  seriea: "ITA-Serie A",
  bundesliga: "GER-Bundesliga",
  ligue1: "FRA-Ligue 1",
};

function pct(x: number): string {
  if (x >= 0.99) return ">99%";
  if (x <= 0.005) return "<1%";
  return `${(x * 100).toFixed(1)}%`;
}

function pctSmall(x: number): string {
  if (x >= 0.99) return ">99";
  if (x <= 0.005) return "<1";
  return `${Math.round(x * 100)}`;
}

export default async function TitleRacePage() {
  const lang = await getLang();
  const leagueSlug = (await getLeagueSlug()) as LeagueSlug;
  const leagueCode = LEAGUE_CODE_BY_SLUG[leagueSlug] ?? "ENG-Premier League";
  const leagueInfo = getLeague(leagueSlug === "all" ? "epl" : leagueSlug);
  const data = await fetchData(leagueCode);

  if (!data || data.teams.length === 0) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <div className="card text-muted">
          {tLang(lang, {
            en: "No data yet — check back after matchday.",
            vi: "Chưa có dữ liệu — xem lại sau lượt đấu.",
            th: "ยังไม่มีข้อมูล",
            zh: "暂无数据",
            ko: "데이터 없음",
          })}
        </div>
      </main>
    );
  }

  const leagueLabel = lang === "vi" ? leagueInfo.name_vi : leagueInfo.name_en;
  const leader = data.teams[0];

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-10">
      <Link href="/" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
      </Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">
          {leagueInfo.emoji} {leagueLabel} · {data.season}
        </p>
        <h1 className="headline-section">
          {tLang(lang, {
            en: "Title race — who lifts the trophy?",
            vi: "Đường đua vô địch — ai nâng cúp?",
            th: "ศึกชิงแชมป์ — ใครจะคว้าแชมป์?",
            zh: "冠军争夺战 — 谁将夺冠?",
            ko: "우승 경쟁 — 누가 트로피를 들까?",
          })}
        </h1>
        <p className="max-w-2xl text-secondary">
          {tLang(lang, {
            en: `Monte Carlo — ${data.n_simulations.toLocaleString()} simulations of the remaining ${data.remaining_fixtures} fixtures using per-match Poisson λ from the ensemble. Re-runs every 10 minutes.`,
            vi: `Monte Carlo — ${data.n_simulations.toLocaleString()} lần mô phỏng ${data.remaining_fixtures} trận còn lại, dùng λ Poisson per-trận từ ensemble. Cập nhật mỗi 10 phút.`,
            th: `Monte Carlo ${data.n_simulations.toLocaleString()} รอบของ ${data.remaining_fixtures} แมตช์ที่เหลือ ใช้ λ Poisson`,
            zh: `Monte Carlo ${data.n_simulations.toLocaleString()} 次模拟剩余 ${data.remaining_fixtures} 场比赛,使用 Poisson λ`,
            ko: `Monte Carlo ${data.n_simulations.toLocaleString()}회 시뮬레이션, 남은 ${data.remaining_fixtures}경기`,
          })}
        </p>
      </header>

      {/* Champion card */}
      <section className="card flex items-center justify-between gap-6 flex-wrap">
        <div className="flex items-center gap-4">
          <TeamLogo slug={leader.slug} name={leader.name} size={48} />
          <div>
            <p className="font-mono text-[10px] uppercase tracking-wide text-neon">
              {tLang(lang, { en: "Most likely champion", vi: "Khả năng vô địch cao nhất", th: "แชมป์ที่น่าจะเป็น", zh: "最可能冠军", ko: "가장 유력한 우승" })}
            </p>
            <p className="font-display text-3xl font-bold uppercase tracking-tighter">
              {leader.short_name}
            </p>
          </div>
        </div>
        <div className="flex gap-6 font-mono">
          <div>
            <p className="label">P(title)</p>
            <p className="stat text-neon">{pct(leader.p_champions)}</p>
          </div>
          <div>
            <p className="label">mean pts</p>
            <p className="stat">{leader.mean_points.toFixed(1)}</p>
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
                {tLang(lang, { en: "Team", vi: "Đội", th: "ทีม", zh: "球队", ko: "팀" })}
              </th>
              <th className="px-3 py-3 text-right">
                {tLang(lang, { en: "Pts", vi: "Điểm", th: "แต้ม", zh: "积分", ko: "점수" })}
              </th>
              <th className="px-3 py-3 text-right">GD</th>
              <th className="px-3 py-3 text-right">
                {tLang(lang, { en: "Mean end", vi: "TB cuối mùa", th: "เฉลี่ยปลาย", zh: "终场均分", ko: "시즌말 평균" })}
              </th>
              <th className="px-3 py-3 text-right text-neon">P(title)</th>
              <th className="px-3 py-3 text-right">P(top-4)</th>
              <th className="px-3 py-3 text-right text-error">P(relegate)</th>
            </tr>
          </thead>
          <tbody>
            {data.teams.map((t, i) => (
              <tr key={t.slug} className="border-t border-border-muted">
                <td className="px-3 py-2 font-mono tabular-nums text-muted">{i + 1}</td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <TeamLogo slug={t.slug} name={t.name} size={20} />
                    <span className="font-display uppercase tracking-tighter">{t.short_name}</span>
                  </div>
                </td>
                <td className="px-3 py-2 text-right font-mono tabular-nums">{t.points}</td>
                <td className="px-3 py-2 text-right font-mono tabular-nums">
                  {t.gd > 0 ? `+${t.gd}` : t.gd}
                </td>
                <td className="px-3 py-2 text-right font-mono tabular-nums">{t.mean_points.toFixed(1)}</td>
                <td className={`px-3 py-2 text-right font-mono tabular-nums ${t.p_champions > 0.01 ? "text-neon" : "text-muted"}`}>
                  {pctSmall(t.p_champions)}
                </td>
                <td className={`px-3 py-2 text-right font-mono tabular-nums ${t.p_top_four > 0.25 ? "" : "text-muted"}`}>
                  {pctSmall(t.p_top_four)}
                </td>
                <td className={`px-3 py-2 text-right font-mono tabular-nums ${t.p_relegate > 0.05 ? "text-error" : "text-muted"}`}>
                  {pctSmall(t.p_relegate)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="font-mono text-[11px] uppercase tracking-wide text-muted space-y-1">
        <p>• P(title) = share of sims where team finishes #1</p>
        <p>• P(top-4) = share where team finishes in top {4}; P(relegate) = bottom {3}</p>
        <p>• λ per fixture comes from the ensemble's Poisson + Elo + XGB blend</p>
        <p>
          <Link href="/relegation" className="hover:text-neon">
            {tLang(lang, { en: "Relegation race →", vi: "Đường đua xuống hạng →", th: "ศึกหนีตกชั้น →", zh: "保级战 →", ko: "강등 경쟁 →" })}
          </Link>
        </p>
      </section>
    </main>
  );
}
