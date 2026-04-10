"""
Cases API Routes

Case management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.core.security import verify_token
from app.core.logging import logger
from app.services.postgres_service import PostgresService


router = APIRouter()


class CaseInfo(BaseModel):
    """Case information"""
    id: int
    case_number: str
    case_name: str
    description: Optional[str]
    status: str
    created_at: str


@router.get("/{case_id}", response_model=CaseInfo)
async def get_case(
    case_id: int,
    user_info: dict = Depends(verify_token)
):
    """
    Get case details by ID.
    """
    try:
        db = PostgresService()
        case = db.get_case(case_id)
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        return CaseInfo(**case)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get case: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[CaseInfo])
@router.get("/", response_model=List[CaseInfo])
async def list_cases(
    user_info: dict = Depends(verify_token),
    status: Optional[str] = None,
    limit: int = 100
):
    """
    List cases with optional filters.
    """
    try:
        db = PostgresService()
        cases = db.list_cases(status=status, limit=limit)
        
        return [CaseInfo(**c) for c in cases]
        
    except Exception as e:
        logger.error(f"Failed to list cases: {e}")
        raise HTTPException(status_code=500, detail=str(e))
