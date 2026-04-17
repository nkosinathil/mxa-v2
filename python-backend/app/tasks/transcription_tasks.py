"""
Transcription task stubs.

These lightweight tasks keep Celery imports/routing compatible when
transcription processing is not yet fully implemented.
"""

from app.tasks.celery_app import celery_app
from app.core.logging import logger


@celery_app.task(bind=True)
def process_transcription_task(self, job_id: str, payload: dict | None = None):
    """Placeholder transcription task for worker startup compatibility."""
    logger.info("Transcription placeholder task invoked for job %s", job_id)
    return {
        "job_id": job_id,
        "status": "skipped",
        "reason": "transcription task not implemented yet",
        "payload": payload or {},
    }
