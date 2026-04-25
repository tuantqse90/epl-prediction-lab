import type { Metadata } from "next";
import Link from "next/link";

import TeamLogo from "@/components/TeamLogo";
import { getLang, tFor } from "@/lib/i18n-server";
import type { Lang } from "@/lib/i18n";
import { colorFor } from "@/lib/team-colors";
import { leagueByCode } from "@/lib/leagues";
import { alternatesFor } from "@/lib/seo";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Compare teams — head-to-head · predictor.nullshift.sh",
  description: "Side-by-side stats comparison for any two teams in a top-5 season.",
  alternates: alternatesFor("/compare"),
};

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type Stats = {
  played: number; wins: number; draws: number; losses: number;
  points: number; goals_for: number; goals_against: number;
  xg_for: number; xg_against: number;
};
type Scorer = { player_name: string; goals: number; xg: number; assists: number };
type TeamProfile = {
  slug: string; name: string; short_name: string; season: string;
  stats: Stats; form: string[]; top_scorers: Scorer[];
};
type TeamBrief = { slug: string; name: string; short_name: string; league_code: string | null };

async function fetchTeam(slug: string): Promise<TeamProfile | null> {
  try {
    const res = await fetch(`${BASE}/api/teams/${encodeURIComponent(slug)}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

async function fetchAllTeams(): Promise<TeamBrief[]> {
  try {
    const res = await fetch(`${BASE}/api/teams?season=2025-26`, { next: { revalidate: 300 } });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

function copy(lang: Lang) {
  return {
    back: lang === "vi" ? "← Quay lại" : "← Back",
    title: lang === "vi" ? "So sánh 2 đội" : "Compare teams",
    pickerBlurb: lang === "vi"
      ? "Chọn 2 đội để so sánh toàn bộ số liệu mùa này."
      : "Pick any two teams to compare their full-season stats.",
    home: lang === "vi" ? "Đội A" : "Team A",
    away: lang === "vi" ? "Đội B" : "Team B",
    go: lang === "vi" ? "So sánh" : "Compare",
    swap: lang === "vi" ? "Đổi" : "Swap",
    notFound: lang === "vi"
      ? "Một hoặc cả hai đội không tìm thấy. Hãy chọn từ danh sách bên dưới."
      : "One or both teams not found. Pick from the dropdowns below.",
    labels: {
      points: lang === "vi" ? "Điểm" : "Points",
      wins: lang === "vi" ? "Thắng" : "Wins",
      losses: lang === "vi" ? "Thua" : "Losses",
      gf: lang === "vi" ? "Bàn thắng" : "Goals for",
      ga: lang === "vi" ? "Bàn thua" : "Goals against",
      xgf: "xG for",
      xga: "xG against",
      xgd: "xG Δ",
      ppg: lang === "vi" ? "Điểm / trận" : "Points / game",
    },
    form: lang === "vi" ? "Form" : "form",
    topScorers: lang === "vi" ? "Top ghi bàn" : "top scorers",
    noPlayerData: lang === "vi" ? "Chưa có dữ liệu cầu thủ." : "No player data yet.",
  };
}

function pct(x: number, y: number) {
  return y === 0 ? 0 : x / y;
}

function StatRow({
  label, home, away, format = (n: number) => n.toFixed(2), higherIsBetter = true,
}: {
  label: string; home: number; away: number;
  format?: (n: number) => string; higherIsBetter?: boolean;
}) {
  // "Better" only lights up when the numeric gap survives the display
  // rounding. Otherwise a 0.0006 difference showed as 45.09 vs 45.09 with
  // one neon and one muted — looks like a rendering bug when it's just
  // rounding coincidence. Tie on display → both muted.
  const displayTie = format(home) === format(away);
  const homeBetter = !displayTie && (higherIsBetter ? home > away : home < away);
  const awayBetter = !displayTie && (higherIsBetter ? away > home : away < home);
  return (
    <tr className="border-b border-border-muted">
      <td className={`px-3 py-2 text-right tabular-nums font-mono ${homeBetter ? "text-neon" : "text-secondary"}`}>
        {format(home)}
      </td>
      <td className="px-3 py-2 text-center label text-muted">{label}</td>
      <td className={`px-3 py-2 tabular-nums font-mono ${awayBetter ? "text-neon" : "text-secondary"}`}>
        {format(away)}
      </td>
    </tr>
  );
}

function FormDots({ form }: { form: string[] }) {
  return (
    <div className="flex gap-1 justify-center">
      {form.slice(0, 5).map((r, i) => (
        <span
          key={i}
          title={r}
          className={"h-3 w-3 rounded-full " + (r === "W" ? "bg-neon" : r === "D" ? "bg-secondary" : "bg-error")}
        />
      ))}
    </div>
  );
}

function TeamPicker({
  teams, lang, defaultHome, defaultAway,
}: {
  teams: TeamBrief[]; lang: Lang;
  defaultHome?: string; defaultAway?: string;
}) {
  const c = copy(lang);
  // Group teams by league for optgroups — helps user skim a long list.
  const byLeague = new Map<string, TeamBrief[]>();
  for (const t of teams) {
    const key = t.league_code ?? "";
    if (!byLeague.has(key)) byLeague.set(key, []);
    byLeague.get(key)!.push(t);
  }

  const renderOpts = () =>
    Array.from(byLeague.entries()).map(([lc, list]) => {
      const info = leagueByCode(lc);
      const label = info
        ? `${info.emoji} ${lang === "vi" ? info.name_vi : info.name_en}`
        : (lc || "—");
      return (
        <optgroup key={lc} label={label}>
          {list.map((t) => (
            <option key={t.slug} value={t.slug}>{t.name}</option>
          ))}
        </optgroup>
      );
    });

  return (
    <form action="/compare" method="get" className="card space-y-4">
      <p className="text-secondary text-sm">{c.pickerBlurb}</p>
      <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr_auto] gap-3 items-end">
        <label className="block">
          <span className="label">{c.home}</span>
          <select
            name="home"
            defaultValue={defaultHome ?? ""}
            className="w-full mt-1 rounded-full bg-high border border-border px-4 py-2 font-mono text-sm text-primary focus:outline-none focus:border-neon"
            required
          >
            <option value="" disabled>—</option>
            {renderOpts()}
          </select>
        </label>

        <span className="font-mono text-muted text-xs text-center md:self-end md:pb-3">vs</span>

        <label className="block">
          <span className="label">{c.away}</span>
          <select
            name="away"
            defaultValue={defaultAway ?? ""}
            className="w-full mt-1 rounded-full bg-high border border-border px-4 py-2 font-mono text-sm text-primary focus:outline-none focus:border-neon"
            required
          >
            <option value="" disabled>—</option>
            {renderOpts()}
          </select>
        </label>

        <button
          type="submit"
          className="rounded-full border border-neon bg-neon text-on-neon px-5 py-2 font-mono text-xs uppercase tracking-wide"
        >
          {c.go}
        </button>
      </div>
    </form>
  );
}

export default async function ComparePage({
  searchParams,
}: {
  searchParams: Promise<{ home?: string; away?: string }>;
}) {
  const sp = await searchParams;
  const lang = await getLang();
  const t = tFor(lang);
  const c = copy(lang);

  const [teams, home, away] = await Promise.all([
    fetchAllTeams(),
    sp.home ? fetchTeam(sp.home) : Promise.resolve(null),
    sp.away ? fetchTeam(sp.away) : Promise.resolve(null),
  ]);

  const bothLoaded = home && away;
  const invalid = (sp.home || sp.away) && !bothLoaded;

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>

      <header className="space-y-2">
        <h1 className="headline-section">{c.title}</h1>
      </header>

      <TeamPicker
        teams={teams}
        lang={lang}
        defaultHome={sp.home}
        defaultAway={sp.away}
      />

      {invalid && (
        <div className="card text-error">{c.notFound}</div>
      )}

      {bothLoaded && home && away && (
        <>
          <section
            className="relative overflow-hidden rounded-xl p-6 border border-border"
            style={{
              background: `linear-gradient(110deg, ${colorFor(home.slug)}33 0%, transparent 45%, transparent 55%, ${colorFor(away.slug)}33 100%)`,
            }}
          >
            <div className="flex items-center justify-between gap-6">
              <Link href={`/teams/${home.slug}`} className="flex items-center gap-3 min-w-0 hover:text-neon">
                <TeamLogo slug={home.slug} name={home.name} size={56} />
                <span className="font-display text-2xl md:text-4xl font-bold uppercase tracking-tighter truncate">
                  {home.name}
                </span>
              </Link>
              <div className="flex flex-col items-center gap-1">
                <span className="font-mono text-muted">vs</span>
                <Link
                  href={`/compare?home=${away.slug}&away=${home.slug}`}
                  className="font-mono text-[10px] uppercase tracking-wide text-muted hover:text-neon"
                  title={c.swap}
                >
                  ⇄ {c.swap}
                </Link>
              </div>
              <Link href={`/teams/${away.slug}`} className="flex items-center gap-3 min-w-0 hover:text-neon justify-end">
                <span className="font-display text-2xl md:text-4xl font-bold uppercase tracking-tighter truncate text-right">
                  {away.name}
                </span>
                <TeamLogo slug={away.slug} name={away.name} size={56} />
              </Link>
            </div>
          </section>

          <section className="card p-0 overflow-x-auto">
            <table className="w-full">
              <tbody>
                <StatRow label={c.labels.points} home={home.stats.points} away={away.stats.points} format={(n) => String(n)} />
                <StatRow label={c.labels.wins} home={home.stats.wins} away={away.stats.wins} format={(n) => String(n)} />
                <StatRow label={c.labels.losses} home={home.stats.losses} away={away.stats.losses} format={(n) => String(n)} higherIsBetter={false} />
                <StatRow label={c.labels.gf} home={home.stats.goals_for} away={away.stats.goals_for} format={(n) => String(n)} />
                <StatRow label={c.labels.ga} home={home.stats.goals_against} away={away.stats.goals_against} format={(n) => String(n)} higherIsBetter={false} />
                <StatRow label={c.labels.xgf} home={home.stats.xg_for} away={away.stats.xg_for} />
                <StatRow label={c.labels.xga} home={home.stats.xg_against} away={away.stats.xg_against} higherIsBetter={false} />
                <StatRow label={c.labels.xgd}
                  home={home.stats.xg_for - home.stats.xg_against}
                  away={away.stats.xg_for - away.stats.xg_against}
                />
                <StatRow label={c.labels.ppg}
                  home={pct(home.stats.points, home.stats.played)}
                  away={pct(away.stats.points, away.stats.played)}
                />
              </tbody>
            </table>
          </section>

          <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="card space-y-2">
              <h2 className="label">{home.short_name} · {c.form}</h2>
              <FormDots form={home.form} />
            </div>
            <div className="card space-y-2">
              <h2 className="label">{away.short_name} · {c.form}</h2>
              <FormDots form={away.form} />
            </div>
          </section>

          <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[home, away].map((team) => (
              <div key={team.slug} className="card space-y-2">
                <h2 className="label">{team.short_name} · {c.topScorers}</h2>
                {team.top_scorers.length === 0 ? (
                  <p className="text-muted text-sm">{c.noPlayerData}</p>
                ) : (
                  <ul className="space-y-1 text-sm">
                    {team.top_scorers.slice(0, 5).map((s) => (
                      <li key={s.player_name} className="flex justify-between font-mono">
                        <span className="truncate">{s.player_name}</span>
                        <span className="tabular-nums text-neon">
                          {s.goals ?? 0}{" "}
                          <span className="text-muted text-xs">· xG {(s.xg ?? 0).toFixed(1)}</span>
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </section>
        </>
      )}
    </main>
  );
}
