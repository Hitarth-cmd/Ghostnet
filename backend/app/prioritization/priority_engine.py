from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import PriorityLevel
from app.prioritization.schemas import PriorityOut

_ACTIONS = {
    PriorityLevel.CRITICAL: "Immediate verification / cleanup planning recommended.",
    PriorityLevel.HIGH: "Prioritize monitoring and schedule verification soon.",
    PriorityLevel.MEDIUM: "Add to monitoring queue; re-check on next overpass.",
    PriorityLevel.LOW: "Routine observation; no immediate action required.",
}

# These are decision-support recommendations only, not official
# operational instructions - enforced in wording above and repeated in
# the generated report / README.


@dataclass
class PriorityInputs:
    risk_score: float
    detection_confidence: float
    estimated_time_to_protected_area_hours: float
    protected_area_overlap: bool
    habitat_overlap: bool
    forecast_uncertainty: float  # 0-1, higher = more uncertain


def _score_to_level(score: float) -> PriorityLevel:
    if score >= 0.80:
        return PriorityLevel.CRITICAL
    if score >= 0.60:
        return PriorityLevel.HIGH
    if score >= 0.35:
        return PriorityLevel.MEDIUM
    return PriorityLevel.LOW


def compute_priority(detection_id: str, inputs: PriorityInputs, batch_rank: int = 1) -> PriorityOut:
    urgency_bonus = 0.0
    factors: list[str] = []

    if inputs.protected_area_overlap:
        urgency_bonus += 0.10
        factors.append("protected_area_intersection")
    if inputs.habitat_overlap:
        urgency_bonus += 0.05
        factors.append("habitat_intersection")
    if inputs.estimated_time_to_protected_area_hours < 48:
        urgency_bonus += 0.05
        factors.append("short_time_to_sensitive_area")
    if inputs.detection_confidence >= 0.8:
        factors.append("high_detection_confidence")
    if inputs.forecast_uncertainty >= 0.6:
        factors.append("high_forecast_uncertainty")

    combined = min(1.0, inputs.risk_score + urgency_bonus)
    level = _score_to_level(combined)

    return PriorityOut(
        detection_id=detection_id,
        priority_rank=batch_rank,
        priority_level=level,
        recommended_action=_ACTIONS[level],
        contributing_factors=factors,
    )


def rank_detections(priorities: list[PriorityOut]) -> list[PriorityOut]:
    """Sort a batch of priorities highest-first and assign priority_rank."""
    level_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    ordered = sorted(priorities, key=lambda p: level_order[p.priority_level.value])
    for i, p in enumerate(ordered, start=1):
        p.priority_rank = i
    return ordered
