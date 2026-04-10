# Python Backend - MxA - Mobile Analytics Processing

This service runs on the **processing server** (`192.168.1.90`) and provides:

- FastAPI endpoints for job submit/status
- Celery async worker for long-running OCR jobs
- Redis broker/backend
- MinIO input/output artifact storage
- PostgreSQL job state persistence (DB hosted on `192.168.1.66`)

## Runtime alignment with discovered python server

From attached server report:

- Existing runtime path is `/opt/mxa-mobile-analytics/api`
- Existing services: `mxa-api.service`, `mxa-celery.service`
- Existing API listens on `127.0.0.1:8000` behind nginx on port 80
- Redis active on localhost, MinIO active on 9000/9001

Use provided deployment assets:

- `deploy/python-server/systemd/mxa-api.service`
- `deploy/python-server/systemd/mxa-celery.service`
- `deploy/python-server/nginx/mxa-api.conf`
- `deploy/python-server/python-server.env.mxa.example`
- `deploy/python-server/deploy-python-server.sh`

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Run API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Run worker:

```bash
celery -A app.tasks worker --loglevel=info
```

## Important integration detail

The worker imports and executes:

```python
from forensic_toolkit.runner import run_analysis
```

Ensure `TOOLKIT_PATH` includes repository root where `forensic_toolkit/` exists.

## OS package prerequisites for OCR pipeline

Install on python server:

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils ffmpeg
```

These are required for OCR/image and PDF/audio parsing paths.
