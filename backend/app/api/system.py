from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.detection.factory import get_detection_provider
from app.models.detection import Detection

router = APIRouter(tags=["system"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # noqa: BLE001
        db_ok = False
    return {"status": "healthy" if db_ok else "degraded", "database": "ok" if db_ok else "unreachable"}


@router.get("/api/v1/system/status")
def system_status(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    provider = get_detection_provider()
    detection_count = db.query(Detection).count()
    return {
        "app_env": settings.APP_ENV,
        "data_mode": settings.DATA_MODE,
        "model_provider": provider.name,
        "ocean_data_provider": settings.OCEAN_DATA_PROVIDER,
        "llm_provider": settings.LLM_PROVIDER,
        "vector_store": settings.VECTOR_STORE,
        "job_backend": settings.JOB_BACKEND,
        "detections_in_database": detection_count,
    }
