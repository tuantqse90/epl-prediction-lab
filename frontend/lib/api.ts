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
