"""
Health Check API Routes

Simple health check and readiness endpoints.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.services.postgres_service import PostgresService
from app.services.minio_service import MinioService


router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    service: str
    version: str


class ReadinessResponse(BaseModel):
    """Readiness check response model"""
    ready: bool
    database: bool
    minio: bool
    message: str


@router.get("", response_model=HealthResponse)
@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.
    Returns service status and version.
    """
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version="1.0.0"
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check():
    """
    Readiness check endpoint.
    Verifies that all required services are accessible.
    """
    db_ready = False
    minio_ready = False
    
    # Check database
    try:
        db_service = PostgresService()
        db_ready = db_service.check_connection()
    except Exception:
        pass
    
    # Check MinIO
    try:
        minio_service = MinioService()
        minio_ready = minio_service.check_connection()
    except Exception:
        pass
    
    ready = db_ready and minio_ready
    message = "Service is ready" if ready else "Service is not ready"
    
    return ReadinessResponse(
        ready=ready,
        database=db_ready,
        minio=minio_ready,
        message=message
    )


@router.get("/live")
async def liveness_check():
    """
    Liveness check endpoint.
    Simple check that the service is running.
    """
    return {"alive": True}
