#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/var/www/gismartanalytics"
APACHE_SITE="/etc/apache2/sites-available/mxa-mobile-analytics.conf"
PHP_INI_OVERRIDE="/etc/php/8.1/fpm/conf.d/99-mxa-mobile-analytics.ini"

if [[ ! -d "$APP_ROOT" ]]; then
  echo "[error] expected app root not found: $APP_ROOT"
  exit 1
fi

sudo install -m 0644 deploy/app-server/apache-vhost-mxa-mobile-analytics.conf "$APACHE_SITE"
sudo install -m 0644 deploy/app-server/php-upload-overrides.ini "$PHP_INI_OVERRIDE"

sudo a2enmod headers proxy_fcgi rewrite
sudo a2ensite mxa-mobile-analytics.conf
sudo a2dissite gismartanalytics.com.conf || true

sudo apache2ctl configtest
sudo systemctl reload php8.1-fpm
sudo systemctl reload apache2

echo "[done] app server deployment applied on 192.168.1.66"
