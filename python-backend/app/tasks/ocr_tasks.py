"""
OCR Celery tasks.

This module intentionally provides a minimal task implementation so that
Celery worker startup does not fail when OCR-specific pipelines are not yet
implemented on this branch.
"""

from app.tasks.celery_app import celery_app
from app.core.logging import logger


@celery_app.task(bind=True)
def run_ocr_task(self, job_id: str, payload: dict | None = None):
    """
    Placeholder OCR task.

    Keeps queue processing functional until full OCR pipeline tasks are
    implemented.
    """
    logger.warning(
        "run_ocr_task placeholder executed for job_id=%s; OCR pipeline not implemented.",
        job_id,
    )
    return {
        "job_id": job_id,
        "status": "skipped",
        "reason": "ocr task placeholder",
        "payload": payload or {},
    }
