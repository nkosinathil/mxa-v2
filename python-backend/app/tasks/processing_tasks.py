"""
Processing Tasks

Main Celery tasks for evidence processing.
Wraps the legacy forensic_toolkit logic.
"""

from celery import Task
from typing import Dict

from app.tasks.celery_app import celery_app
from app.core.logging import logger
from app.services.job_service import JobService
from app.services.minio_service import MinioService
from app.services.postgres_service import PostgresService


class ProcessingTask(Task):
    """Base task with error handling"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        logger.error(f"Task {task_id} failed: {exc}")
        job_service = JobService()
        job_service.update_job_status(
            job_id=task_id,
            status='failed',
            error=str(exc)
        )


@celery_app.task(base=ProcessingTask, bind=True)
def process_case_task(self, job_id: str, job_data: Dict):
    """
    Main processing task.
    
    Downloads files from MinIO, runs analysis using preserved
    forensic_toolkit logic, uploads results back to MinIO,
    and stores metadata in PostgreSQL.
    
    Args:
        job_id: Unique job identifier
        job_data: Job configuration including case_id, modes, etc.
    """
    try:
        logger.info(f"Starting processing for job {job_id}")
        
        # Update status to processing
        job_service = JobService()
        job_service.update_job_status(
            job_id=job_id,
            status='processing',
            progress=0,
            current_step='Initializing'
        )
        
        # TODO: Implement full processing pipeline:
        # 1. Download files from MinIO
        # 2. Run analysis using legacy_logic/runner.py
        # 3. Upload results to MinIO
        # 4. Store metadata in PostgreSQL
        # 5. Update job status
        
        # Placeholder - would call adapted run_analysis function
        logger.info(f"Processing job {job_id}")
        
        # Update progress
        job_service.update_job_status(
            job_id=job_id,
            status='processing',
            progress=50,
            current_step='Analyzing evidence'
        )
        
        # Complete
        job_service.update_job_status(
            job_id=job_id,
            status='completed',
            progress=100,
            current_step='Complete',
            result={'records': 0, 'attachments': 0}
        )
        
        logger.info(f"Completed processing for job {job_id}")
        
        return {'job_id': job_id, 'status': 'completed'}
        
    except Exception as e:
        logger.error(f"Processing failed for job {job_id}: {e}")
        raise
