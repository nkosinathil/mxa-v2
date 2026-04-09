# PHP Frontend - Premium OCR

This application runs on the **application server** (`192.168.1.66`) and provides:

- SSO login against identity server (`192.168.1.59`)
- Upload form for evidence archives
- Job status dashboard powered by Python API (`192.168.1.90`)

## Runtime alignment with discovered app server

From the attached app report:

- Apache + PHP-FPM 8.1 are active
- Existing document root: `/var/www/gismartanalytics/public`
- Existing PHP upload limits are too low for OCR evidence (`2M/8M`)

Use provided deployment assets:

- `deploy/app-server/apache-vhost-premium-ocr.conf`
- `deploy/app-server/php-upload-overrides.ini`
- `deploy/app-server/deploy-app-server.sh`

## Setup (code)

```bash
cp .env.example .env
```

For local dev only:

```bash
php -S 0.0.0.0:8080 -t public
```

## Required PHP extensions

- curl
- json
- session

## Production env highlights

- `PYTHON_API_BASE_URL=http://192.168.1.90`
- `SSO_ISSUER=http://sso.gint.co.za/realms/premium-ocr`
- `SSO_REDIRECT_URI=http://192.168.1.66/callback.php`

> If Keycloak remains `hostname-strict=true`, do not use raw IP for SSO endpoints.
