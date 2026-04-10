#!/usr/bin/env bash
set -euo pipefail

if [[ ! -d /opt/mxa-mobile-analytics/api ]]; then
  echo "[error] /opt/mxa-mobile-analytics/api not found on this host"
  exit 1
fi

sudo install -d -m 0755 /opt/mxa-mobile-analytics/data/uploads /opt/mxa-mobile-analytics/data/tmp /opt/mxa-mobile-analytics/data/output
sudo chown -R pyminio:pyminio /opt/mxa-mobile-analytics/data

sudo install -m 0644 deploy/python-server/nginx/mxa-api.conf /etc/nginx/sites-available/mxa-api
if [[ ! -L /etc/nginx/sites-enabled/mxa-api ]]; then
  sudo ln -s /etc/nginx/sites-available/mxa-api /etc/nginx/sites-enabled/mxa-api
fi

sudo install -m 0644 deploy/python-server/systemd/mxa-api.service /etc/systemd/system/mxa-api.service
sudo install -m 0644 deploy/python-server/systemd/mxa-celery.service /etc/systemd/system/mxa-celery.service

sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl enable mxa-api mxa-celery
sudo systemctl restart mxa-api mxa-celery
sudo systemctl reload nginx

echo "[done] python server deployment applied on 192.168.1.90"
