"""TDD tests for football-data.co.uk odds ingest."""

from __future__ import annotations

import pandas as pd
import pytest


def _toy_csv() -> pd.DataFrame:
    rows = [
        # date, home, away, ftgh, ftag, avg_h, avg_d, avg_a, psh, psd, psa
        ("16/08/2024", "Man United",       "Fulham",    1, 0, 1.60, 4.20, 5.25, 1.62, 4.30, 5.30),
        ("17/08/2024", "Arsenal",          "Wolves",    2, 0, 1.22, 6.50, 13.0, 1.23, 6.60, 13.5),
        ("17/08/2024", "Everton",          "Brighton",  0, 3, 2.90, 3.40, 2.45, 2.92, 3.45, 2.46),
    ]
    return pd.DataFrame(
        rows,
        columns=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG",
                 "AvgH", "AvgD", "AvgA", "PSH", "PSD", "PSA"],
    )


def test_odds_translator_maps_football_data_names_to_understat():
    from app.ingest.odds import odds_csv_to_rows

    out = odds_csv_to_rows(_toy_csv(), season="2024-25")
    names = {(r.home_name, r.away_name) for r in out}
    # Man United → Manchester United; Wolves → Wolverhampton Wanderers.
    assert ("Manchester United", "Fulham") in names
    assert ("Arsenal", "Wolverhampton Wanderers") in names
    assert ("Everton", "Brighton") in names


def test_odds_translator_uses_avg_columns_when_present():
    from app.ingest.odds import odds_csv_to_rows

    out = odds_csv_to_rows(_toy_csv(), season="2024-25")
    row = next(r for r in out if r.home_name == "Arsenal")
    assert row.odds_home == pytest.approx(1.22)
    assert row.odds_draw == pytest.approx(6.50)
    assert row.odds_away == pytest.approx(13.0)


def test_odds_translator_falls_back_to_pinnacle_when_avg_missing():
    from app.ingest.odds import odds_csv_to_rows

    df = _toy_csv().drop(columns=["AvgH", "AvgD", "AvgA"])
    out = odds_csv_to_rows(df, season="2024-25")
    row = next(r for r in out if r.home_name == "Arsenal")
    assert row.odds_home == pytest.approx(1.23)  # PSH
    assert row.odds_draw == pytest.approx(6.60)  # PSD


def test_odds_translator_skips_rows_with_no_odds():
    from app.ingest.odds import odds_csv_to_rows

    df = _toy_csv().copy()
    df.loc[0, ["AvgH", "AvgD", "AvgA", "PSH", "PSD", "PSA"]] = pd.NA
    out = odds_csv_to_rows(df, season="2024-25")
    assert not any(r.home_name == "Manchester United" for r in out)
    assert len(out) == 2  # the other 2


def test_fair_probs_strips_overround():
    from app.ingest.odds import fair_probs

    # Bookmaker's implied sums > 1 (overround); fair probs must sum to 1.
    f_h, f_d, f_a = fair_probs(1.60, 4.20, 5.25)
    assert f_h + f_d + f_a == pytest.approx(1.0)
    # Order preserved
    assert f_h > f_d > f_a


def test_fair_probs_handles_zero_odds_safely():
    from app.ingest.odds import fair_probs

    # If any odd is 0 / negative, caller should see None rather than a crash.
    assert fair_probs(0, 3.0, 3.0) is None
    assert fair_probs(2.0, -1.0, 3.0) is None


def test_edge_is_model_minus_fair():
    from app.ingest.odds import edge

    # Model says home 50%, fair implied 40% → edge +10pp.
    assert edge(0.50, 0.40) == pytest.approx(0.10)
    assert edge(0.30, 0.40) == pytest.approx(-0.10)
