from __future__ import annotations

import logging

from shapely.geometry import shape
from sqlalchemy.orm import Session

from app.drift.schemas import DriftRequest
from app.drift.trajectory import forecast_drift
from app.geospatial.alert_engine import generate_ecological_alerts
from app.geospatial.spatial_queries import analyze_geometry
from app.models.alert import EcologicalAlert
from app.models.detection import Detection
from app.models.other import Report, RiskAssessment, Trajectory
from app.orchestrator.schemas import AnalysisResult
from app.prioritization.priority_engine import PriorityInputs, compute_priority
from app.reporting.report_generator import generate_report
from app.risk.features import RiskFeatureInputs
from app.risk.risk_engine import assess_risk

logger = logging.getLogger("ghostnet.orchestrator")


class DetectionNotFoundError(Exception):
    pass


def analyze_detection(db: Session, detection_id: str) -> AnalysisResult:
    """
    Full multi-agent pipeline:
      1. get detection
      2. drift agent — 24h/48h/72h particle ensemble + uncertainty polygon
      3. geospatial agent — MPA/habitat/coastline spatial analysis
      4. risk agent — deterministic weighted risk scoring
      5. prioritization — urgency ranking
      6. ecological alert agent — coral reefs / MPAs / species habitats
      7. RAG agent — evidence retrieval + report narration
      8. persist everything to database
    """
    detection = db.query(Detection).filter(Detection.id == detection_id).one_or_none()
    if detection is None:
        detection = db.query(Detection).filter(Detection.external_id == detection_id).one_or_none()
    if detection is None:
        raise DetectionNotFoundError(detection_id)

    logger.info("[DETECTION] id=%s external_id=%s starting analysis", detection.id, detection.external_id)

    # --- DRIFT AGENT ---
    from app.config import get_settings
    settings = get_settings()

    drift_request = DriftRequest(
        detection_id=detection.external_id,
        latitude=detection.latitude,
        longitude=detection.longitude,
        start_time=detection.timestamp,
        ocean_data_provider=settings.OCEAN_DATA_PROVIDER,
    )
    drift_result = forecast_drift(drift_request)
    logger.info("[DRIFT] id=%s horizons=%s mode=%s provider=%s", detection.external_id,
                [h.forecast_hour for h in drift_result.horizons], drift_result.mode, settings.OCEAN_DATA_PROVIDER)

    # Persist each horizon as a Trajectory row.
    db.query(Trajectory).filter(Trajectory.detection_id == detection.id).delete()
    for h in drift_result.horizons:
        db.add(
            Trajectory(
                detection_id=detection.id,
                forecast_hour=h.forecast_hour,
                mode=drift_result.mode,
                position_geometry=h.position_geometry,
                uncertainty_geometry=h.uncertainty_geometry,
                particle_geometry=h.particle_geometry,
                timestamp=h.timestamp,
            )
        )

    # --- GEOSPATIAL AGENT ---
    final_horizon = max(drift_result.horizons, key=lambda h: h.forecast_hour)
    geospatial_summary = analyze_geometry(
        final_horizon.uncertainty_geometry, final_horizon.mean_latitude, final_horizon.mean_longitude
    )
    logger.info("[SPATIAL] id=%s mpa_overlap=%s habitat_overlap=%s", detection.external_id,
                geospatial_summary["protected_area_overlap"], geospatial_summary["habitat_overlap"])

    poly = shape(final_horizon.uncertainty_geometry)
    uncertainty_area_km2 = poly.area * (111.32**2)

    # --- RISK AGENT ---
    risk_inputs = RiskFeatureInputs(
        detection_confidence=detection.confidence,
        protected_area_overlap=geospatial_summary["protected_area_overlap"],
        habitat_overlap=geospatial_summary["habitat_overlap"],
        species_habitat_overlap=bool(geospatial_summary["habitat_kinds"]),
        distance_to_coastline_km=geospatial_summary["distance_to_coastline_km"],
        forecast_uncertainty_area_km2=uncertainty_area_km2,
        scene_id=detection.scene_id,
    )
    risk_result = assess_risk(detection.external_id, risk_inputs)
    logger.info("[RISK] id=%s score=%s level=%s", detection.external_id,
                risk_result.risk_score, risk_result.risk_level.value)

    priority_result = compute_priority(
        detection.external_id,
        PriorityInputs(
            risk_score=risk_result.risk_score,
            detection_confidence=detection.confidence,
            estimated_time_to_protected_area_hours=geospatial_summary["estimated_time_to_protected_area_hours"],
            protected_area_overlap=geospatial_summary["protected_area_overlap"],
            habitat_overlap=geospatial_summary["habitat_overlap"],
            forecast_uncertainty=risk_result.feature_values["forecast_uncertainty"],
        ),
    )
    logger.info("[PRIORITY] id=%s level=%s", detection.external_id, priority_result.priority_level.value)

    db.query(RiskAssessment).filter(RiskAssessment.detection_id == detection.id).delete()
    db.add(
        RiskAssessment(
            detection_id=detection.id,
            risk_score=risk_result.risk_score,
            risk_level=risk_result.risk_level.value,
            feature_values=risk_result.feature_values,
            feature_contributions=risk_result.feature_contributions,
            reason_codes=risk_result.reason_codes,
            priority_rank=priority_result.priority_rank,
            priority_level=priority_result.priority_level.value,
            recommended_action=priority_result.recommended_action,
        )
    )

    # --- ECOLOGICAL ALERT AGENT ---
    drift_horizons_for_alerts = [
        {
            "forecast_hour": h.forecast_hour,
            "mean_lat": h.mean_latitude,
            "mean_lon": h.mean_longitude,
            "uncertainty_geometry": h.uncertainty_geometry,
        }
        for h in drift_result.horizons
    ]
    try:
        alert_records = generate_ecological_alerts(
            detection_id=detection.id,
            external_id=detection.external_id,
            latitude=detection.latitude,
            longitude=detection.longitude,
            confidence=detection.confidence,
            drift_horizons=drift_horizons_for_alerts,
        )
        db.query(EcologicalAlert).filter(EcologicalAlert.detection_id == detection.id).delete()
        for a in alert_records:
            db.add(EcologicalAlert(
                detection_id=a["detection_id"],
                external_id=a["external_id"],
                alert_type=a["alert_type"],
                severity=a["severity"],
                status=a["status"],
                headline=a["headline"],
                details=a["details"],
                region_name=a["region_name"],
                feature_type=a["feature_type"],
                species_at_risk=a["species_at_risk"],
                distance_km=a["distance_km"],
                estimated_impact_hours=a["estimated_impact_hours"],
                impact_point_geometry=a["impact_point_geometry"],
                recommended_action=a["recommended_action"],
                source_citation=a["source_citation"],
            ))
        logger.info("[ALERTS] id=%s generated %d ecological alerts", detection.external_id, len(alert_records))
    except Exception as exc:
        logger.error("[ALERTS] id=%s alert generation failed: %s", detection.external_id, exc)
        alert_records = []

    # --- RAG + REPORT AGENT ---
    detection_summary = {
        "external_id": detection.external_id,
        "object_class": detection.object_class,
        "confidence": detection.confidence,
        "status": detection.status,
        "latitude": detection.latitude,
        "longitude": detection.longitude,
        "timestamp": detection.timestamp.isoformat(),
    }
    drift_summary = {
        "mode": drift_result.mode,
        "horizons": [
            {
                "forecast_hour": h.forecast_hour,
                "timestamp": h.timestamp.isoformat(),
                "latitude": h.mean_latitude,
                "longitude": h.mean_longitude,
            }
            for h in drift_result.horizons
        ],
    }
    report = generate_report(
        detection=detection_summary,
        drift_summary=drift_summary,
        geospatial_summary=geospatial_summary,
        risk_summary=risk_result.model_dump(mode="json"),
        priority_summary=priority_result.model_dump(mode="json"),
    )
    logger.info("[RAG] id=%s evidence_chunks=%d", detection.external_id, len(report.evidence))
    logger.info("[REPORT] id=%s generated", detection.external_id)

    db.query(Report).filter(Report.detection_id == detection.id).delete()
    db.add(Report(detection_id=detection.id, content=report.model_dump(mode="json")))

    db.commit()
    logger.info("[DATABASE] id=%s persisted trajectories/risk/alerts/report", detection.external_id)

    return AnalysisResult(
        detection_id=detection.external_id,
        drift=drift_result,
        geospatial=geospatial_summary,
        risk=risk_result.model_dump(mode="json"),
        priority=priority_result.model_dump(mode="json"),
        report=report,
    )
