from __future__ import annotations

import logging
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal, get_db
from app.detection.providers.model import Sentinel2ModelProvider
from app.models.detection import Detection
from app.models.other import Job

router = APIRouter(prefix="/api/v1/inference", tags=["inference"])
logger = logging.getLogger("ghostnet.inference")

_UPLOAD_DIR = os.environ.get("GHOSTNET_UPLOAD_DIR", "/tmp/ghostnet_uploads")


def _run_sentinel2_job(job_id: str, file_path: str) -> None:
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).one()
        job.status = "running"
        db.commit()

        provider = Sentinel2ModelProvider()
        records = provider.run_on_geotiff(file_path)

        for record in records:
            detection = Detection(
                external_id=record.external_id,
                latitude=record.latitude,
                longitude=record.longitude,
                geometry=record.geometry,
                confidence=record.confidence,
                object_class=record.object_class.value,
                status=record.status.value,
                timestamp=record.timestamp,
                source=record.source,
                scene_id=record.scene_id,
                area_m2=record.area_m2,
            )
            db.add(detection)

        job = db.query(Job).filter(Job.id == job_id).one()
        job.status = "completed"
        job.progress = 1.0
        job.result = {"detections_created": len(records)}
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        job = db.query(Job).filter(Job.id == job_id).one_or_none()
        if job is not None:
            job.status = "failed"
            job.error = str(exc)
            db.commit()
        logger.exception("[INFERENCE] job=%s failed", job_id)
    finally:
        db.close()


@router.post("/sentinel2")
async def infer_sentinel2(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    """
    Upload a Sentinel-2 GeoTIFF scene for real-model inference.

    Requires MODEL_PROVIDER=sentinel2 and a configured trained checkpoint
    (see README "Model integration"). Without a checkpoint installed,
    this endpoint still accepts and validates the upload, but the
    resulting job will fail with a clear ModelNotConfiguredError - it
    never fabricates detections.
    """
    settings = get_settings()

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {settings.ALLOWED_UPLOAD_EXTENSIONS}",
        )

    os.makedirs(_UPLOAD_DIR, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(_UPLOAD_DIR, safe_name)

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    size = 0
    with open(dest_path, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                out.close()
                os.remove(dest_path)
                raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_MB}MB limit")
            out.write(chunk)

    job = Job(job_type="sentinel2_inference", status="queued", payload={"file": safe_name})
    db.add(job)
    db.commit()
    db.refresh(job)

    import threading

    threading.Thread(target=_run_sentinel2_job, args=(job.id, dest_path), daemon=True).start()

    return {"job_id": job.id, "status": job.status}
