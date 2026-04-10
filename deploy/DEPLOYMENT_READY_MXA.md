# MxA - Mobile Analytics Deployment Guide

This guide verifies and deploys **MxA - Mobile Analytics** as a unique environment across:

- App server: `192.168.1.66`
- SSO server: `192.168.1.59`
- Python server: `192.168.1.90`

## 0) Unique environment identifiers used

- Application name: `mxa-mobile-analytics`
- PHP session name: `mxa_mobile_analytics`
- PostgreSQL database: `mxa_mobile_analytics`
- PostgreSQL user: `mxa_mobile_analytics`
- MinIO buckets:
  - `mxa-mobile-analytics-input`
  - `mxa-mobile-analytics-output`
- Celery app/task namespace: `mxa_mobile_analytics`
- Python runtime root: `/opt/mxa-mobile-analytics`

---

## 1) Deploy on SSO server (192.168.1.59)

### 1.1 Realm and client
Create Keycloak realm and client:

- Realm: `mxa-mobile-analytics`
- Client ID: `mxa-mobile-analytics-web`
- Redirect URI: `http://192.168.1.66/callback.php`

### 1.2 Keep host consistency for strict mode
Your Keycloak is strict-hostname. Keep this consistent:

- Keycloak hostname: `sso.gint.co.za`
- Nginx `server_name`: `sso.gint.co.za`

Apply nginx config from repo:

```bash
cd /path/to/repo
bash deploy/sso-server/deploy-sso-nginx.sh
```

If DNS is unavailable, temporarily set Keycloak `hostname-strict=false` and use IP URLs.

---

## 2) Deploy on app server (192.168.1.66)

### 2.1 Prepare code path
Place app code at existing Apache root parent:

- Expected web root in config: `/var/www/gismartanalytics/public`

Copy `php-app` public/src content into your app root structure.

### 2.2 Configure environment
Create `.env` from template:

```bash
cp php-app/.env.example php-app/.env
```

Set at minimum:

- `PYTHON_API_KEY` (must match python server)
- `SSO_CLIENT_SECRET`

### 2.3 Apply Apache + PHP-FPM hardening

```bash
cd /path/to/repo
bash deploy/app-server/deploy-app-server.sh
```

This applies:

- mxa app vhost
- PHP upload and timeout overrides
- Apache/PHP-FPM reload

### 2.4 Verify

```bash
curl -I http://192.168.1.66/
```

Expect `200` (or redirect to login route once auth is enforced).

---

## 3) Deploy on python server (192.168.1.90)

### 3.1 Install OS packages (required)

```bash
sudo apt-get update
sudo apt-get install -y python3-venv tesseract-ocr poppler-utils ffmpeg
```

### 3.2 Prepare unique runtime path

```bash
sudo mkdir -p /opt/mxa-mobile-analytics/api
sudo chown -R pyminio:pyminio /opt/mxa-mobile-analytics
```

Copy repository code so these exist:

- `/opt/mxa-mobile-analytics/api/app`
- `/opt/mxa-mobile-analytics/forensic_toolkit`

### 3.3 Python virtualenv and dependencies

```bash
cd /opt/mxa-mobile-analytics/api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3.4 Environment file

```bash
cp /path/to/repo/deploy/python-server/python-server.env.mxa.example /opt/mxa-mobile-analytics/api/.env
```

Set secrets/values:

- `API_KEY`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `POSTGRES_DSN` password

### 3.5 Apply services and proxy

```bash
cd /path/to/repo
bash deploy/python-server/deploy-python-server.sh
```

### 3.6 Verify python service

```bash
curl -s http://192.168.1.90/health
```

Expect JSON with `"status":"ok"`.

---

## 4) PostgreSQL setup on app server (192.168.1.66)

```sql
CREATE USER mxa_mobile_analytics WITH PASSWORD 'change-me';
CREATE DATABASE mxa_mobile_analytics OWNER mxa_mobile_analytics;
```

Apply schema:

```bash
psql "postgresql://mxa_mobile_analytics:change-me@192.168.1.66:5432/mxa_mobile_analytics" -f deploy/topology/postgres-schema.sql
```

---

## 5) MinIO bucket setup on python server (192.168.1.90)

Create buckets if not auto-created by app startup:

- `mxa-mobile-analytics-input`
- `mxa-mobile-analytics-output`

(Backend will auto-create if credentials allow.)

---

## 6) End-to-end smoke test

1. Open: `http://192.168.1.66/`
2. Login via SSO
3. Submit small zip evidence file
4. Confirm job enters queued/running/completed
5. Download result zip from status page

---

## 7) Readiness status

From code perspective, this repo is deployment-ready **provided** these environment prerequisites are completed:

- Keycloak realm/client created for `mxa-mobile-analytics`
- DNS or strict-host strategy finalized for `sso.gint.co.za`
- Postgres database/user created and schema applied
- Python OCR dependencies installed (`tesseract`, `poppler`, `ffmpeg`)
- Matching API key and secrets configured
