"""
Jobs API Routes

Handles job submission, status checking, and management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from uuid import uuid4

from app.core.security import verify_token
from app.core.logging import logger
from app.tasks.processing_tasks import process_case_task
from app.services.job_service import JobService


router = APIRouter()


class JobSubmission(BaseModel):
    """Job submission request"""
    case_id: int
    case_number: str
    modes: List[str]
    category_models: List[str] = ["generic"]
    transcribe_audio: bool = False
    audio_max_seconds: Optional[int] = None


class JobResponse(BaseModel):
    """Job submission response"""
    job_id: str
    case_id: int
    status: str
    message: str


class JobStatus(BaseModel):
    """Job status response"""
    job_id: str
    case_id: int
    status: str
    progress: Optional[int] = None
    current_step: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def submit_job(
    job_data: JobSubmission,
    user_info: dict = Depends(verify_token)
):
    """
    Submit a new processing job.
    
    Uploads will already be in MinIO at this point.
    This endpoint queues the job for processing.
    """
    try:
        # Generate job ID
        job_id = str(uuid4())
        
        # Create job record in database
        job_service = JobService()
        job_service.create_job(
            job_id=job_id,
            case_id=job_data.case_id,
            user_id=user_info.get('sub'),
            config={
                'modes': job_data.modes,
                'category_models': job_data.category_models,
                'transcribe_audio': job_data.transcribe_audio,
                'audio_max_seconds': job_data.audio_max_seconds,
            }
        )
        
        # Submit to Celery queue
        process_case_task.apply_async(
            args=[job_id, job_data.dict()],
            task_id=job_id,
            queue=settings.celery_queue_name
        )
        
        logger.info(f"Job {job_id} submitted for case {job_data.case_number}")
        
        return JobResponse(
            job_id=job_id,
            case_id=job_data.case_id,
            status="queued",
            message="Job submitted successfully"
        )
        
    except Exception as e:
        logger.error(f"Job submission failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{job_id}/status", response_model=JobStatus)
async def get_job_status(
    job_id: str,
    user_info: dict = Depends(verify_token)
):
    """
    Get status of a processing job.
    """
    try:
        job_service = JobService()
        job = job_service.get_job_status(job_id)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        return JobStatus(**job)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("", response_model=List[JobStatus])
@router.get("/", response_model=List[JobStatus])
async def list_jobs(
    user_info: dict = Depends(verify_token),
    case_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    limit: int = 100
):
    """
    List processing jobs.
    """
    try:
        job_service = JobService()
        jobs = job_service.list_jobs(
            case_id=case_id,
            status=status_filter,
            limit=limit
        )
        
        return [JobStatus(**job) for job in jobs]
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


from app.core.config import settings
