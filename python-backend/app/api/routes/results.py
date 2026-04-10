"""
Results API Routes

Retrieves analysis results - communications, attachments, visualizations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.core.security import verify_token
from app.core.logging import logger
from app.services.postgres_service import PostgresService


router = APIRouter()


class Communication(BaseModel):
    """Communication record"""
    id: int
    mode: str
    timestamp: Optional[str]
    sender: Optional[str]
    receiver: Optional[str]
    message: Optional[str]
    category: Optional[str]
    attachment_count: int = 0


class Attachment(BaseModel):
    """Attachment record"""
    id: int
    communication_id: int
    filename: str
    file_type: Optional[str]
    found_status: str
    has_ocr: bool = False
    has_gps: bool = False


@router.get("/communications", response_model=List[Communication])
async def get_communications(
    case_id: int = Query(..., description="Case ID"),
    user_info: dict = Depends(verify_token),
    mode: Optional[str] = None,
    category: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Get communications for a case with optional filters.
    """
    try:
        db = PostgresService()
        results = db.get_communications(
            case_id=case_id,
            mode=mode,
            category=category,
            date_from=date_from,
            date_to=date_to,
            search=search,
            limit=limit,
            offset=offset
        )
        
        return [Communication(**r) for r in results]
        
    except Exception as e:
        logger.error(f"Failed to get communications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/attachments", response_model=List[Attachment])
async def get_attachments(
    case_id: int = Query(..., description="Case ID"),
    user_info: dict = Depends(verify_token),
    communication_id: Optional[int] = None,
    file_type: Optional[str] = None,
    has_ocr: Optional[bool] = None,
    has_gps: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Get attachments for a case with optional filters.
    """
    try:
        db = PostgresService()
        results = db.get_attachments(
            case_id=case_id,
            communication_id=communication_id,
            file_type=file_type,
            has_ocr=has_ocr,
            has_gps=has_gps,
            limit=limit,
            offset=offset
        )
        
        return [Attachment(**r) for r in results]
        
    except Exception as e:
        logger.error(f"Failed to get attachments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeline")
async def get_timeline(
    case_id: int = Query(..., description="Case ID"),
    user_info: dict = Depends(verify_token)
):
    """
    Get timeline data for visualization.
    """
    try:
        db = PostgresService()
        timeline = db.get_timeline_data(case_id)
        
        return {"case_id": case_id, "timeline": timeline}
        
    except Exception as e:
        logger.error(f"Failed to get timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/network")
async def get_network_data(
    case_id: int = Query(..., description="Case ID"),
    user_info: dict = Depends(verify_token)
):
    """
    Get network visualization data.
    """
    try:
        db = PostgresService()
        network = db.get_network_data(case_id)
        
        return {"case_id": case_id, "network": network}
        
    except Exception as e:
        logger.error(f"Failed to get network data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gps")
async def get_gps_data(
    case_id: int = Query(..., description="Case ID"),
    user_info: dict = Depends(verify_token)
):
    """
    Get GPS data for map visualization.
    """
    try:
        db = PostgresService()
        gps_data = db.get_gps_data(case_id)
        
        return {"case_id": case_id, "gps_points": gps_data}
        
    except Exception as e:
        logger.error(f"Failed to get GPS data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
