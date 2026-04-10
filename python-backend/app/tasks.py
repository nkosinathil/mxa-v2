from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any

from celery import Celery

from .config import get_settings
from .database import get_job, update_job_status
from .storage import MinioStorage, zip_directory

settings = get_settings()
celery_app = Celery('mxa_mobile_analytics', broker=settings.celery_broker_url, backend=settings.celery_result_backend)
celery_app.conf.task_track_started = True
celery_app.conf.worker_max_tasks_per_child = 20


def _prepare_toolkit_import() -> None:
    toolkit_path = settings.toolkit_path
    if toolkit_path not in sys.path:
        sys.path.insert(0, toolkit_path)


def _input_key_from_row(row: dict[str, Any]) -> str:
    key = row.get('input_object_key')
    if isinstance(key, str) and key:
        return key
    raise RuntimeError('Job input object key is missing in database row.')


@celery_app.task(name='mxa_mobile_analytics.process_job', bind=True)
def process_job(self, job_id: str) -> dict[str, Any]:
    row = get_job(job_id)
    if row is None:
        raise RuntimeError(f'Job {job_id} not found')

    update_job_status(job_id, 'running')
    storage = MinioStorage()

    work_root = settings.tmp_path / job_id
    input_dir = work_root / 'input'
    output_dir = settings.output_path / job_id
    input_zip = input_dir / 'evidence.zip'
    output_zip = settings.output_path / f'{job_id}.zip'

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        storage.download_file(storage.input_bucket, _input_key_from_row(row), input_zip)

        extracted_input = input_dir / 'evidence'
        extracted_input.mkdir(parents=True, exist_ok=True)

        import zipfile

        with zipfile.ZipFile(input_zip, 'r') as zf:
            zf.extractall(extracted_input)

        _prepare_toolkit_import()
        from forensic_toolkit.runner import run_analysis  # pylint: disable=import-error

        payload = row.get('payload_json') or {}
        if isinstance(payload, str):
            import json
            payload = json.loads(payload)

        summary = run_analysis(
            input_path=str(extracted_input),
            output_path=str(output_dir),
            case_no=str(payload.get('case_no', 'CASE-001')),
            transcribe_audio=bool(payload.get('transcribe_audio', False)),
            audio_max_transcription_seconds=payload.get('audio_max_transcription_seconds'),
            selected_models=payload.get('selected_models') or ['generic'],
            selected_modes=payload.get('selected_modes') or None,
        )

        zip_directory(output_dir, output_zip)
        result_key = f'jobs/{job_id}/output/result.zip'
        storage.upload_file(storage.output_bucket, result_key, output_zip)

        update_job_status(job_id, 'completed', summary=summary, result_object_key=result_key)
        return {'job_id': job_id, 'status': 'completed', 'summary': summary}
    except Exception as exc:  # noqa: BLE001
        update_job_status(job_id, 'failed', error_message=str(exc))
        raise
    finally:
        shutil.rmtree(work_root, ignore_errors=True)
        shutil.rmtree(output_dir, ignore_errors=True)
        try:
            output_zip.unlink(missing_ok=True)
        except Exception:
            pass
