from __future__ import annotations

import os

import yaml

from app.risk.features import RiskFeatureInputs, compute_raw_features
from app.risk.schemas import RiskAssessmentOut
from app.risk.scoring import classify_risk, derive_reason_codes, weighted_score

_CONFIG_CACHE: dict | None = None


def _load_risk_config() -> dict:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    path = os.environ.get(
        "GHOSTNET_RISK_CONFIG",
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "configs", "risk.yaml"),
    )
    with open(path, encoding="utf-8") as f:
        _CONFIG_CACHE = yaml.safe_load(f)
    return _CONFIG_CACHE


def assess_risk(detection_id: str, inputs: RiskFeatureInputs) -> RiskAssessmentOut:
    """
    Deterministic, fully explainable risk scoring. This function - not an
    LLM - computes the numeric risk score. Any LLM/report step downstream
    may only narrate this result, never recompute or override it.
    """
    config = _load_risk_config()
    features = compute_raw_features(inputs, config["coastline_proximity_max_km"])
    score, contributions = weighted_score(features, config["weights"])
    level = classify_risk(score, config["thresholds"])
    reasons = derive_reason_codes(features)

    return RiskAssessmentOut(
        detection_id=detection_id,
        risk_score=score,
        risk_level=level,
        feature_values=features,
        feature_contributions=contributions,
        reason_codes=reasons,
    )
