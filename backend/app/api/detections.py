from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.jobs.queue import get_job_queue
from app.models.detection import Detection
from app.models.other import Job, Report, RiskAssessment, Trajectory
from app.orchestrator.pipeline import DetectionNotFoundError, analyze_detection
from app.schemas.detection import DetectionCreate, DetectionListOut, DetectionOut

router = APIRouter(prefix="/api/v1/detections", tags=["detections"])


@router.get("", response_model=DetectionListOut)
def list_detections(
    status: str | None = None,
    object_class: str | None = None,
    db: Session = Depends(get_db),
) -> DetectionListOut:
    query = db.query(Detection)
    if status:
        query = query.filter(Detection.status == status)
    if object_class:
        query = query.filter(Detection.object_class == object_class)
    items = query.order_by(Detection.timestamp.desc()).all()
    return DetectionListOut(total=len(items), items=[DetectionOut.model_validate(d) for d in items])


@router.get("/{detection_id}", response_model=DetectionOut)
def get_detection(detection_id: str, db: Session = Depends(get_db)) -> DetectionOut:
    detection = (
        db.query(Detection)
        .filter((Detection.id == detection_id) | (Detection.external_id == detection_id))
        .one_or_none()
    )
    if detection is None:
        raise HTTPException(status_code=404, detail=f"Detection '{detection_id}' not found")
    return DetectionOut.model_validate(detection)


@router.post("", response_model=DetectionOut, status_code=201)
def create_detection(payload: DetectionCreate, db: Session = Depends(get_db)) -> DetectionOut:
    external_id = payload.external_id or f"MANUAL-{uuid.uuid4().hex[:8].upper()}"
    existing = db.query(Detection).filter(Detection.external_id == external_id).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"Detection '{external_id}' already exists")

    detection = Detection(
        external_id=external_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        geometry={"type": "Point", "coordinates": [payload.longitude, payload.latitude]},
        confidence=payload.confidence,
        object_class=payload.object_class.value,
        status=payload.status.value,
        timestamp=payload.timestamp or dt.datetime.utcnow(),
        source=payload.source,
        scene_id=payload.scene_id,
        area_m2=payload.area_m2,
    )
    db.add(detection)
    db.commit()
    db.refresh(detection)
    return DetectionOut.model_validate(detection)


@router.post("/{detection_id}/analyze")
def analyze(detection_id: str, sync: bool = False, db: Session = Depends(get_db)) -> dict:
    """
    Trigger the full analysis pipeline for a detection.

    sync=true runs the pipeline synchronously and returns the complete
    result immediately (useful for simple/manual testing). Otherwise a
    background job is enqueued and a job_id is returned right away -
    poll GET /api/v1/jobs/{job_id} for status/result.
    """
    detection = (
        db.query(Detection)
        .filter((Detection.id == detection_id) | (Detection.external_id == detection_id))
        .one_or_none()
    )
    if detection is None:
        raise HTTPException(status_code=404, detail=f"Detection '{detection_id}' not found")

    if sync:
        try:
            result = analyze_detection(db, detection.external_id)
        except DetectionNotFoundError:
            raise HTTPException(status_code=404, detail="Detection not found") from None
        return result.model_dump(mode="json")

    job = Job(job_type="analyze_detection", status="queued", payload={"detection_id": detection.external_id})
    db.add(job)
    db.commit()
    db.refresh(job)

    get_job_queue().enqueue_analysis(job.id, detection.external_id)
    return {"job_id": job.id, "status": job.status}


@router.get("/{detection_id}/drift")
def get_drift(detection_id: str, db: Session = Depends(get_db)) -> dict:
    detection = (
        db.query(Detection)
        .filter((Detection.id == detection_id) | (Detection.external_id == detection_id))
        .one_or_none()
    )
    if detection is None:
        raise HTTPException(status_code=404, detail="Detection not found")
    trajectories = db.query(Trajectory).filter(Trajectory.detection_id == detection.id).all()
    if not trajectories:
        raise HTTPException(status_code=404, detail="No drift result yet - call analyze first")
    return {
        "detection_id": detection.external_id,
        "horizons": [
            {
                "forecast_hour": t.forecast_hour,
                "mode": t.mode,
                "timestamp": t.timestamp.isoformat(),
                "position_geometry": t.position_geometry,
                "uncertainty_geometry": t.uncertainty_geometry,
            }
            for t in sorted(trajectories, key=lambda t: t.forecast_hour)
        ],
    }


@router.get("/{detection_id}/risk")
def get_risk(detection_id: str, db: Session = Depends(get_db)) -> dict:
    detection = (
        db.query(Detection)
        .filter((Detection.id == detection_id) | (Detection.external_id == detection_id))
        .one_or_none()
    )
    if detection is None:
        raise HTTPException(status_code=404, detail="Detection not found")
    risk = db.query(RiskAssessment).filter(RiskAssessment.detection_id == detection.id).one_or_none()
    if risk is None:
        raise HTTPException(status_code=404, detail="No risk assessment yet - call analyze first")
    return {
        "detection_id": detection.external_id,
        "risk_score": risk.risk_score,
        "risk_level": risk.risk_level,
        "feature_values": risk.feature_values,
        "feature_contributions": risk.feature_contributions,
        "reason_codes": risk.reason_codes,
        "priority_level": risk.priority_level,
        "recommended_action": risk.recommended_action,
    }


@router.get("/{detection_id}/report")
def get_report(detection_id: str, db: Session = Depends(get_db)) -> dict:
    detection = (
        db.query(Detection)
        .filter((Detection.id == detection_id) | (Detection.external_id == detection_id))
        .one_or_none()
    )
    if detection is None:
        raise HTTPException(status_code=404, detail="Detection not found")
    report = db.query(Report).filter(Report.detection_id == detection.id).one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="No report yet - call analyze first")
    return report.content
