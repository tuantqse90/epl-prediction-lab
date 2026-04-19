import type { Lang } from "@/lib/i18n";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type BookRow = {
  book: string;
  odds_home: number;
  odds_draw: number;
  odds_away: number;
  fair_home: number;
  fair_draw: number;
  fair_away: number;
  edge_home: number | null;
  edge_draw: number | null;
  edge_away: number | null;
  captured_at: string;
};

type ComparisonOut = {
  match_id: number;
  updated_at: string | null;
  books: BookRow[];
  best_home_book: string | null;
  best_home_odds: number | null;
  best_draw_book: string | null;
  best_draw_odds: number | null;
  best_away_book: string | null;
  best_away_odds: number | null;
};

async function fetchComparison(matchId: number): Promise<ComparisonOut | null> {
  try {
    const res = await fetch(`${BASE}/api/matches/${matchId}/odds-comparison`, { cache: "no-store" });
    if (!res.ok) return null;
    const d = (await res.json()) as ComparisonOut;
    return d.books.length > 0 ? d : null;
  } catch {
    return null;
  }
}

function book_label(key: string): string {
  const map: Record<string, string> = {
    pinnacle: "Pinnacle",
    bet365: "Bet365",
    williamhill_uk: "William Hill",
    williamhill: "William Hill",
    unibet_eu: "Unibet",
    unibet: "Unibet",
    betfair_ex_uk: "Betfair",
    betfair: "Betfair",
    marathonbet: "Marathon",
    onexbet: "1xBet",
    nordicbet: "NordicBet",
    betvictor: "Betvictor",
    paddypower: "PaddyPower",
    ladbrokes_uk: "Ladbrokes",
    ladbrokes: "Ladbrokes",
    coolbet: "Coolbet",
    betsson: "Betsson",
    matchbook: "Matchbook",
    betclic: "Betclic",
    livescorebet_eu: "LiveScoreBet",
  };
  return map[key] ?? key.replace(/_/g, " ");
}

function pp(x: number | null): string {
  if (x == null) return "—";
  const n = Math.round(x * 1000) / 10;
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(1)}pp`;
}

export default async function OddsComparisonPanel({
  matchId,
  homeShort,
  awayShort,
  lang,
}: {
  matchId: number;
  homeShort: string;
  awayShort: string;
  lang: Lang;
}) {
  const d = await fetchComparison(matchId);
  if (!d || d.books.length < 2) return null;

  return (
    <section className="card space-y-3">
      <div className="flex items-baseline justify-between flex-wrap gap-2">
        <h3 className="font-display font-semibold uppercase tracking-tight">
          {lang === "vi" ? "So sánh kèo" : "Odds comparison"}
        </h3>
        <div className="flex items-baseline gap-2 font-mono text-[10px]">
          <span className="text-muted">{d.books.length} {lang === "vi" ? "nhà cái" : "books"}</span>
          {d.updated_at && (
            <>
              <span className="text-muted">·</span>
              <span className="text-muted">
                {new Date(d.updated_at).toLocaleString()}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Best-price band */}
      <div className="grid grid-cols-3 gap-2 font-mono text-xs">
        <div className="rounded-lg bg-neon/5 border border-neon/30 p-2">
          <p className="text-[10px] uppercase tracking-wide text-muted">
            {lang === "vi" ? "Best" : "Best"} · {homeShort}
          </p>
          <p className="stat text-neon text-lg">{d.best_home_odds?.toFixed(2) ?? "—"}</p>
          <p className="text-[10px] text-secondary truncate">{book_label(d.best_home_book ?? "")}</p>
        </div>
        <div className="rounded-lg bg-neon/5 border border-neon/30 p-2">
          <p className="text-[10px] uppercase tracking-wide text-muted">
            {lang === "vi" ? "Best · Hòa" : "Best · Draw"}
          </p>
          <p className="stat text-neon text-lg">{d.best_draw_odds?.toFixed(2) ?? "—"}</p>
          <p className="text-[10px] text-secondary truncate">{book_label(d.best_draw_book ?? "")}</p>
        </div>
        <div className="rounded-lg bg-neon/5 border border-neon/30 p-2">
          <p className="text-[10px] uppercase tracking-wide text-muted">
            {lang === "vi" ? "Best" : "Best"} · {awayShort}
          </p>
          <p className="stat text-neon text-lg">{d.best_away_odds?.toFixed(2) ?? "—"}</p>
          <p className="text-[10px] text-secondary truncate">{book_label(d.best_away_book ?? "")}</p>
        </div>
      </div>

      {/* Per-book table */}
      <div className="overflow-x-auto -mx-2">
        <table className="w-full font-mono text-xs">
          <thead className="text-muted">
            <tr>
              <th className="px-2 py-1 text-left">{lang === "vi" ? "Nhà cái" : "Book"}</th>
              <th className="px-2 py-1 text-right">{homeShort}</th>
              <th className="px-2 py-1 text-right">{lang === "vi" ? "Hòa" : "Draw"}</th>
              <th className="px-2 py-1 text-right">{awayShort}</th>
              <th className="px-2 py-1 text-right">{lang === "vi" ? "Biên (H)" : "Edge H"}</th>
              <th className="px-2 py-1 text-right">{lang === "vi" ? "Biên (D)" : "Edge D"}</th>
              <th className="px-2 py-1 text-right">{lang === "vi" ? "Biên (A)" : "Edge A"}</th>
            </tr>
          </thead>
          <tbody>
            {d.books.map((b) => {
              const isBestH = b.book === d.best_home_book;
              const isBestD = b.book === d.best_draw_book;
              const isBestA = b.book === d.best_away_book;
              const edgeCls = (e: number | null) =>
                e == null ? "text-muted" : e >= 0.05 ? "text-neon font-semibold" : e <= -0.05 ? "text-error" : "text-secondary";
              return (
                <tr key={b.book} className="border-t border-border-muted">
                  <td className="px-2 py-2 text-primary">{book_label(b.book)}</td>
                  <td className={`px-2 py-2 text-right tabular-nums ${isBestH ? "text-neon font-semibold" : "text-primary"}`}>
                    {b.odds_home.toFixed(2)}
                  </td>
                  <td className={`px-2 py-2 text-right tabular-nums ${isBestD ? "text-neon font-semibold" : "text-primary"}`}>
                    {b.odds_draw.toFixed(2)}
                  </td>
                  <td className={`px-2 py-2 text-right tabular-nums ${isBestA ? "text-neon font-semibold" : "text-primary"}`}>
                    {b.odds_away.toFixed(2)}
                  </td>
                  <td className={`px-2 py-2 text-right tabular-nums ${edgeCls(b.edge_home)}`}>{pp(b.edge_home)}</td>
                  <td className={`px-2 py-2 text-right tabular-nums ${edgeCls(b.edge_draw)}`}>{pp(b.edge_draw)}</td>
                  <td className={`px-2 py-2 text-right tabular-nums ${edgeCls(b.edge_away)}`}>{pp(b.edge_away)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="font-mono text-[10px] text-muted leading-relaxed">
        {lang === "vi"
          ? "Neon = kèo tốt nhất trong số các nhà cái. Biên = xác suất model − xác suất thực (devigged). +5pp trở lên có giá trị."
          : "Neon = best price across books. Edge = model prob − devigged fair prob. +5pp or more indicates value."}
      </p>
    </section>
  );
}
