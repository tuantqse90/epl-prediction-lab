export type TeamBrief = {
  slug: string;
  name: string;
  short_name: string;
  form?: string[];
};

export type Scoreline = {
  home: number;
  away: number;
  prob: number;
};

export type PredictionOut = {
  p_home_win: number;
  p_draw: number;
  p_away_win: number;
  expected_home_goals: number;
  expected_away_goals: number;
  top_scorelines: Scoreline[];
  reasoning: string | null;
  reasoning_model: string | null;
  model_version: string;
  commitment_hash: string | null;
};

export type OddsOut = {
  odds_home: number;
  odds_draw: number;
  odds_away: number;
  fair_home: number;
  fair_draw: number;
  fair_away: number;
  source: string;
  edge_home?: number | null;
  edge_draw?: number | null;
  edge_away?: number | null;
  best_outcome?: "H" | "D" | "A" | null;
  best_edge?: number | null;
};

export type LiveOut = {
  minute: number;
  live_period: string | null; // '1H' | 'HT' | '2H' | 'FT' | 'AET' | 'PEN'
  live_updated_at: string | null;
  p_home_win: number;
  p_draw: number;
  p_away_win: number;
  expected_remaining_home_goals: number;
  expected_remaining_away_goals: number;
};

export type MatchEvent = {
  minute: number | null;
  extra_minute: number | null;
  team_slug: string | null;
  player_name: string | null;
  assist_name: string | null;
  event_type: string;
  event_detail: string | null;
};

export type MatchOut = {
  id: number;
  external_id: string;
  season: string;
  league_code: string;
  kickoff_time: string;
  status: "scheduled" | "live" | "final" | string;
  home: TeamBrief;
  away: TeamBrief;
  home_goals: number | null;
  away_goals: number | null;
  home_xg: number | null;
  away_xg: number | null;
  referee: string | null;
  prediction: PredictionOut | null;
  odds: OddsOut | null;
  live: LiveOut | null;
  events: MatchEvent[];
};
