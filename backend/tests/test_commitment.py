"""TDD tests for the prediction commitment hash.

The hash is the *cryptographic* part of 'we predicted X before kickoff'.
Determinism + sensitivity to every input field are the two properties that
actually matter — anyone with the public data + our canonical encoding must
reproduce the exact hex we publish on-chain.
"""

from __future__ import annotations

from app.models.poisson import MatchPrediction


def _base_pred() -> MatchPrediction:
    return MatchPrediction(
        p_home_win=0.62,
        p_draw=0.22,
        p_away_win=0.16,
        expected_home_goals=1.9,
        expected_away_goals=0.9,
        top_scorelines=[(2, 1, 0.12), (1, 1, 0.10), (2, 0, 0.09), (1, 0, 0.08), (3, 1, 0.07)],
    )


def test_commitment_is_deterministic_for_same_input():
    from app.onchain.commitment import commitment_hash

    args = dict(
        prediction=_base_pred(),
        match_id=42,
        kickoff_unix=1776600000,
        model_version="poisson-dc-v1",
        rho=-0.1,
    )
    assert commitment_hash(**args) == commitment_hash(**args)


def test_commitment_shape_is_0x_plus_64_hex_chars():
    from app.onchain.commitment import commitment_hash

    h = commitment_hash(
        prediction=_base_pred(),
        match_id=1,
        kickoff_unix=0,
        model_version="x",
        rho=0.0,
    )
    assert h.startswith("0x")
    assert len(h) == 2 + 64
    int(h, 16)  # must parse as hex


def test_commitment_changes_when_any_field_changes():
    from app.onchain.commitment import commitment_hash

    base = commitment_hash(
        prediction=_base_pred(),
        match_id=42,
        kickoff_unix=1776600000,
        model_version="poisson-dc-v1",
        rho=-0.1,
    )

    # Different match_id
    assert commitment_hash(
        prediction=_base_pred(), match_id=43, kickoff_unix=1776600000,
        model_version="poisson-dc-v1", rho=-0.1,
    ) != base

    # Different kickoff
    assert commitment_hash(
        prediction=_base_pred(), match_id=42, kickoff_unix=1776600001,
        model_version="poisson-dc-v1", rho=-0.1,
    ) != base

    # Different rho
    assert commitment_hash(
        prediction=_base_pred(), match_id=42, kickoff_unix=1776600000,
        model_version="poisson-dc-v1", rho=-0.12,
    ) != base

    # Different model_version
    assert commitment_hash(
        prediction=_base_pred(), match_id=42, kickoff_unix=1776600000,
        model_version="poisson-dc-v2", rho=-0.1,
    ) != base

    # Different probabilities (swap H/A)
    from dataclasses import replace
    swapped = replace(
        _base_pred(),
        p_home_win=_base_pred().p_away_win,
        p_away_win=_base_pred().p_home_win,
    )
    assert commitment_hash(
        prediction=swapped, match_id=42, kickoff_unix=1776600000,
        model_version="poisson-dc-v1", rho=-0.1,
    ) != base


def test_commitment_ignores_probability_floating_jitter_below_6dp():
    """Rounding stabilizes the hash against float noise re-running the model."""
    from dataclasses import replace

    from app.onchain.commitment import commitment_hash

    base = commitment_hash(
        prediction=_base_pred(), match_id=42, kickoff_unix=1776600000,
        model_version="poisson-dc-v1", rho=-0.1,
    )
    jittered = replace(
        _base_pred(),
        p_home_win=_base_pred().p_home_win + 1e-10,
        p_draw=_base_pred().p_draw - 1e-10,
    )
    assert commitment_hash(
        prediction=jittered, match_id=42, kickoff_unix=1776600000,
        model_version="poisson-dc-v1", rho=-0.1,
    ) == base
