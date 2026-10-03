from __future__ import annotations

from app.models.enums import RiskLevel
from app.prioritization.priority_engine import PriorityInputs, compute_priority, rank_detections
from app.risk.features import RiskFeatureInputs
from app.risk.risk_engine import assess_risk


def test_risk_score_increases_with_mpa_and_habitat_overlap():
    low_inputs = RiskFeatureInputs(
        detection_confidence=0.6,
        protected_area_overlap=False,
        habitat_overlap=False,
        species_habitat_overlap=False,
        distance_to_coastline_km=100.0,
        forecast_uncertainty_area_km2=10.0,
        scene_id="scene-a",
    )
    high_inputs = RiskFeatureInputs(
        detection_confidence=0.6,
        protected_area_overlap=True,
        habitat_overlap=True,
        species_habitat_overlap=True,
        distance_to_coastline_km=100.0,
        forecast_uncertainty_area_km2=10.0,
        scene_id="scene-a",
    )
    low_result = assess_risk("DET-LOW", low_inputs)
    high_result = assess_risk("DET-HIGH", high_inputs)
    assert high_result.risk_score > low_result.risk_score


def test_risk_reason_codes_include_protected_area_overlap():
    inputs = RiskFeatureInputs(
        detection_confidence=0.9,
        protected_area_overlap=True,
        habitat_overlap=True,
        species_habitat_overlap=False,
        distance_to_coastline_km=5.0,
        forecast_uncertainty_area_km2=5.0,
        scene_id="scene-b",
    )
    result = assess_risk("DET-REASONS", inputs)
    assert "trajectory_intersects_protected_area" in result.reason_codes
    assert "habitat_overlap" in result.reason_codes


def test_risk_level_is_a_valid_enum_member():
    inputs = RiskFeatureInputs(
        detection_confidence=0.9,
        protected_area_overlap=True,
        habitat_overlap=True,
        species_habitat_overlap=True,
        distance_to_coastline_km=1.0,
        forecast_uncertainty_area_km2=1.0,
        scene_id="scene-c",
    )
    result = assess_risk("DET-VALID", inputs)
    assert result.risk_level in list(RiskLevel)


def test_priority_critical_for_high_risk_near_mpa():
    inputs = PriorityInputs(
        risk_score=0.85,
        detection_confidence=0.9,
        estimated_time_to_protected_area_hours=10.0,
        protected_area_overlap=True,
        habitat_overlap=True,
        forecast_uncertainty=0.7,
    )
    result = compute_priority("DET-CRIT", inputs)
    assert result.priority_level.value in ("HIGH", "CRITICAL")


def test_rank_detections_orders_by_level():
    from app.models.enums import PriorityLevel
    from app.prioritization.schemas import PriorityOut

    items = [
        PriorityOut(detection_id="a", priority_rank=0, priority_level=PriorityLevel.LOW,
                    recommended_action="", contributing_factors=[]),
        PriorityOut(detection_id="b", priority_rank=0, priority_level=PriorityLevel.CRITICAL,
                    recommended_action="", contributing_factors=[]),
        PriorityOut(detection_id="c", priority_rank=0, priority_level=PriorityLevel.MEDIUM,
                    recommended_action="", contributing_factors=[]),
    ]
    ranked = rank_detections(items)
    assert [p.detection_id for p in ranked] == ["b", "c", "a"]
    assert ranked[0].priority_rank == 1
