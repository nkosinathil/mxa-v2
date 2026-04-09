from __future__ import annotations

import json
import shutil
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status

from .config import get_settings
from .models import JobPayload, JobResponse, JobStatusResponse
from .security import require_api_key
from .services import enqueue_job, resolve_job_status

app = FastAPI(title='Premium OCR Processing API', version='1.0.0')


@app.get('/health')
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        'status': 'ok',
        'app_env': settings.app_env,
        'python_server': '192.168.1.90',
        'app_server': '192.168.1.66',
        'sso_server': '192.168.1.59',
    }


@app.post('/v1/jobs', response_model=JobResponse, dependencies=[Depends(require_api_key)])
async def create_job(payload: str = Form(...), evidence: UploadFile = File(...)) -> JobResponse:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'Invalid payload JSON: {exc}') from exc

    normalized = JobPayload.model_validate(data)
    settings = get_settings()

    suffix = Path(evidence.filename or 'upload.bin').suffix
    temp_path = settings.upload_path / f"{normalized.case_no}_{Path(evidence.filename or 'upload.bin').stem}{suffix}"

    with temp_path.open('wb') as out:
        shutil.copyfileobj(evidence.file, out)

    try:
        result = enqueue_job(normalized.model_dump(), temp_path, evidence.filename or temp_path.name)
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass

    return JobResponse(**result)


@app.get('/v1/jobs/{job_id}', response_model=JobStatusResponse, dependencies=[Depends(require_api_key)])
def get_job(job_id: str) -> JobStatusResponse:
    row = resolve_job_status(job_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Job not found')
    return JobStatusResponse(**row)
