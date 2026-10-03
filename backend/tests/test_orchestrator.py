from __future__ import annotations

import pytest

from app.orchestrator.pipeline import DetectionNotFoundError, analyze_detection
from app.seed import seed_demo_data


def test_analyze_detection_full_pipeline(db_session):
    seed_demo_data(db_session)
    result = analyze_detection(db_session, "DEMO-001")

    assert result.detection_id == "DEMO-001"
    assert len(result.drift.horizons) == 3
    assert "protected_area_overlap" in result.geospatial
    assert result.risk["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert result.priority["priority_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert result.report.summary
    assert len(result.report.limitations) > 0


def test_analyze_detection_unknown_id_raises(db_session):
    seed_demo_data(db_session)
    with pytest.raises(DetectionNotFoundError):
        analyze_detection(db_session, "DOES-NOT-EXIST")


def test_end_to_end_demo_pipeline_all_stages_succeed(db_session):
    """
    Integration test required by spec: mock detection -> drift -> geospatial
    -> risk -> priority -> RAG -> report, asserting every stage succeeds.
    """
    seed_demo_data(db_session)
    result = analyze_detection(db_session, "DEMO-003")

    # detection
    assert result.detection_id == "DEMO-003"
    # drift
    assert all(h.forecast_hour in (24, 48, 72) for h in result.drift.horizons)
    # geospatial
    assert isinstance(result.geospatial["protected_area_overlap"], bool)
    # risk
    assert 0.0 <= result.risk["risk_score"] <= 1.0
    # priority
    assert result.priority["priority_rank"] >= 1
    # RAG
    assert isinstance(result.report.evidence, list)
    # report
    assert result.report.detection_id == "DEMO-003"
