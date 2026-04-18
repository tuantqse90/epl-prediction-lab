"""TDD tests for the pure DataFrame → row translation layer.

The IO side (asyncpg upsert) is a thin wrapper that we verify manually
against a real DB; these tests cover the logic that's easy to get wrong.
"""

from __future__ import annotations

import pandas as pd


def _toy_understat_schedule() -> pd.DataFrame:
    rows = [
        ("2024-08-16 19:00", 26602, "Manchester United", "Fulham", 1, 0, 2.04, 0.42, True),
        ("2024-08-17 14:00", 26604, "Arsenal", "Wolverhampton Wanderers", 2, 0, 1.63, 0.58, True),
        # Reverse fixture — same teams, should not produce duplicate team rows:
        ("2024-11-02 16:30", 26700, "Fulham", "Manchester United", 0, 1, 0.90, 1.45, True),
        # Unplayed (scheduled) future fixture:
        ("2025-05-25 16:00", 26999, "Arsenal", "Fulham", None, None, None, None, False),
    ]
    df = pd.DataFrame(
        rows,
        columns=["date", "game_id", "home_team", "away_team",
                 "home_goals", "away_goals", "home_xg", "away_xg", "is_result"],
    )
    df["date"] = pd.to_datetime(df["date"])
    return df


def test_translate_returns_unique_team_rows():
    from app.ingest.schedule import schedule_to_rows

    teams, _ = schedule_to_rows(_toy_understat_schedule(), season="2024-25")
    names = {t.name for t in teams}
    assert names == {"Manchester United", "Fulham", "Arsenal", "Wolverhampton Wanderers"}
    # No duplicates even though Manchester United / Fulham appear twice
    assert len(teams) == 4


def test_translate_team_slugs_are_url_safe():
    from app.ingest.schedule import schedule_to_rows

    teams, _ = schedule_to_rows(_toy_understat_schedule(), season="2024-25")
    by_name = {t.name: t for t in teams}
    assert by_name["Manchester United"].slug == "manchester-united"
    assert by_name["Wolverhampton Wanderers"].slug == "wolverhampton-wanderers"


def test_translate_match_rows_carry_external_id_and_season():
    from app.ingest.schedule import schedule_to_rows

    _, matches = schedule_to_rows(_toy_understat_schedule(), season="2024-25")
    assert len(matches) == 4
    assert all(m.season == "2024-25" for m in matches)
    assert {m.external_id for m in matches} == {"26602", "26604", "26700", "26999"}


def test_translate_match_status_reflects_is_result():
    from app.ingest.schedule import schedule_to_rows

    _, matches = schedule_to_rows(_toy_understat_schedule(), season="2024-25")
    by_ext = {m.external_id: m for m in matches}
    assert by_ext["26602"].status == "final"
    assert by_ext["26999"].status == "scheduled"


def test_translate_match_rows_resolve_team_slugs():
    from app.ingest.schedule import schedule_to_rows

    _, matches = schedule_to_rows(_toy_understat_schedule(), season="2024-25")
    mu_fulham = next(m for m in matches if m.external_id == "26602")
    assert mu_fulham.home_slug == "manchester-united"
    assert mu_fulham.away_slug == "fulham"
    assert mu_fulham.home_goals == 1
    assert mu_fulham.away_goals == 0
    assert mu_fulham.home_xg == 2.04
    assert mu_fulham.away_xg == 0.42


def test_translate_unplayed_match_has_null_goals_and_xg():
    from app.ingest.schedule import schedule_to_rows

    _, matches = schedule_to_rows(_toy_understat_schedule(), season="2024-25")
    future = next(m for m in matches if m.external_id == "26999")
    assert future.home_goals is None
    assert future.away_goals is None
    assert future.home_xg is None
    assert future.away_xg is None
