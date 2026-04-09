# Premium OCR Environment Mapping

This platform is designed for the requested three-server topology.

## 1) Application server (`192.168.1.66`)

Components:

- PHP frontend (`php-app/public`)
- PostgreSQL database (`premium_ocr`)

Responsibilities:

- User-facing web pages
- SSO redirect/callback handling
- Forward uploads to Python API
- Store OCR job metadata in PostgreSQL

## 2) SSO server (`192.168.1.59`)

Components:

- OIDC/OAuth2 identity provider

Responsibilities:

- User authentication
- Issuing access tokens and user profile claims

## 3) Python processing server (`192.168.1.90`)

Components:

- FastAPI (`python-backend/app/main.py`)
- Celery worker (`python-backend/app/tasks.py`)
- Redis (broker + result backend)
- MinIO (object storage for input/output bundles)
- forensic toolkit runtime (`forensic_toolkit/`)

Responsibilities:

- Queue and execute OCR jobs asynchronously
- Invoke toolkit `run_analysis(...)`
- Package outputs and expose result URLs

## Core ports (suggested)

- PHP web: `80/443` on 192.168.1.66
- PostgreSQL: `5432` on 192.168.1.66
- SSO: `80/443` on 192.168.1.59
- FastAPI: `8000` on 192.168.1.90
- Redis: `6379` on 192.168.1.90
- MinIO API: `9000` on 192.168.1.90
- MinIO Console: `9001` on 192.168.1.90
