import Link from "next/link";

import TeamLogo from "@/components/TeamLogo";
import { getLang, tFor } from "@/lib/i18n-server";
import { colorFor } from "@/lib/team-colors";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type Stats = {
  played: number;
  wins: number;
  draws: number;
  losses: number;
  points: number;
  goals_for: number;
  goals_against: number;
  xg_for: number;
  xg_against: number;
  xg_diff: number;
};

type Scorer = {
  player_name: string;
  goals: number;
  xg: number;
  assists: number;
};

type TeamProfile = {
  slug: string;
  name: string;
  short_name: string;
  season: string;
  stats: Stats;
  form: string[];
  top_scorers: Scorer[];
};

async function fetchTeam(slug: string): Promise<TeamProfile | null> {
  try {
    const res = await fetch(`${BASE}/api/teams/${encodeURIComponent(slug)}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

function pct(x: number, y: number) {
  if (y === 0) return 0;
  return x / y;
}

function StatRow({
  label,
  home,
  away,
  format = (n: number) => n.toFixed(2),
  higherIsBetter = true,
}: {
  label: string;
  home: number;
  away: number;
  format?: (n: number) => string;
  higherIsBetter?: boolean;
}) {
  const homeBetter = higherIsBetter ? home > away : home < away;
  const awayBetter = higherIsBetter ? away > home : away < home;
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
          className={
            "h-3 w-3 rounded-full " +
            (r === "W" ? "bg-neon" : r === "D" ? "bg-secondary" : "bg-error")
          }
        />
      ))}
    </div>
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

  if (!sp.home || !sp.away) {
    return (
      <main className="mx-auto max-w-5xl px-6 py-12 space-y-6">
        <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>
        <h1 className="headline-section">Compare teams</h1>
        <p className="text-muted">
          Pass ?home=&lt;slug&gt;&amp;away=&lt;slug&gt; in the URL to compare two teams.
        </p>
      </main>
    );
  }

  const [home, away] = await Promise.all([fetchTeam(sp.home), fetchTeam(sp.away)]);

  if (!home || !away) {
    return (
      <main className="mx-auto max-w-5xl px-6 py-12 space-y-6">
        <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>
        <div className="card text-error">One or both teams not found.</div>
      </main>
    );
  }

  const homeColor = colorFor(home.slug);
  const awayColor = colorFor(away.slug);

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">{t("common.back")}</Link>

      <header
        className="relative overflow-hidden rounded-xl p-6 border border-border"
        style={{
          background: `linear-gradient(110deg, ${homeColor}33 0%, transparent 45%, transparent 55%, ${awayColor}33 100%)`,
        }}
      >
        <div className="flex items-center justify-between gap-6">
          <Link href={`/teams/${home.slug}`} className="flex items-center gap-3 min-w-0 hover:text-neon">
            <TeamLogo slug={home.slug} name={home.name} size={56} />
            <span className="font-display text-2xl md:text-4xl font-bold uppercase tracking-tighter truncate">
              {home.name}
            </span>
          </Link>
          <span className="font-mono text-muted">vs</span>
          <Link href={`/teams/${away.slug}`} className="flex items-center gap-3 min-w-0 hover:text-neon justify-end">
            <span className="font-display text-2xl md:text-4xl font-bold uppercase tracking-tighter truncate text-right">
              {away.name}
            </span>
            <TeamLogo slug={away.slug} name={away.name} size={56} />
          </Link>
        </div>
      </header>

      <section className="card p-0 overflow-x-auto">
        <table className="w-full">
          <tbody>
            <StatRow label="Points" home={home.stats.points} away={away.stats.points} format={(n) => String(n)} />
            <StatRow label="Wins" home={home.stats.wins} away={away.stats.wins} format={(n) => String(n)} />
            <StatRow label="Losses" home={home.stats.losses} away={away.stats.losses} format={(n) => String(n)} higherIsBetter={false} />
            <StatRow label="Goals for" home={home.stats.goals_for} away={away.stats.goals_for} format={(n) => String(n)} />
            <StatRow label="Goals against" home={home.stats.goals_against} away={away.stats.goals_against} format={(n) => String(n)} higherIsBetter={false} />
            <StatRow label="xG for" home={home.stats.xg_for} away={away.stats.xg_for} />
            <StatRow label="xG against" home={home.stats.xg_against} away={away.stats.xg_against} higherIsBetter={false} />
            <StatRow label="xG Δ" home={home.stats.xg_diff} away={away.stats.xg_diff} />
            <StatRow
              label="Points / game"
              home={pct(home.stats.points, home.stats.played)}
              away={pct(away.stats.points, away.stats.played)}
            />
          </tbody>
        </table>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="card space-y-2">
          <h2 className="label">{home.short_name} · form</h2>
          <FormDots form={home.form} />
        </div>
        <div className="card space-y-2">
          <h2 className="label">{away.short_name} · form</h2>
          <FormDots form={away.form} />
        </div>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="card space-y-2">
          <h2 className="label">{home.short_name} · top scorers</h2>
          <ul className="space-y-1 text-sm">
            {home.top_scorers.slice(0, 5).map((s) => (
              <li key={s.player_name} className="flex justify-between font-mono">
                <span className="truncate">{s.player_name}</span>
                <span className="tabular-nums text-neon">{s.goals} <span className="text-muted text-xs">· xG {s.xg.toFixed(1)}</span></span>
              </li>
            ))}
          </ul>
        </div>
        <div className="card space-y-2">
          <h2 className="label">{away.short_name} · top scorers</h2>
          <ul className="space-y-1 text-sm">
            {away.top_scorers.slice(0, 5).map((s) => (
              <li key={s.player_name} className="flex justify-between font-mono">
                <span className="truncate">{s.player_name}</span>
                <span className="tabular-nums text-neon">{s.goals} <span className="text-muted text-xs">· xG {s.xg.toFixed(1)}</span></span>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </main>
  );
}
