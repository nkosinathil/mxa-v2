# SSO Server Hardening (192.168.1.59)

Based on attached report details:

- Keycloak 26.5.7 (`/opt/keycloak`)
- keycloak.conf has `hostname=sso.gint.co.za` and `hostname-strict=true`
- Nginx reverse proxy currently serves `server_name sso.local`

This mismatch can break OIDC redirect flows if app uses IP URLs.

## Recommended approach

Use a consistent hostname for browser-facing SSO endpoints (preferred):

- Keep Keycloak hostname strict
- Update nginx `server_name` to `sso.gint.co.za`
- Ensure app server can resolve that DNS and use it in `.env`

## Option A (preferred)

1) Keep `/opt/keycloak/conf/keycloak.conf`:

```ini
hostname=sso.gint.co.za
hostname-strict=true
http-enabled=true
http-port=8080
proxy-headers=xforwarded
```

2) Update nginx site to the same host:

```nginx
server {
    listen 80;
    server_name sso.gint.co.za;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_buffering off;
        proxy_request_buffering off;
    }
}
```

3) In PHP app `.env`, set all SSO URLs to `http://sso.gint.co.za/...`

## Option B (IP-based temporary mode)

If DNS not ready, disable strict host validation temporarily:

```ini
hostname=192.168.1.59
hostname-strict=false
```

Then restart Keycloak and set PHP SSO URLs to `http://192.168.1.59/...`.

> Use Option B only for short-term internal testing.
