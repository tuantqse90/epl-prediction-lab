"""Pydantic response models for the public API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TeamBrief(BaseModel):
    slug: str
    name: str
    short_name: str
    form: list[str] = []


class Scoreline(BaseModel):
    home: int
    away: int
    prob: float


class PredictionOut(BaseModel):
    p_home_win: float
    p_draw: float
    p_away_win: float
    expected_home_goals: float
    expected_away_goals: float
    top_scorelines: list[Scoreline]
    reasoning: str | None = None
    reasoning_model: str | None = None
    model_version: str
    commitment_hash: str | None = None


class OddsOut(BaseModel):
    odds_home: float
    odds_draw: float
    odds_away: float
    fair_home: float
    fair_draw: float
    fair_away: float
    source: str
    edge_home: float | None = None
    edge_draw: float | None = None
    edge_away: float | None = None
    best_outcome: str | None = None
    best_edge: float | None = None


class LiveStatsSide(BaseModel):
    possession_pct: str | None = None
    shots_total: int | None = None
    shots_on: int | None = None
    corners: int | None = None
    fouls: int | None = None
    offsides: int | None = None
    passes_pct: str | None = None
    saves: int | None = None
    xg: float | str | None = None


class LiveStats(BaseModel):
    home: LiveStatsSide | None = None
    away: LiveStatsSide | None = None


class LiveOut(BaseModel):
    minute: int
    live_period: str | None = None     # '1H' | 'HT' | '2H' | 'FT' | 'AET' | 'PEN'
    live_updated_at: datetime | None = None
    # (referee sits on MatchOut directly since it applies pre-match too)
    p_home_win: float
    p_draw: float
    p_away_win: float
    expected_remaining_home_goals: float
    expected_remaining_away_goals: float
    stats: LiveStats | None = None


class MatchEventOut(BaseModel):
    minute: int | None = None
    extra_minute: int | None = None
    team_slug: str | None = None
    player_name: str | None = None
    assist_name: str | None = None
    event_type: str
    event_detail: str | None = None


class MatchOut(BaseModel):
    id: int
    external_id: str
    league_code: str = "ENG-Premier League"
    season: str
    kickoff_time: datetime
    status: str
    home: TeamBrief
    away: TeamBrief
    home_goals: int | None = None
    away_goals: int | None = None
    home_xg: float | None = None
    away_xg: float | None = None
    referee: str | None = None
    prediction: PredictionOut | None = None
    odds: OddsOut | None = None
    live: LiveOut | None = None
    events: list[MatchEventOut] = []
