from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class JobPayload(BaseModel):
    requested_by: str = Field(default='unknown')
    case_no: str = Field(default='CASE-001')
    transcribe_audio: bool = Field(default=False)
    audio_max_transcription_seconds: float | None = Field(default=None)
    selected_models: list[str] = Field(default_factory=lambda: ['generic'])
    selected_modes: dict[str, bool] = Field(
        default_factory=lambda: {
            'whatsapp': True,
            'texts': True,
            'calls': True,
            'emails': True,
            'audio': True,
            'photos': True,
            'files': True,
        }
    )


class JobResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    case_no: str
    requested_by: str
    created_at: datetime
    updated_at: datetime
    result_url: str | None = None
    summary: dict[str, Any] | None = None
    error_message: str | None = None
