from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator

import psycopg
from psycopg.rows import dict_row

from .config import get_settings


def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


@contextmanager
def get_conn() -> Generator[psycopg.Connection[Any], None, None]:
    settings = get_settings()
    conn = psycopg.connect(settings.postgres_dsn, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()


def insert_job(job_id: str, payload: dict[str, Any], input_object_key: str) -> None:
    now = utcnow()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO ocr_jobs (job_id, case_no, requested_by, status, created_at, updated_at, payload_json, input_object_key)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
            """,
            (
                job_id,
                payload.get('case_no', 'CASE-001'),
                payload.get('requested_by', 'unknown'),
                'queued',
                now,
                now,
                json.dumps(payload),
                input_object_key,
            ),
        )
        conn.commit()


def update_job_status(job_id: str, status: str, *, summary: dict[str, Any] | None = None, result_object_key: str | None = None, error_message: str | None = None) -> None:
    now = utcnow()
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE ocr_jobs
               SET status = %s,
                   updated_at = %s,
                   summary_json = COALESCE(%s::jsonb, summary_json),
                   result_object_key = COALESCE(%s, result_object_key),
                   error_message = COALESCE(%s, error_message)
             WHERE job_id = %s
            """,
            (status, now, json.dumps(summary) if summary is not None else None, result_object_key, error_message, job_id),
        )
        conn.commit()


def get_job(job_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT job_id, case_no, requested_by, status, created_at, updated_at,
                   payload_json, summary_json, input_object_key, result_object_key, error_message
              FROM ocr_jobs
             WHERE job_id = %s
            """,
            (job_id,),
        ).fetchone()

        return dict(row) if row else None
