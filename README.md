# Premium OCR Web Platform (PHP + Python)

This repository now contains a web-based Premium OCR platform converted from the attached desktop-oriented toolkit.

## Environment Memory Confirmation

This implementation is aligned to the requested three-server environment:

- **Application server**: `192.168.1.66` (PHP frontend + PostgreSQL)
- **SSO server**: `192.168.1.59` (OIDC/OAuth2 identity provider)
- **Python processing server**: `192.168.1.90` (FastAPI, Celery worker, Redis, MinIO)

## Repository Structure

- `forensic_toolkit/` - existing OCR/forensics processing engine (preserved)
- `php-app/` - PHP web frontend (login, upload, job tracking)
- `python-backend/` - Python API + Celery pipeline that invokes `forensic_toolkit.runner.run_analysis`
- `deploy/` - environment templates and topology/deployment notes

## High-Level Flow

1. User authenticates via SSO from the PHP app.
2. User uploads evidence ZIP in PHP frontend.
3. PHP forwards upload to Python API.
4. Python API stores source object in MinIO and queues Celery task in Redis.
5. Celery worker downloads source, runs toolkit analysis, writes outputs.
6. Result bundle + summary are uploaded to MinIO.
7. PHP polls job status and shows result download URL.

## Quick Start (Development)

### 1) PHP frontend

```bash
cd php-app
cp .env.example .env
# serve static PHP pages
php -S 0.0.0.0:8080 -t public
```

### 2) Python API

```bash
cd python-backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3) Celery worker

```bash
cd python-backend
source .venv/bin/activate
celery -A app.tasks worker --loglevel=info
```

## Production Deployment Notes

- Configure real SSO client values in `php-app/.env`.
- Configure MinIO/Redis/PostgreSQL endpoints in `python-backend/.env`.
- Apply schema in `deploy/topology/postgres-schema.sql`.
- Keep `forensic_toolkit/` available on Python server so the worker can import and execute it.

