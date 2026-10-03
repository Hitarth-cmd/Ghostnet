"""
Celery application for production background processing.

Not exercised in the sandboxed DEMO environment (no Redis broker
available there), but fully wired for real deployment: start Redis, then

    celery -A app.jobs.celery_app worker --loglevel=info

and set JOB_BACKEND=redis, REDIS_URL=redis://<host>:6379/0.
"""
from __future__ import annotations

from celery import Celery

from app.config import get_settings

settings = get_settings()
celery_app = Celery(
    "ghostnet",
    broker=settings.REDIS_URL or "redis://localhost:6379/0",
    backend=settings.REDIS_URL or "redis://localhost:6379/0",
)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]


@celery_app.task(name="ghostnet.run_analysis")
def celery_analysis_task(job_id: str, detection_id: str) -> None:
    from app.jobs.tasks import run_analysis_job

    run_analysis_job(job_id, detection_id)
