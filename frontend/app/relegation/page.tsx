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
};

type Response = {
  league_code: string;
  season: string;
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

export default async function RelegationPage() {
  const lang = await getLang();
  const leagueSlug = (await getLeagueSlug()) as LeagueSlug;
  const leagueCode = LEAGUE_CODE_BY_SLUG[leagueSlug] ?? "ENG-Premier League";
  const leagueInfo = getLeague(leagueSlug === "all" ? "epl" : leagueSlug);
  const data = await fetchData(leagueCode);

  if (!data || data.teams.length === 0) {
    return <main className="mx-auto max-w-3xl px-6 py-12"><div className="card text-muted">—</div></main>;
  }

  const leagueLabel = lang === "vi" ? leagueInfo.name_vi : leagueInfo.name_en;
  // Sort by P(relegate) desc, highlight top 6
  const sorted = [...data.teams].sort((a, b) => b.p_relegate - a.p_relegate);
  const atRisk = sorted.filter((t) => t.p_relegate > 0.05);

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-10">
      <Link href="/title-race" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Title race", vi: "← Đường đua vô địch", th: "← ศึกชิงแชมป์", zh: "← 冠军争夺", ko: "← 우승 경쟁" })}
      </Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">
          {leagueInfo.emoji} {leagueLabel} · {data.season}
        </p>
        <h1 className="headline-section">
          {tLang(lang, {
            en: "Relegation battle — who survives?",
            vi: "Đường đua trụ hạng — ai sống sót?",
            th: "ศึกหนีตกชั้น — ใครจะรอด?",
            zh: "保级大战 — 谁能存活?",
            ko: "강등 경쟁 — 누가 살아남는가?",
          })}
        </h1>
        <p className="max-w-2xl text-secondary">
          {tLang(lang, {
            en: `Same simulator as /title-race, bottom 3 view. ${data.n_simulations.toLocaleString()} sims · ${data.remaining_fixtures} fixtures remaining.`,
            vi: `Cùng simulator với /title-race, view bottom 3. ${data.n_simulations.toLocaleString()} sim · còn ${data.remaining_fixtures} trận.`,
            th: `ใช้ซิมเดียวกับ /title-race มุมมอง 3 อันดับสุดท้าย`,
            zh: `与 /title-race 同一模拟器,视角为末三名`,
            ko: `/title-race와 동일한 시뮬레이터, 하위 3위 시점`,
          })}
        </p>
      </header>

      <section className="card p-0 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-[10px] uppercase tracking-wide text-muted">
            <tr className="border-b border-border">
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
              <th className="px-3 py-3 text-right text-error">P(relegate)</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((t) => {
              const danger = t.p_relegate;
              const color =
                danger > 0.5 ? "text-error"
                : danger > 0.2 ? "text-warning"
                : danger > 0.05 ? "" : "text-muted";
              return (
                <tr key={t.slug} className="border-t border-border-muted">
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
                  <td className={`px-3 py-2 text-right font-mono tabular-nums ${color}`}>{pct(danger)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      {atRisk.length > 0 && (
        <section className="card">
          <p className="font-mono text-[10px] uppercase tracking-wide text-error">
            {tLang(lang, { en: "At risk", vi: "Nguy hiểm", th: "เสี่ยง", zh: "有风险", ko: "위험" })}
          </p>
          <p className="mt-2 text-secondary">
            {tLang(lang, {
              en: `${atRisk.length} team${atRisk.length === 1 ? "" : "s"} have >5% relegation risk. Top risk: ${sorted[0].short_name} at ${pct(sorted[0].p_relegate)}.`,
              vi: `${atRisk.length} đội có nguy cơ xuống hạng >5%. Cao nhất: ${sorted[0].short_name} ${pct(sorted[0].p_relegate)}.`,
              th: `${atRisk.length} ทีมมีความเสี่ยงตกชั้น >5%`,
              zh: `${atRisk.length} 支球队有 >5% 降级风险`,
              ko: `${atRisk.length}개 팀이 5% 이상 강등 위험`,
            })}
          </p>
        </section>
      )}
    </main>
  );
}
