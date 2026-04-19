import { ImageResponse } from "next/og";

import { getMatch } from "@/lib/api";
import { leagueByCode } from "@/lib/leagues";

export const alt = "EPL Prediction Lab — match prediction";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const runtime = "nodejs";

function pct(x: number) {
  return `${Math.round(x * 100)}%`;
}

function kickoffStr(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default async function MatchOpenGraphImage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let match;
  try {
    match = await getMatch(Number(id));
  } catch {
    return fallback("EPL Prediction Lab");
  }

  const p = match.prediction;
  const topScore = p?.top_scorelines?.[0];
  const league = leagueByCode(match.league_code);

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          backgroundColor: "#000",
          color: "#fff",
          padding: 64,
          fontFamily: "Geist, Inter, system-ui, sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 28, color: "#778899", letterSpacing: 2, textTransform: "uppercase" }}>
            {league ? `${league.emoji} ${league.short}` : "Prediction Lab"}
          </span>
          <span style={{ fontSize: 24, color: "#E0FF32", letterSpacing: 2, textTransform: "uppercase" }}>
            {match.status}
          </span>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            flex: 1,
            gap: 24,
          }}
        >
          <div style={{ fontSize: 36, color: "#D9D9D9" }}>{kickoffStr(match.kickoff_time)}</div>
          <div style={{ display: "flex", alignItems: "center", gap: 40, fontSize: 96, fontWeight: 700, textTransform: "uppercase", letterSpacing: "-0.02em" }}>
            <span>{match.home.name}</span>
            <span style={{ color: "#778899", fontSize: 48 }}>vs</span>
            <span>{match.away.name}</span>
          </div>

          {p && topScore ? (
            <div style={{ display: "flex", alignItems: "baseline", gap: 40, marginTop: 24 }}>
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span style={{ fontSize: 22, color: "#778899", textTransform: "uppercase", letterSpacing: 2 }}>
                  Most likely
                </span>
                <span style={{ fontSize: 120, color: "#E0FF32", fontWeight: 700, lineHeight: 1 }}>
                  {topScore.home}–{topScore.away}
                </span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", marginLeft: "auto" }}>
                <span style={{ fontSize: 22, color: "#778899", textTransform: "uppercase", letterSpacing: 2 }}>
                  H / D / A
                </span>
                <span style={{ fontSize: 56, fontFamily: "monospace", color: "#fff" }}>
                  {pct(p.p_home_win)} / {pct(p.p_draw)} / {pct(p.p_away_win)}
                </span>
              </div>
            </div>
          ) : (
            <div style={{ fontSize: 32, color: "#778899" }}>Prediction pending</div>
          )}
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 24, color: "#778899" }}>
          <span>predictor.nullshift.sh</span>
          <span>xG · Poisson · Dixon-Coles · Qwen</span>
        </div>
      </div>
    ),
    size,
  );
}

function fallback(msg: string) {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#000",
          color: "#E0FF32",
          fontSize: 72,
          fontWeight: 700,
          textTransform: "uppercase",
        }}
      >
        {msg}
      </div>
    ),
    size,
  );
}
