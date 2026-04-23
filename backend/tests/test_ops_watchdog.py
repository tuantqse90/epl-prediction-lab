"""Watchdog checkers — each a pure function over SQL-shaped rows."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest


def _row(**kw):
    return SimpleNamespace(**kw)


NOW = datetime(2026, 4, 24, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# fixture_drift
# ---------------------------------------------------------------------------


def test_fixture_drift_flags_scheduled_past_kickoff_by_2h():
    from scripts.ops_watchdog import _check_fixture_drift

    rows = [
        # Scheduled but kickoff was 3h ago — should be live or final
        _row(id=101, kickoff_time=NOW - timedelta(hours=3),
             status="scheduled", league_code="ENG-Premier League",
             home_name="Burnley", away_name="Manchester City"),
        # Scheduled 1h ago — still within the 2h grace window
        _row(id=102, kickoff_time=NOW - timedelta(hours=1),
             status="scheduled", league_code="ESP-La Liga",
             home_name="Barcelona", away_name="Valencia"),
    ]
    alerts = _check_fixture_drift(rows, now=NOW)
    assert len(alerts) == 1
    assert alerts[0]["match_id"] == 101
    assert "Burnley" in alerts[0]["message"]


def test_fixture_drift_ignores_already_live_or_final():
    from scripts.ops_watchdog import _check_fixture_drift

    rows = [
        _row(id=201, kickoff_time=NOW - timedelta(hours=5),
             status="live", league_code="X",
             home_name="A", away_name="B"),
        _row(id=202, kickoff_time=NOW - timedelta(hours=5),
             status="final", league_code="X",
             home_name="C", away_name="D"),
    ]
    assert _check_fixture_drift(rows, now=NOW) == []


# ---------------------------------------------------------------------------
# stale_live
# ---------------------------------------------------------------------------


def test_stale_live_flags_live_rows_not_updated_recently():
    from scripts.ops_watchdog import _check_stale_live

    rows = [
        _row(id=301, status="live", live_updated_at=NOW - timedelta(minutes=10),
             home_name="A", away_name="B"),
        _row(id=302, status="live", live_updated_at=NOW - timedelta(minutes=2),
             home_name="C", away_name="D"),
    ]
    alerts = _check_stale_live(rows, now=NOW, threshold_minutes=5)
    assert [a["match_id"] for a in alerts] == [301]


def test_stale_live_handles_null_live_updated_at():
    """Live row with NULL live_updated_at has never been touched — alert."""
    from scripts.ops_watchdog import _check_stale_live

    rows = [_row(id=303, status="live", live_updated_at=None,
                 home_name="A", away_name="B")]
    alerts = _check_stale_live(rows, now=NOW, threshold_minutes=5)
    assert len(alerts) == 1
    assert alerts[0]["match_id"] == 303


# ---------------------------------------------------------------------------
# missing_recap
# ---------------------------------------------------------------------------


def test_missing_recap_flags_finals_older_than_12h_without_recap():
    from scripts.ops_watchdog import _check_missing_recap

    rows = [
        _row(id=401, status="final", recap=None,
             kickoff_time=NOW - timedelta(hours=13),
             home_name="A", away_name="B"),
        # Too recent — inline FT trigger probably still running
        _row(id=402, status="final", recap=None,
             kickoff_time=NOW - timedelta(hours=2),
             home_name="C", away_name="D"),
        # Has recap — OK
        _row(id=403, status="final", recap="prose",
             kickoff_time=NOW - timedelta(hours=20),
             home_name="E", away_name="F"),
    ]
    alerts = _check_missing_recap(rows, now=NOW)
    assert [a["match_id"] for a in alerts] == [401]


# ---------------------------------------------------------------------------
# low_quota
# ---------------------------------------------------------------------------


def test_low_quota_flags_below_threshold():
    from scripts.ops_watchdog import _check_low_quota

    assert _check_low_quota(remaining=5000, threshold=10_000) != []
    assert _check_low_quota(remaining=15_000, threshold=10_000) == []


def test_low_quota_handles_missing_reading():
    """No recorded reading (None) is not an alert — don't spam on fresh boot."""
    from scripts.ops_watchdog import _check_low_quota

    assert _check_low_quota(remaining=None, threshold=10_000) == []


# ---------------------------------------------------------------------------
# stale_predictions
# ---------------------------------------------------------------------------


def test_stale_predictions_flags_upcoming_matches_without_prediction():
    from scripts.ops_watchdog import _check_stale_predictions

    rows = [
        _row(id=501, kickoff_time=NOW + timedelta(hours=24),
             has_prediction=False, home_name="A", away_name="B"),
        _row(id=502, kickoff_time=NOW + timedelta(hours=24),
             has_prediction=True, home_name="C", away_name="D"),
        # Too far in the future — predict_upcoming hasn't touched it yet
        _row(id=503, kickoff_time=NOW + timedelta(days=5),
             has_prediction=False, home_name="E", away_name="F"),
    ]
    alerts = _check_stale_predictions(rows, now=NOW)
    assert [a["match_id"] for a in alerts] == [501]


# ---------------------------------------------------------------------------
# dispatcher dedup
# ---------------------------------------------------------------------------


def test_alert_hash_stable_for_same_content():
    """Same checker output two ticks running must produce the same hash so
    the dedup layer can suppress re-posting."""
    from scripts.ops_watchdog import _alert_hash

    a = [{"match_id": 101, "message": "x"}, {"match_id": 102, "message": "y"}]
    b = [{"match_id": 102, "message": "y"}, {"match_id": 101, "message": "x"}]
    assert _alert_hash("fixture_drift", a) == _alert_hash("fixture_drift", b)


def test_alert_hash_differs_when_content_changes():
    from scripts.ops_watchdog import _alert_hash

    a = [{"match_id": 101, "message": "x"}]
    b = [{"match_id": 101, "message": "x"}, {"match_id": 102, "message": "y"}]
    assert _alert_hash("fixture_drift", a) != _alert_hash("fixture_drift", b)
