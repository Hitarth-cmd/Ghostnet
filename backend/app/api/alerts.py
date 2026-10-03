"""
Ecological Alerts API — returns marine-life alerts triggered by detection proximity to
coral reefs, marine protected areas, turtle/whale/dolphin habitats.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.alert import EcologicalAlert
from app.models.detection import Detection

logger = logging.getLogger("ghostnet.api.alerts")

router = APIRouter(prefix="/api/v1/alerts", tags=["ecological-alerts"])


@router.get("")
def list_alerts(
    status: str | None = None,
    severity: str | None = None,
    detection_id: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> dict:
    """List all ecological alerts, optionally filtered."""
    query = db.query(EcologicalAlert)
    if status:
        query = query.filter(EcologicalAlert.status == status)
    if severity:
        query = query.filter(EcologicalAlert.severity == severity)
    if detection_id:
        # Allow external_id or internal detection id
        det = (
            db.query(Detection)
            .filter((Detection.id == detection_id) | (Detection.external_id == detection_id))
            .one_or_none()
        )
        if det:
            query = query.filter(EcologicalAlert.detection_id == det.id)
    alerts = query.order_by(EcologicalAlert.created_at.desc()).limit(limit).all()
    return {
        "total": len(alerts),
        "alerts": [a.to_dict() for a in alerts],
    }


@router.get("/active")
def get_active_alerts(db: Session = Depends(get_db)) -> dict:
    """Return only active (unacknowledged) alerts, sorted by severity."""
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    alerts = (
        db.query(EcologicalAlert)
        .filter(EcologicalAlert.status == "active")
        .all()
    )
    alerts.sort(key=lambda a: severity_order.get(a.severity, 99))
    return {
        "total_active": len(alerts),
        "critical": sum(1 for a in alerts if a.severity == "CRITICAL"),
        "high": sum(1 for a in alerts if a.severity == "HIGH"),
        "alerts": [a.to_dict() for a in alerts],
    }


@router.get("/{alert_id}")
def get_alert(alert_id: str, db: Session = Depends(get_db)) -> dict:
    alert = db.query(EcologicalAlert).filter(EcologicalAlert.id == alert_id).one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert.to_dict()


@router.post("/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, db: Session = Depends(get_db)) -> dict:
    alert = db.query(EcologicalAlert).filter(EcologicalAlert.id == alert_id).one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = "acknowledged"
    db.commit()
    return {"id": alert_id, "status": "acknowledged"}


@router.post("/{alert_id}/resolve")
def resolve_alert(alert_id: str, db: Session = Depends(get_db)) -> dict:
    alert = db.query(EcologicalAlert).filter(EcologicalAlert.id == alert_id).one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = "resolved"
    db.commit()
    return {"id": alert_id, "status": "resolved"}


@router.get("/map/geojson")
def alerts_geojson(db: Session = Depends(get_db)) -> dict:
    """GeoJSON FeatureCollection of active alert impact points for map overlay."""
    alerts = (
        db.query(EcologicalAlert)
        .filter(EcologicalAlert.status.in_(["active", "acknowledged"]))
        .all()
    )
    features = []
    for a in alerts:
        if a.impact_point_geometry:
            features.append({
                "type": "Feature",
                "geometry": a.impact_point_geometry,
                "properties": {
                    "id": a.id,
                    "alert_type": a.alert_type,
                    "severity": a.severity,
                    "status": a.status,
                    "headline": a.headline,
                    "region_name": a.region_name,
                    "feature_type": a.feature_type,
                    "species_at_risk": a.species_at_risk,
                    "distance_km": a.distance_km,
                    "detection_id": a.external_id,
                    "recommended_action": a.recommended_action,
                },
            })
    return {"type": "FeatureCollection", "features": features}
