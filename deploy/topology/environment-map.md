# Premium OCR Environment Mapping

This platform is hardened for the discovered three-server topology.

## 1) Application server (`192.168.1.66`)

Components:

- Apache + PHP-FPM frontend (`/var/www/gismartanalytics/public`)
- PostgreSQL database (`premium_ocr`)

Responsibilities:

- User-facing web pages
- SSO redirect/callback handling
- Forward uploads to Python API
- Store OCR job metadata in PostgreSQL

Hardening notes:

- Increase PHP upload limits (default discovered: `upload_max_filesize=2M`, `post_max_size=8M`)
- Increase Apache/PHP timeouts for large evidence uploads
- Use `deploy/app-server/*` assets

## 2) SSO server (`192.168.1.59`)

Components:

- Keycloak 26.5.7 via nginx reverse proxy

Responsibilities:

- User authentication
- Issuing access tokens and user profile claims

Hardening notes:

- Current Keycloak config uses `hostname=sso.gint.co.za` with `hostname-strict=true`
- App SSO URLs should use `sso.gint.co.za` (not raw IP) unless strict mode is changed
- Use `deploy/sso-server/*` assets

## 3) Python processing server (`192.168.1.90`)

Components:

- FastAPI (`python-backend/app/main.py`) behind nginx
- Celery worker (`python-backend/app/tasks.py`)
- Redis (broker + result backend)
- MinIO (object storage for input/output bundles)
- forensic toolkit runtime

Responsibilities:

- Queue and execute OCR jobs asynchronously
- Invoke toolkit `run_analysis(...)`
- Package outputs and expose result URLs

Hardening notes:

- Align to existing `/opt/mxa/api` deployment model
- Keep API on `127.0.0.1:8000` behind nginx `:80`
- Ensure OS packages installed: `tesseract-ocr`, `poppler-utils`, `ffmpeg`

## Core ports in current environment

- App server Apache: `80` on 192.168.1.66
- App server PostgreSQL: `5432` on 192.168.1.66
- SSO server nginx/keycloak: `80` (proxy to 8080) on 192.168.1.59
- Python server nginx: `80` on 192.168.1.90 (proxy to 127.0.0.1:8000)
- Python server Redis: `127.0.0.1:6379`
- Python server MinIO API/Console: `9000/9001`
