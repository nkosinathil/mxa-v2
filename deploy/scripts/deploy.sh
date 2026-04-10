#!/bin/bash
#
# MxA Mobile Deployment Script
#
# This script deploys or updates the MxA Mobile application.
#

set -e

REPO_URL="<repository-url>"
APP_DIR="/var/www/mxa-mobile-app"
PYTHON_DIR="/opt/apps/mxa-mobile"
BACKUP_DIR="/var/backups/mxa-mobile"

echo "=== MxA Mobile Deployment ==="
echo "Starting deployment at $(date)"

# Create backup
echo "Creating backup..."
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).tar.gz"
tar -czf "$BACKUP_FILE" -C "$APP_DIR" current || true

# Deploy PHP application
echo "Deploying PHP application..."
cd "$APP_DIR"
if [ ! -d "current/.git" ]; then
    git clone "$REPO_URL" current
else
    cd current
    git pull origin main
fi

cd "$APP_DIR/current/php-app"
composer install --no-dev --optimize-autoloader

# Set permissions
chown -R www-data:www-data "$APP_DIR/current"
chmod -R 755 "$APP_DIR/current"
chmod -R 775 "$APP_DIR/current/php-app/storage"

echo "Reloading Apache..."
systemctl reload apache2

# Deploy Python application
echo "Deploying Python application..."
cd "$PYTHON_DIR"
if [ ! -d ".git" ]; then
    git clone "$REPO_URL" .
else
    git pull origin main
fi

cd "$PYTHON_DIR/python-backend"
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Set permissions
chown -R celery:celery "$PYTHON_DIR"
chmod -R 750 "$PYTHON_DIR"

echo "Restarting Python services..."
systemctl restart mxa-mobile-api
systemctl restart mxa-mobile-worker

# Health check
echo "Running health checks..."
sleep 5

if curl -f http://localhost:8104/health > /dev/null 2>&1; then
    echo "✓ FastAPI is healthy"
else
    echo "✗ FastAPI health check failed"
    exit 1
fi

if systemctl is-active --quiet mxa-mobile-worker; then
    echo "✓ Celery worker is running"
else
    echo "✗ Celery worker is not running"
    exit 1
fi

if systemctl is-active --quiet apache2; then
    echo "✓ Apache is running"
else
    echo "✗ Apache is not running"
    exit 1
fi

echo "=== Deployment completed successfully at $(date) ==="
echo "Backup saved to: $BACKUP_FILE"
