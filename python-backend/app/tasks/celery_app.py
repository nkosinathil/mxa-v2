"""
Celery Application Configuration

Sets up Celery for background task processing.
"""

from celery import Celery

from app.core.config import settings

# Create Celery application
celery_app = Celery(
    'mxa_mobile',
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=['app.tasks.processing_tasks', 'app.tasks.ocr_tasks', 'app.tasks.transcription_tasks']
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.celery_task_time_limit,
    task_soft_time_limit=settings.celery_task_soft_time_limit,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Task routing
celery_app.conf.task_routes = {
    'app.tasks.processing_tasks.*': {'queue': settings.celery_queue_name},
    'app.tasks.ocr_tasks.*': {'queue': settings.celery_queue_name},
    'app.tasks.transcription_tasks.*': {'queue': settings.celery_queue_name},
}
