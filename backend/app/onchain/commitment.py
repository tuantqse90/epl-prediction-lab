"""Deterministic SHA-256 commitment hash for a prediction.

The hash is the cryptographic payload we publish on-chain. Any third party
given the prediction body + the canonical encoding rules below must reproduce
the exact hex we stored, and block.timestamp of the publishing tx then proves
our model view pre-dates kickoff.

Fields are serialized as a sorted-key, minimum-whitespace JSON document, with
all probabilities rounded to 6 decimal places so floating-point noise between
re-runs doesn't perturb the hash.
"""

from __future__ import annotations

import hashlib
import json

from app.models.poisson import MatchPrediction

COMMITMENT_SCHEMA_VERSION = 1
_PROB_DP = 6


def _round(x: float) -> float:
    return round(float(x), _PROB_DP)


def canonical_payload(
    *,
    prediction: MatchPrediction,
    match_id: int,
    kickoff_unix: int,
    model_version: str,
    rho: float,
) -> str:
    top = prediction.top_scorelines[0] if prediction.top_scorelines else (0, 0, 0.0)
    body = {
        "v": COMMITMENT_SCHEMA_VERSION,
        "match_id": int(match_id),
        "kickoff_unix": int(kickoff_unix),
        "model_version": str(model_version),
        "rho": _round(rho),
        "p_home_win": _round(prediction.p_home_win),
        "p_draw": _round(prediction.p_draw),
        "p_away_win": _round(prediction.p_away_win),
        "expected_home_goals": _round(prediction.expected_home_goals),
        "expected_away_goals": _round(prediction.expected_away_goals),
        "top_scoreline": [int(top[0]), int(top[1]), _round(top[2])],
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":"))


def commitment_hash(
    *,
    prediction: MatchPrediction,
    match_id: int,
    kickoff_unix: int,
    model_version: str,
    rho: float,
) -> str:
    payload = canonical_payload(
        prediction=prediction,
        match_id=match_id,
        kickoff_unix=kickoff_unix,
        model_version=model_version,
        rho=rho,
    )
    return "0x" + hashlib.sha256(payload.encode("utf-8")).hexdigest()
