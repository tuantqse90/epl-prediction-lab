import type { MatchOut } from "./types";

// Server components reach the API via the Docker network (http://api:8000);
// browser-side uses the same-origin reverse proxy, so NEXT_PUBLIC_API_URL can
// stay empty in production and requests go to `/api/...` relative.
const BASE =
  typeof window === "undefined"
    ? process.env.SERVER_API_URL ?? "http://localhost:8000"
    : process.env.NEXT_PUBLIC_API_URL ?? "";

export async function listMatches(
  opts: { upcomingOnly?: boolean; limit?: number; league?: string } = {},
) {
  const params = new URLSearchParams();
  if (opts.upcomingOnly !== undefined) params.set("upcoming_only", String(opts.upcomingOnly));
  if (opts.limit !== undefined) params.set("limit", String(opts.limit));
  if (opts.league) params.set("league", opts.league);
  const url = `${BASE}/api/matches?${params.toString()}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`listMatches failed: ${res.status}`);
  return (await res.json()) as MatchOut[];
}

export async function getMatch(matchId: number) {
  const res = await fetch(`${BASE}/api/matches/${matchId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`getMatch failed: ${res.status}`);
  return (await res.json()) as MatchOut;
}

export type H2HMatch = {
  match_id: number;
  kickoff_date: string;
  season: string;
  league_code: string | null;
  home_slug: string;
  home_short: string;
  home_goals: number;
  away_slug: string;
  away_short: string;
  away_goals: number;
};

export async function getH2H(matchId: number, limit = 5): Promise<H2HMatch[]> {
  const res = await fetch(`${BASE}/api/matches/${matchId}/h2h?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) return [];
  return (await res.json()) as H2HMatch[];
}

export type Injury = {
  team_slug: string;
  player_name: string;
  reason: string | null;
  status_label: string | null;
  last_seen_at: string;
};

export type MatchInjuries = { home: Injury[]; away: Injury[] };

export async function getInjuries(matchId: number): Promise<MatchInjuries> {
  const res = await fetch(`${BASE}/api/matches/${matchId}/injuries`, { cache: "no-store" });
  if (!res.ok) return { home: [], away: [] };
  return (await res.json()) as MatchInjuries;
}

export type LineupPlayer = {
  player_name: string;
  player_number: number | null;
  position: string | null;
  is_starting: boolean;
};

export type TeamLineup = {
  team_slug: string;
  formation: string | null;
  starting: LineupPlayer[];
  bench: LineupPlayer[];
};

export type MatchLineups = { home: TeamLineup | null; away: TeamLineup | null };

export async function getLineups(matchId: number): Promise<MatchLineups> {
  const res = await fetch(`${BASE}/api/matches/${matchId}/lineups`, { cache: "no-store" });
  if (!res.ok) return { home: null, away: null };
  return (await res.json()) as MatchLineups;
}

export type ScorerOdds = {
  player_name: string;
  team_slug: string;
  team_short: string;
  position: string | null;
  season_xg: number;
  season_games: number;
  expected_goals: number;
  p_anytime: number;
};

export async function getScorerOdds(matchId: number, limit = 12): Promise<ScorerOdds[]> {
  const res = await fetch(`${BASE}/api/matches/${matchId}/scorers?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) return [];
  return (await res.json()) as ScorerOdds[];
}

export type TeamInjuryImpact = {
  team_slug: string;
  injured_xg_share: number;
  lambda_multiplier: number;
  top_absent: string[];
};

export type InjuryImpact = { home: TeamInjuryImpact; away: TeamInjuryImpact };

export async function getInjuryImpact(matchId: number): Promise<InjuryImpact | null> {
  const res = await fetch(`${BASE}/api/matches/${matchId}/injury-impact`, { cache: "no-store" });
  if (!res.ok) return null;
  return (await res.json()) as InjuryImpact;
}

export type Weather = {
  temp_c: number | null;
  wind_kmh: number | null;
  precip_mm: number | null;
  condition: string | null;
  fetched_at: string | null;
};

export async function getWeather(matchId: number): Promise<Weather | null> {
  const res = await fetch(`${BASE}/api/matches/${matchId}/weather`, { cache: "no-store" });
  if (!res.ok) return null;
  const body = (await res.json()) as Weather | null;
  return body;
}

export type Markets = {
  prob_over_0_5: number;
  prob_over_1_5: number;
  prob_over_2_5: number;
  prob_over_3_5: number;
  prob_btts: number;
  prob_home_clean_sheet: number;
  prob_away_clean_sheet: number;
  lam_home: number;
  lam_away: number;
};

export async function getMarkets(matchId: number): Promise<Markets | null> {
  const res = await fetch(`${BASE}/api/matches/${matchId}/markets`, { cache: "no-store" });
  if (!res.ok) return null;
  return (await res.json()) as Markets | null;
}

export async function fetchSuggestedPrompts(matchId: number): Promise<string[]> {
  const res = await fetch(`${BASE}/api/chat/suggest/${matchId}`, { cache: "no-store" });
  if (!res.ok) return [];
  const { prompts } = await res.json();
  return prompts as string[];
}

function getSessionId(): string {
  if (typeof window === "undefined") return "";
  let id = window.localStorage.getItem("epl-lab:session-id");
  if (!id) {
    id =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}`;
    window.localStorage.setItem("epl-lab:session-id", id);
  }
  return id;
}

export async function* streamChat(matchId: number, question: string): AsyncGenerator<string> {
  const res = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ match_id: matchId, question, session_id: getSessionId() }),
  });
  if (!res.ok || !res.body) {
    throw new Error(`streamChat failed: ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    yield decoder.decode(value, { stream: true });
  }
}

export async function fetchChatHistory(matchId: number): Promise<Array<{ role: string; content: string }>> {
  if (typeof window === "undefined") return [];
  const session_id = getSessionId();
  const params = new URLSearchParams({ session_id, match_id: String(matchId) });
  const res = await fetch(`${BASE}/api/chat/history?${params.toString()}`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}
