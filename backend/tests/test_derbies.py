"""Derby tagging — is this fixture a rivalry worth flagging?

Returns a DerbyTag per fixture when (home_slug, away_slug) is a known
rivalry pair. Variance inflation is separate — the tag alone enables
the UI chip + downstream blending.
"""
from __future__ import annotations

import pytest


def test_north_london_derby_recognised_both_orders():
    from app.models.derbies import derby_tag

    tag_ha = derby_tag("arsenal", "tottenham")
    tag_ah = derby_tag("tottenham", "arsenal")
    assert tag_ha is not None
    assert tag_ah is not None
    assert tag_ha.name == "North London Derby"
    assert tag_ah.name == "North London Derby"


def test_non_derby_returns_none():
    from app.models.derbies import derby_tag
    assert derby_tag("arsenal", "bournemouth") is None


def test_el_clasico_and_madrid_derby():
    from app.models.derbies import derby_tag
    assert derby_tag("real-madrid", "barcelona") is not None
    assert derby_tag("real-madrid", "atletico-madrid") is not None


def test_merseyside_and_manchester():
    from app.models.derbies import derby_tag
    assert derby_tag("liverpool", "everton") is not None
    assert derby_tag("manchester-united", "manchester-city") is not None


def test_derby_variance_multiplier_in_band():
    """Must stay in a plausible band (1.0 .. 1.3). 30% max variance bump."""
    from app.models.derbies import derby_tag

    tag = derby_tag("arsenal", "tottenham")
    assert tag is not None
    assert 1.0 <= tag.variance_multiplier <= 1.3
