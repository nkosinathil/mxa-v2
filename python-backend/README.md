# Python Backend - Premium OCR Processing

This service runs on the **processing server** (`192.168.1.90`) and provides:

- FastAPI endpoints for job submit/status
- Celery async worker for long-running OCR jobs
- Redis broker/backend
- MinIO input/output artifact storage
- PostgreSQL job state persistence (DB hosted on `192.168.1.66`)

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
