# PHP Frontend - Premium OCR

This application runs on the **application server** (`192.168.1.66`) and provides:

- SSO login against identity server (`192.168.1.59`)
- Upload form for evidence archives
- Job status dashboard powered by Python API (`192.168.1.90`)

## Setup

```bash
cp .env.example .env
php -S 0.0.0.0:8080 -t public
```

## Required PHP extensions

- curl
- json
- session

## Environment variables

See `.env.example` for complete values.

Key values in production:

- `PYTHON_API_BASE_URL=http://192.168.1.90:8000`
- `SSO_AUTHORIZE_URL=http://192.168.1.59/.../auth`
- `SSO_TOKEN_URL=http://192.168.1.59/.../token`
- `SSO_REDIRECT_URI=http://192.168.1.66/callback.php`
