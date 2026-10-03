from __future__ import annotations

from app.models.enums import RiskLevel

_REASON_LABELS = {
    "protected_area_overlap": "trajectory_intersects_protected_area",
    "habitat_overlap": "habitat_overlap",
    "species_habitat_overlap": "species_habitat_overlap",
    "detection_confidence": "high_detection_confidence",
    "coastline_proximity": "near_coastline",
    "fishing_activity": "elevated_fishing_activity_area",
    "forecast_uncertainty": "high_forecast_uncertainty",
    "trajectory_confidence": "low_trajectory_confidence",
}

# Features above this normalized value are considered a meaningful
# contributor and included in reason_codes.
_REASON_THRESHOLD = 0.5


def weighted_score(features: dict[str, float], weights: dict[str, float]) -> tuple[float, dict[str, float]]:
    """
    Deterministic weighted sum, normalized by total weight used. The LLM
    never touches this calculation - see app/risk/risk_engine.py.
    """
    total_weight = sum(weights.get(k, 0.0) for k in features)
    if total_weight == 0:
        return 0.0, {k: 0.0 for k in features}

    contributions = {}
    weighted_sum = 0.0
    for key, value in features.items():
        w = weights.get(key, 0.0)
        contribution = (value * w) / total_weight
        contributions[key] = round(contribution, 4)
        weighted_sum += contribution

    return round(weighted_sum, 4), contributions


def classify_risk(score: float, thresholds: dict[str, float]) -> RiskLevel:
    ordered = sorted(thresholds.items(), key=lambda kv: kv[1])
    level = RiskLevel.LOW
    for name, cutoff in ordered:
        if score >= cutoff:
            level = RiskLevel(name)
    return level


def derive_reason_codes(features: dict[str, float]) -> list[str]:
    reasons = []
    for key, value in features.items():
        if key == "trajectory_confidence":
            if value < _REASON_THRESHOLD:
                reasons.append(_REASON_LABELS[key])
            continue
        if value >= _REASON_THRESHOLD and key in _REASON_LABELS:
            reasons.append(_REASON_LABELS[key])
    return reasons
