import Link from "next/link";

import TeamLogo from "@/components/TeamLogo";
import { getLang, getLeagueSlug } from "@/lib/i18n-server";
import { tLang } from "@/lib/i18n-fallback";
import { getLeague, type LeagueSlug } from "@/lib/leagues";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type Team = {
  rank: number;
  slug: string;
  short_name: string;
  name: string;
  elo: number;
  elo_prior: number | null;
  delta: number | null;
  rank_prior: number | null;
  rank_delta: number | null;
};

type Mover = { slug: string; short_name: string; delta: number };

type Response = {
  league_code: string;
  season: string;
  as_of: string;
  snapshot_prior: string;
  teams: Team[];
  top_risers: Mover[];
  top_fallers: Mover[];
};

const LEAGUE_CODE: Record<LeagueSlug, string> = {
  all: "ENG-Premier League",
  epl: "ENG-Premier League",
  laliga: "ESP-La Liga",
  seriea: "ITA-Serie A",
  bundesliga: "GER-Bundesliga",
  ligue1: "FRA-Ligue 1",
};

async function fetchData(leagueCode: string): Promise<Response | null> {
  const qs = new URLSearchParams({ league: leagueCode, season: "2025-26", lookback_days: "7" });
  try {
    const res = await fetch(`${BASE}/api/stats/power-rankings?${qs}`, { next: { revalidate: 600 } });
    if (!res.ok) return null;
    return (await res.json()) as Response;
  } catch {
    return null;
  }
}

function RankArrow({ delta }: { delta: number | null }) {
  if (delta == null) return <span className="text-muted">•</span>;
  if (delta > 0) return <span className="text-neon">▲ {delta}</span>;
  if (delta < 0) return <span className="text-error">▼ {Math.abs(delta)}</span>;
  return <span className="text-muted">—</span>;
}

export default async function PowerRankingsPage() {
  const lang = await getLang();
  const leagueSlug = (await getLeagueSlug()) as LeagueSlug;
  const leagueCode = LEAGUE_CODE[leagueSlug] ?? "ENG-Premier League";
  const leagueInfo = getLeague(leagueSlug === "all" ? "epl" : leagueSlug);
  const data = await fetchData(leagueCode);

  if (!data || data.teams.length === 0) {
    return <main className="mx-auto max-w-3xl px-6 py-12"><div className="card text-muted">—</div></main>;
  }

  const leagueLabel = lang === "vi" ? leagueInfo.name_vi : leagueInfo.name_en;

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
            en: "Power rankings — pure elo",
            vi: "Power rankings — elo thuần",
            th: "Power rankings — elo ล้วน",
            zh: "实力榜 — 纯 Elo",
            ko: "파워 랭킹 — 순수 Elo",
          })}
        </h1>
        <p className="max-w-2xl text-secondary">
          {tLang(lang, {
            en: "Goal-difference-weighted Elo rebuilt from the match log every 10 min. Points, GD, league standing ignored — only match results. Arrows show week-over-week rank change.",
            vi: "Elo trọng số hiệu số bàn, tính lại từ log trận mỗi 10 phút. Bỏ qua điểm, GD, vị trí giải — chỉ kết quả trận. Mũi tên = thay đổi rank 7 ngày qua.",
            th: "Elo แบบ goal-diff weighted สร้างใหม่จาก match log ทุก 10 นาที",
            zh: "按净胜球加权的 Elo,每 10 分钟从比赛日志重建",
            ko: "득실 가중 Elo, 매 10분 매치 로그에서 재생성",
          })}
        </p>
      </header>

      {/* Risers / fallers strip */}
      {(data.top_risers.length > 0 || data.top_fallers.length > 0) && (
        <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="card space-y-2">
            <p className="font-mono text-[10px] uppercase tracking-wide text-neon">
              {tLang(lang, { en: "Top risers (7d)", vi: "Lên mạnh nhất (7 ngày)", th: "เพิ่มมากสุด (7d)", zh: "上升最多 (7d)", ko: "급상승 (7d)" })}
            </p>
            <ul className="space-y-1">
              {data.top_risers.map((m) => (
                <li key={m.slug} className="flex items-center justify-between">
                  <span className="font-display uppercase tracking-tighter">{m.short_name}</span>
                  <span className="font-mono text-neon">+{m.delta.toFixed(1)}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="card space-y-2">
            <p className="font-mono text-[10px] uppercase tracking-wide text-error">
              {tLang(lang, { en: "Top fallers (7d)", vi: "Tụt mạnh nhất (7 ngày)", th: "ลดมากสุด (7d)", zh: "下降最多 (7d)", ko: "급하락 (7d)" })}
            </p>
            <ul className="space-y-1">
              {data.top_fallers.length > 0 ? data.top_fallers.map((m) => (
                <li key={m.slug} className="flex items-center justify-between">
                  <span className="font-display uppercase tracking-tighter">{m.short_name}</span>
                  <span className="font-mono text-error">{m.delta.toFixed(1)}</span>
                </li>
              )) : <li className="text-muted text-sm">—</li>}
            </ul>
          </div>
        </section>
      )}

      {/* Full table */}
      <section className="card p-0 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-[10px] uppercase tracking-wide text-muted">
            <tr className="border-b border-border">
              <th className="px-3 py-3 text-left">#</th>
              <th className="px-3 py-3 text-left">
                {tLang(lang, { en: "Team", vi: "Đội", th: "ทีม", zh: "球队", ko: "팀" })}
              </th>
              <th className="px-3 py-3 text-right">Elo</th>
              <th className="px-3 py-3 text-right">
                {tLang(lang, { en: "7d Δ", vi: "Δ 7 ngày", th: "Δ 7d", zh: "7d 变", ko: "7일 변" })}
              </th>
              <th className="px-3 py-3 text-right">
                {tLang(lang, { en: "Rank Δ", vi: "Δ Rank", th: "Δ อันดับ", zh: "排名变", ko: "순위 변" })}
              </th>
            </tr>
          </thead>
          <tbody>
            {data.teams.map((t) => (
              <tr key={t.slug} className="border-t border-border-muted">
                <td className="px-3 py-2 font-mono tabular-nums text-muted">{t.rank}</td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <TeamLogo slug={t.slug} name={t.name} size={20} />
                    <span className="font-display uppercase tracking-tighter">{t.short_name}</span>
                  </div>
                </td>
                <td className="px-3 py-2 text-right font-mono tabular-nums">{t.elo.toFixed(0)}</td>
                <td
                  className={`px-3 py-2 text-right font-mono tabular-nums ${
                    t.delta == null ? "text-muted" : t.delta > 0 ? "text-neon" : t.delta < 0 ? "text-error" : ""
                  }`}
                >
                  {t.delta == null ? "—" : `${t.delta > 0 ? "+" : ""}${t.delta.toFixed(1)}`}
                </td>
                <td className="px-3 py-2 text-right font-mono tabular-nums">
                  <RankArrow delta={t.rank_delta} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="font-mono text-[11px] uppercase tracking-wide text-muted space-y-1">
        <p>• Elo start = 1500; home-field advantage 70 pts; K = 20 × goal-diff multiplier</p>
        <p>• Snapshot prior: {new Date(data.snapshot_prior).toISOString().slice(0, 10)}</p>
        <p>• As of: {new Date(data.as_of).toISOString().slice(0, 16).replace("T", " ")} UTC</p>
      </section>
    </main>
  );
}
