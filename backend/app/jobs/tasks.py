from __future__ import annotations

import logging

from app.database import SessionLocal
from app.models.other import Job
from app.orchestrator.pipeline import analyze_detection

logger = logging.getLogger("ghostnet.jobs")


def run_analysis_job(job_id: str, detection_id: str) -> None:
    """
    Execute analyze_detection for a background job, updating the Job row's
    status/progress/result as it goes. Uses its own DB session because it
    may run on a separate thread (inline queue) or a separate worker
    process (Celery).
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).one()
        job.status = "running"
        job.progress = 0.1
        db.commit()

        result = analyze_detection(db, detection_id)

        job = db.query(Job).filter(Job.id == job_id).one()
        job.status = "completed"
        job.progress = 1.0
        job.result = {"detection_id": result.detection_id, "risk_level": result.risk["risk_level"]}
        db.commit()
        logger.info("[JOB] id=%s completed for detection=%s", job_id, detection_id)
    except Exception as exc:  # noqa: BLE001 - job errors must be recorded, never swallowed
        db.rollback()
        job = db.query(Job).filter(Job.id == job_id).one_or_none()
        if job is not None:
            job.status = "failed"
            job.error = str(exc)
            db.commit()
        logger.exception("[JOB] id=%s failed for detection=%s", job_id, detection_id)
        raise
    finally:
        db.close()
