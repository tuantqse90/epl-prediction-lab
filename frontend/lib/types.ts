export type TeamBrief = {
  slug: string;
  name: string;
  short_name: string;
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

export type MatchOut = {
  id: number;
  external_id: string;
  season: string;
  kickoff_time: string;
  status: "scheduled" | "live" | "final" | string;
  home: TeamBrief;
  away: TeamBrief;
  home_goals: number | null;
  away_goals: number | null;
  home_xg: number | null;
  away_xg: number | null;
  prediction: PredictionOut | null;
  odds: OddsOut | null;
};
