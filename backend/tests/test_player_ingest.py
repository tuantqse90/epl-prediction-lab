"""TDD tests for Understat player-season stats → DB row translation."""

from __future__ import annotations

import pandas as pd


def _toy_player_df() -> pd.DataFrame:
    rows = [
        ("ENG-Premier League", "2425", "Arsenal", "Bukayo Saka",     "F M S", 25, 6, 10, 8.94,  11.58, 5, 58, 0),
        ("ENG-Premier League", "2425", "Arsenal", "David Raya",      "GK",    38, 0,  0, 0.0,    0.09, 0,  1, 0),
        ("ENG-Premier League", "2425", "Fulham",  "Rodrigo Muniz",   "F",     22, 8,  1, 7.21,   1.42, 5, 12, 0),
    ]
    cols = [
        "league", "season", "team", "player",
        "position", "matches", "goals", "assists", "xg", "xa",
        "np_goals", "key_passes", "red_cards",
    ]
    df = pd.DataFrame(rows, columns=cols)
    # Soccerdata actually returns a MultiIndex; mimic by setting it here.
    return df.set_index(["league", "season", "team", "player"])


def test_player_translator_reads_team_and_player_from_index():
    from app.ingest.players import player_stats_to_rows

    out = player_stats_to_rows(_toy_player_df(), season="2024-25")
    by_player = {r.player_name: r for r in out}
    assert set(by_player.keys()) == {"Bukayo Saka", "David Raya", "Rodrigo Muniz"}
    assert by_player["Bukayo Saka"].team_name == "Arsenal"
    assert by_player["Rodrigo Muniz"].team_name == "Fulham"


def test_player_translator_maps_core_stat_columns():
    from app.ingest.players import player_stats_to_rows

    out = player_stats_to_rows(_toy_player_df(), season="2024-25")
    saka = next(r for r in out if r.player_name == "Bukayo Saka")
    assert saka.games == 25
    assert saka.goals == 6
    assert saka.assists == 10
    assert saka.xg == 8.94
    assert saka.xa == 11.58
    assert saka.key_passes == 58
    assert saka.position == "F M S"


def test_player_translator_stamps_season():
    from app.ingest.players import player_stats_to_rows

    out = player_stats_to_rows(_toy_player_df(), season="2024-25")
    assert all(r.season == "2024-25" for r in out)
