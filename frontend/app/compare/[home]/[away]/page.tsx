import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import TeamLogo from "@/components/TeamLogo";
import { getLang, tFor } from "@/lib/i18n-server";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type Triple = { p_home_win: number; p_draw: number; p_away_win: number };

type H2H = {
  home_name: string;
  home_slug: string;
  away_name: string;
  away_slug: string;
  league_code: string | null;
  poisson: Triple;
  elo: Triple | null;
  xgb: Triple | null;
  ensemble: Triple;
  expected_home_goals: number;
  expected_away_goals: number;
  top_scoreline: [number, number];
  data_as_of: string;
};

async function fetchH2H(home: string, away: string): Promise<H2H | null> {
  try {
    const res = await fetch(
      `${BASE}/api/compare/head-to-head?home=${encodeURIComponent(home)}&away=${encodeURIComponent(away)}`,
      { cache: "no-store" },
    );
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

type H2HMeeting = {
  match_id: number;
  kickoff_time: string;
  season: string;
  league_code: string | null;
  home_slug: string;
  home_short: string;
  away_slug: string;
  away_short: string;
  home_goals: number;
  away_goals: number;
  outcome: "H" | "D" | "A";
  predicted_outcome: "H" | "D" | "A" | null;
  hit: boolean | null;
};

type H2HHistory = {
  home_slug: string;
  away_slug: string;
  meetings: H2HMeeting[];
  total_meetings: number;
  home_wins: number;
  draws: number;
  away_wins: number;
  model_scored: number;
  model_correct: number;
  model_accuracy: number | null;
};

async function fetchHistory(home: string, away: string): Promise<H2HHistory | null> {
  try {
    const res = await fetch(
      `${BASE}/api/compare/history?home=${encodeURIComponent(home)}&away=${encodeURIComponent(away)}&limit=10`,
      { next: { revalidate: 600 } },
    );
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ home: string; away: string }>;
}): Promise<Metadata> {
  const { home, away } = await params;
  const title = `${home.replace(/-/g, " ")} vs ${away.replace(/-/g, " ")} — model head-to-head`;
  return {
    title: title + " · predictor.nullshift.sh",
    description: `How each of the three ensemble legs (Poisson / Elo / XGBoost) would predict a ${home} vs ${away} fixture.`,
  };
}

function pct(x: number) {
  return `${Math.round(x * 100)}%`;
}

function Bar({ value, color = "bg-neon" }: { value: number; color?: string }) {
  const w = Math.max(2, Math.min(100, value * 100));
  return (
    <div className="flex-1 h-5 rounded bg-high overflow-hidden">
      <div className={`h-full ${color} transition-all`} style={{ width: `${w}%` }} />
    </div>
  );
}

function LegRow({
  label,
  title,
  triple,
  accent = false,
}: {
  label: string;
  title: string;
  triple: Triple | null;
  accent?: boolean;
}) {
  if (!triple) {
    return (
      <div className="card space-y-2 opacity-60">
        <p className={`font-mono text-[10px] uppercase tracking-[0.18em] ${accent ? "text-neon" : "text-muted"}`}>
          {label}
        </p>
        <p className="font-display text-lg">{title}</p>
        <p className="text-secondary text-sm">not available</p>
      </div>
    );
  }
  const pick = (["p_home_win", "p_draw", "p_away_win"] as const).reduce(
    (a, b) => (triple[b] > triple[a] ? b : a),
  );
  return (
    <div className={`card space-y-3 ${accent ? "border-neon/50" : ""}`}>
      <div className="flex items-baseline justify-between">
        <p className={`font-mono text-[10px] uppercase tracking-[0.18em] ${accent ? "text-neon" : "text-muted"}`}>
          {label}
        </p>
        <p className="font-mono text-[10px] text-muted">{title}</p>
      </div>
      <div className="space-y-2">
        {(["p_home_win", "p_draw", "p_away_win"] as const).map((k, i) => (
          <div key={k} className="flex items-center gap-3 font-mono text-xs">
            <span className="w-16 shrink-0 uppercase text-secondary">
              {i === 0 ? "Home" : i === 1 ? "Draw" : "Away"}
            </span>
            <Bar value={triple[k]} color={k === pick ? "bg-neon" : "bg-secondary/40"} />
            <span className={`w-12 text-right tabular-nums ${k === pick ? "text-neon font-semibold" : "text-primary"}`}>
              {pct(triple[k])}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default async function CompareH2HPage({
  params,
}: {
  params: Promise<{ home: string; away: string }>;
}) {
  const { home, away } = await params;
  const lang = await getLang();
  const t = tFor(lang);
  const [data, history] = await Promise.all([
    fetchH2H(home, away),
    fetchHistory(home, away),
  ]);
  if (!data) notFound();

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-10">
      <Link href="/" className="btn-ghost text-sm">
        {t("common.back")}
      </Link>

      <header className="space-y-4">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-neon">
          {lang === "vi" ? "Model head-to-head" : "Model head-to-head"}
        </p>
        <h1 className="flex flex-wrap items-center gap-3 md:gap-5">
          <span className="flex items-center gap-3">
            <TeamLogo slug={data.home_slug} name={data.home_name} size={48} />
            <span className="headline-hero text-3xl md:text-4xl">{data.home_name}</span>
          </span>
          <span className="text-muted font-body normal-case text-xl">vs</span>
          <span className="flex items-center gap-3">
            <TeamLogo slug={data.away_slug} name={data.away_name} size={48} />
            <span className="headline-hero text-3xl md:text-4xl">{data.away_name}</span>
          </span>
        </h1>
        <p className="text-secondary text-sm max-w-2xl">
          {lang === "vi"
            ? "Mỗi leg của ensemble dự đoán riêng. So sánh để thấy Poisson, Elo, XGBoost đồng thuận hay bất đồng ở đâu — và cuối cùng blended trọng số ra con số."
            : "Each ensemble leg predicts independently. Compare to see where Poisson, Elo, and XGBoost agree or disagree — the final blended number is the weighted mix."}
        </p>
        <p className="font-mono text-[11px] text-muted">
          {lang === "vi" ? "Dữ liệu" : "Snapshot"}: {new Date(data.data_as_of).toLocaleString()}
          {data.league_code ? ` · ${data.league_code}` : ""}
        </p>
      </header>

      {/* top summary */}
      <section className="card grid grid-cols-2 md:grid-cols-3 gap-4">
        <div>
          <p className="label">{lang === "vi" ? "Tỷ số dự đoán" : "Top scoreline"}</p>
          <p className="stat text-neon text-4xl md:text-5xl">
            {data.top_scoreline[0]}–{data.top_scoreline[1]}
          </p>
        </div>
        <div>
          <p className="label">{lang === "vi" ? "xG kỳ vọng" : "Expected goals"}</p>
          <p className="stat">
            {data.expected_home_goals.toFixed(2)} — {data.expected_away_goals.toFixed(2)}
          </p>
        </div>
        <div>
          <p className="label">{lang === "vi" ? "Ensemble chọn" : "Ensemble picks"}</p>
          <p className="stat text-neon">
            {(() => {
              const t = data.ensemble;
              const pick = t.p_home_win > t.p_draw && t.p_home_win > t.p_away_win
                ? data.home_name
                : t.p_away_win > t.p_draw
                ? data.away_name
                : lang === "vi" ? "Hòa" : "Draw";
              const max = Math.max(t.p_home_win, t.p_draw, t.p_away_win);
              return `${pick} · ${pct(max)}`;
            })()}
          </p>
        </div>
      </section>

      {/* per-leg grid */}
      <section className="grid gap-4 md:grid-cols-2">
        <LegRow
          label={lang === "vi" ? "Leg 1 · Poisson+DC" : "Leg 1 · Poisson+DC"}
          title={lang === "vi" ? "xG thô, Dixon-Coles ρ=-0.15" : "Raw xG · Dixon-Coles ρ=-0.15"}
          triple={data.poisson}
        />
        <LegRow
          label={lang === "vi" ? "Leg 2 · Elo" : "Leg 2 · Elo"}
          title={lang === "vi" ? "K=20 · HFA=+70" : "Goal-weighted · K=20 · HFA=+70"}
          triple={data.elo}
        />
        <LegRow
          label={lang === "vi" ? "Leg 3 · XGBoost" : "Leg 3 · XGBoost"}
          title={lang === "vi" ? "21 features · softprob" : "21 features · multi:softprob"}
          triple={data.xgb}
        />
        <LegRow
          label={lang === "vi" ? "Blended (final)" : "Blended (final)"}
          title="elo=0.20 · xgb=0.60"
          triple={data.ensemble}
          accent
        />
      </section>

      {history && history.total_meetings > 0 && (
        <section className="card space-y-4">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="font-mono text-[10px] uppercase tracking-wide text-neon">
              {lang === "vi" ? `${history.total_meetings} trận gần nhất` : `Last ${history.total_meetings} meetings`}
            </p>
            <div className="font-mono text-xs text-muted">
              <span className="text-neon">{history.home_wins}</span>W ·{" "}
              <span>{history.draws}</span>D ·{" "}
              <span className="text-error">{history.away_wins}</span>L
              {history.model_scored > 0 && history.model_accuracy !== null && (
                <span className="ml-3 text-secondary">
                  · {lang === "vi" ? "model đúng" : "model hit"}{" "}
                  <b className={history.model_accuracy > 0.5 ? "text-neon" : "text-error"}>
                    {history.model_correct}/{history.model_scored}
                  </b>{" "}
                  ({pct(history.model_accuracy)})
                </span>
              )}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead className="text-[10px] uppercase tracking-wide text-muted">
                <tr className="border-b border-border">
                  <th className="py-2 pr-3 text-left">{lang === "vi" ? "Ngày" : "Date"}</th>
                  <th className="py-2 pr-3 text-left">{lang === "vi" ? "Mùa" : "Season"}</th>
                  <th className="py-2 pr-3 text-left">{lang === "vi" ? "Trận đấu" : "Fixture"}</th>
                  <th className="py-2 pr-3 text-right">{lang === "vi" ? "Tỷ số" : "Score"}</th>
                  <th className="py-2 pr-3 text-center">{lang === "vi" ? "Model" : "Model"}</th>
                </tr>
              </thead>
              <tbody>
                {history.meetings.map((m) => {
                  const scoreStr = `${m.home_goals}–${m.away_goals}`;
                  const icon =
                    m.hit === null ? "—"
                    : m.hit ? "✓"
                    : "✗";
                  const iconColor =
                    m.hit === null ? "text-muted"
                    : m.hit ? "text-neon"
                    : "text-error";
                  return (
                    <tr key={m.match_id} className="border-t border-border-muted">
                      <td className="py-2 pr-3">{new Date(m.kickoff_time).toISOString().slice(0, 10)}</td>
                      <td className="py-2 pr-3 text-muted">{m.season}</td>
                      <td className="py-2 pr-3">
                        <Link
                          href={`/match/${m.match_id}`}
                          className="hover:text-neon"
                        >
                          {m.home_short} vs {m.away_short}
                        </Link>
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums">{scoreStr}</td>
                      <td className={`py-2 pr-3 text-center ${iconColor}`}>{icon}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className="card text-xs text-muted leading-relaxed space-y-2">
        <p className="font-mono uppercase tracking-wide text-[10px] text-neon">
          {lang === "vi" ? "Lưu ý" : "Note"}
        </p>
        <p>
          {lang === "vi"
            ? "Đây là dự đoán thăm dò (không commit hash). Team strengths tính từ dữ liệu gần nhất trong DB, không bao gồm đội hình/chấn thương/thời tiết của một trận cụ thể. Nếu đây là trận đang có lịch, xem trang match detail để có chỉ số đầy đủ."
            : "Exploratory prediction (no commitment hash). Strengths are from most recent data in DB; injury / weather / lineup adjustments are NOT applied here. If this matchup is a scheduled fixture, see the match detail page for the full numbers."}
        </p>
      </section>
    </main>
  );
}
