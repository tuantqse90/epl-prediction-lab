"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import TeamLogo from "@/components/TeamLogo";
import { useLang } from "@/lib/i18n-client";
import { tLang } from "@/lib/i18n-fallback";

type Team = {
  slug: string;
  short_name: string;
  name: string;
  p_champions: number;
  p_top_four: number;
  p_relegate: number;
  mean_points: number;
};

type TitleRace = {
  league_code: string;
  season: string;
  teams: Team[];
};

type MarketKey = "p_champions" | "p_top_four" | "p_relegate";

const LEAGUES = [
  { slug: "epl", code: "ENG-Premier League", name: "EPL" },
  { slug: "laliga", code: "ESP-La Liga", name: "La Liga" },
  { slug: "seriea", code: "ITA-Serie A", name: "Serie A" },
  { slug: "bundesliga", code: "GER-Bundesliga", name: "Bundesliga" },
  { slug: "ligue1", code: "FRA-Ligue 1", name: "Ligue 1" },
];

const MARKETS: Array<{ key: MarketKey; label_en: string; label_vi: string }> = [
  { key: "p_champions", label_en: "Champion",    label_vi: "Vô địch" },
  { key: "p_top_four",  label_en: "Top 4",       label_vi: "Top 4" },
  { key: "p_relegate",  label_en: "Relegation",  label_vi: "Xuống hạng" },
];

function fairOdds(p: number): number {
  if (p <= 0.0001) return 9999;
  return 1 / p;
}

export default function OutrightsPage() {
  const lang = useLang();
  const [league, setLeague] = useState(LEAGUES[0]);
  const [market, setMarket] = useState<MarketKey>("p_champions");
  const [data, setData] = useState<TitleRace | null>(null);
  // User-posted bookmaker prices keyed on team.slug.
  const [userOdds, setUserOdds] = useState<Record<string, string>>({});

  useEffect(() => {
    setData(null);
    const qs = new URLSearchParams({ league: league.code, season: "2025-26", n: "5000" });
    fetch(`/api/stats/title-race?${qs}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setData(d));
  }, [league]);

  const rows = useMemo(() => {
    if (!data) return [];
    return [...data.teams]
      .sort((a, b) => b[market] - a[market])
      .slice(0, 20)
      .map((t) => {
        const p = t[market];
        const fair = fairOdds(p);
        const posted = parseFloat(userOdds[t.slug] ?? "");
        let edge: number | null = null;
        if (posted > 1.01) {
          edge = (p * posted - 1) * 100;
        }
        return { team: t, p, fair, posted, edge };
      });
  }, [data, market, userOdds]);

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
      </Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">sharp · outrights</p>
        <h1 className="headline-section">
          {tLang(lang, {
            en: "Outrights — fair vs posted",
            vi: "Outrights — fair vs nhà cái",
            th: "Outrights",
            zh: "冠军盘 · 期货赔率",
            ko: "아웃라이트",
          })}
        </h1>
        <p className="max-w-2xl text-secondary">
          {tLang(lang, {
            en: "Fair odds = 1 / (Monte Carlo simulated probability). Paste a bookmaker's posted outright odds below and we compute the edge. Covers Champion / Top 4 / Relegation.",
            vi: "Fair odds = 1 / xác suất Monte Carlo. Dán odds outright của nhà cái ở dưới, hệ thống tính edge. Gồm Vô địch / Top 4 / Xuống hạng.",
            th: "Fair odds = 1 / ความน่าจะเป็นจากการจำลอง Monte Carlo",
            zh: "公允赔率 = 1 / 蒙特卡洛概率",
            ko: "공정 배당 = 1 / 몬테카를로 확률",
          })}
        </p>
      </header>

      <section className="flex flex-wrap gap-3">
        <div className="flex flex-wrap gap-2">
          {LEAGUES.map((l) => (
            <button
              key={l.slug}
              onClick={() => setLeague(l)}
              className={`rounded-full px-3 py-1 font-mono text-xs uppercase tracking-wide border ${
                league.slug === l.slug
                  ? "border-neon bg-neon text-on-neon"
                  : "border-border text-secondary hover:border-neon hover:text-neon"
              }`}
            >
              {l.name}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-2 ml-auto">
          {MARKETS.map((m) => (
            <button
              key={m.key}
              onClick={() => setMarket(m.key)}
              className={`rounded-full px-3 py-1 font-mono text-xs uppercase tracking-wide border ${
                market === m.key
                  ? "border-neon bg-neon text-on-neon"
                  : "border-border text-secondary hover:border-neon hover:text-neon"
              }`}
            >
              {lang === "vi" ? m.label_vi : m.label_en}
            </button>
          ))}
        </div>
      </section>

      {!data ? (
        <div className="card text-muted">Loading…</div>
      ) : (
        <section className="card p-0 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-[10px] uppercase tracking-wide text-muted">
              <tr className="border-b border-border">
                <th className="px-3 py-3 text-left">{tLang(lang, { en: "Team", vi: "Đội", th: "ทีม", zh: "球队", ko: "팀" })}</th>
                <th className="px-3 py-3 text-right">P</th>
                <th className="px-3 py-3 text-right">Fair odds</th>
                <th className="px-3 py-3 text-right">
                  {tLang(lang, { en: "Your odds", vi: "Odds của bạn", th: "ราคาของคุณ", zh: "你的赔率", ko: "당신의 배당" })}
                </th>
                <th className="px-3 py-3 text-right">Edge</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ team, p, fair, posted, edge }) => (
                <tr key={team.slug} className="border-t border-border-muted">
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <TeamLogo slug={team.slug} name={team.name} size={20} />
                      <span className="font-display uppercase tracking-tighter">{team.short_name}</span>
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">{(p * 100).toFixed(1)}%</td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums text-neon">
                    {fair < 100 ? fair.toFixed(2) : "—"}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <input
                      type="number"
                      step="0.01"
                      min="1.01"
                      placeholder="e.g. 3.50"
                      value={userOdds[team.slug] ?? ""}
                      onChange={(e) => setUserOdds((prev) => ({ ...prev, [team.slug]: e.target.value }))}
                      className="w-24 rounded border border-border bg-raised px-2 py-1 text-right font-mono text-sm tabular-nums"
                    />
                  </td>
                  <td
                    className={`px-3 py-2 text-right font-mono tabular-nums ${
                      edge == null ? "text-muted"
                      : edge > 5 ? "text-neon"
                      : edge > 0 ? ""
                      : "text-error"
                    }`}
                  >
                    {edge == null ? "—" : `${edge > 0 ? "+" : ""}${edge.toFixed(1)}%`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <section className="font-mono text-[11px] uppercase tracking-wide text-muted space-y-1">
        <p>• Probabilities from the same MC engine as /title-race + /relegation.</p>
        <p>• Edge = p × posted − 1. Green when ≥ 5%; red when negative.</p>
        <p>• Paste the book's posted outright odds to calculate edge per team. Your inputs stay in this session.</p>
      </section>
    </main>
  );
}
