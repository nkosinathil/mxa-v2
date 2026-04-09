-- PostgreSQL schema for Premium OCR platform

CREATE TABLE IF NOT EXISTS ocr_jobs (
    job_id TEXT PRIMARY KEY,
    case_no TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    payload_json JSONB NOT NULL,
    summary_json JSONB,
    input_object_key TEXT NOT NULL,
    result_object_key TEXT,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_ocr_jobs_status ON ocr_jobs(status);
CREATE INDEX IF NOT EXISTS idx_ocr_jobs_created_at ON ocr_jobs(created_at DESC);
