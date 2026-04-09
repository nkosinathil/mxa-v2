from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

from .config import get_settings
from .database import get_job, insert_job, update_job_status
from .storage import MinioStorage


def _job_input_key(job_id: str, filename: str) -> str:
    safe = ''.join(ch if ch.isalnum() or ch in '._-' else '_' for ch in filename)
    return f'jobs/{job_id}/input/{safe}'


def _job_result_key(job_id: str) -> str:
    return f'jobs/{job_id}/output/result.zip'


def enqueue_job(payload: dict[str, Any], upload_path: Path, filename: str) -> dict[str, str]:
    from .tasks import process_job

    job_id = str(uuid.uuid4())
    storage = MinioStorage()
    input_key = _job_input_key(job_id, filename)
    storage.upload_file(storage.input_bucket, input_key, upload_path)

    insert_job(job_id, payload, input_key)
    process_job.delay(job_id)

    return {'job_id': job_id, 'status': 'queued'}


def resolve_job_status(job_id: str) -> dict[str, Any] | None:
    row = get_job(job_id)
    if row is None:
        return None

    result_url = None
    result_key = row.get('result_object_key')
    if isinstance(result_key, str) and result_key:
        storage = MinioStorage()
        result_url = storage.presigned_get(storage.output_bucket, result_key)

    return {
        'job_id': row['job_id'],
        'status': row['status'],
        'case_no': row['case_no'],
        'requested_by': row['requested_by'],
        'created_at': row['created_at'],
        'updated_at': row['updated_at'],
        'summary': row.get('summary_json'),
        'result_url': result_url,
        'error_message': row.get('error_message'),
    }
