#!/usr/bin/env bash
set -euo pipefail

SITE_AVAILABLE="/etc/nginx/sites-available/keycloak"
SITE_ENABLED="/etc/nginx/sites-enabled/keycloak"

sudo install -m 0644 deploy/sso-server/nginx-keycloak-sso.gint.co.za.conf "$SITE_AVAILABLE"
if [[ ! -L "$SITE_ENABLED" ]]; then
  sudo ln -s "$SITE_AVAILABLE" "$SITE_ENABLED"
fi

sudo nginx -t
sudo systemctl reload nginx

echo "[done] sso nginx updated on 192.168.1.59"
