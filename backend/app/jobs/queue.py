from __future__ import annotations

import logging
import threading

from app.config import get_settings

logger = logging.getLogger("ghostnet.jobs.queue")


class JobQueue:
    def enqueue_analysis(self, job_id: str, detection_id: str) -> None:
        raise NotImplementedError


class InlineThreadJobQueue(JobQueue):
    """
    Default job backend. Runs the job on a background Python thread so
    the HTTP request returns immediately with a job_id, without requiring
    Redis or a Celery worker process to be running. This is what makes
    `docker compose up` (or even just `uvicorn app.main:app`) sufficient
    to exercise the full asynchronous job API in DEMO mode.
    """

    def enqueue_analysis(self, job_id: str, detection_id: str) -> None:
        from app.jobs.tasks import run_analysis_job

        thread = threading.Thread(
            target=run_analysis_job, args=(job_id, detection_id), daemon=True
        )
        thread.start()


class CeleryJobQueue(JobQueue):  # pragma: no cover - requires a running Redis + worker
    """
    Production job backend. Requires REDIS_URL to point at a running
    Redis instance and a Celery worker process
    (`celery -A app.jobs.celery_app worker`) to be running - both are
    wired in docker-compose.yml as the `redis` and `worker` services.
    """

    def enqueue_analysis(self, job_id: str, detection_id: str) -> None:
        from app.jobs.celery_app import celery_analysis_task

        celery_analysis_task.delay(job_id, detection_id)


def get_job_queue() -> JobQueue:
    settings = get_settings()
    if settings.JOB_BACKEND == "redis" and settings.REDIS_URL:
        return CeleryJobQueue()
    return InlineThreadJobQueue()
