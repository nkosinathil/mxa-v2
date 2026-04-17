#!/bin/bash
#
# MxA Mobile - Rollback Script
# Rolls back to a previous backup
#
# Usage: ./rollback.sh <backup_file.tar.gz>
#

set -euo pipefail

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file.tar.gz>"
    echo ""
    echo "Available backups:"
    ls -lh /var/backups/mxa-mobile/*.tar.gz 2>/dev/null || echo "  No backups found"
    exit 1
fi

BACKUP_FILE="$1"
FORCE_ROLLBACK="${FORCE_ROLLBACK:-false}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "=========================================="
echo "MxA Mobile - Rollback"
echo "=========================================="
echo ""
echo "Backup file: $BACKUP_FILE"
echo ""
echo "WARNING: This will:"
echo "  - Stop all services"
echo "  - Restore database from backup"
echo "  - Restore application code"
echo "  - Restart services"
echo ""
if [ "$FORCE_ROLLBACK" != "true" ]; then
    echo "Set FORCE_ROLLBACK=true to execute rollback in non-interactive mode."
    echo "Rollback cancelled"
    exit 1
fi

# Create temporary directory
TEMP_DIR=$(mktemp -d)
echo "Extracting backup to $TEMP_DIR..."
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"

# Find backup directory
BACKUP_DIR=$(find "$TEMP_DIR" -maxdepth 1 -type d -name "mxa_mobile_backup_*" | head -1)

if [ -z "$BACKUP_DIR" ]; then
    echo "Error: Invalid backup file"
    rm -rf "$TEMP_DIR"
    exit 1
fi

echo "✓ Backup extracted"

# Stop services
echo ""
echo "Stopping services..."
systemctl stop mxa-mobile-worker
systemctl stop mxa-mobile-api
systemctl stop apache2

echo "✓ Services stopped"

# Restore database
echo ""
echo "Restoring database..."
DB_PASSWORD="${DB_PASSWORD:-}"
if [ -z "$DB_PASSWORD" ]; then
    echo "DB_PASSWORD must be set (export DB_PASSWORD=...)"
    exit 1
fi
export PGPASSWORD="$DB_PASSWORD"

if [ -f "$BACKUP_DIR/database.sql.gz" ]; then
    # Drop existing database
    dropdb -h 192.168.1.66 -U mxa_mobile_user --if-exists mxa_mobile
    
    # Create new database
    createdb -h 192.168.1.66 -U mxa_mobile_user mxa_mobile
    
    # Restore
    gunzip -c "$BACKUP_DIR/database.sql.gz" | psql -h 192.168.1.66 -U mxa_mobile_user mxa_mobile
    
    echo "✓ Database restored"
else
    echo "⚠ Database backup not found, skipping"
fi

unset PGPASSWORD

# Restore PHP application
echo ""
echo "Restoring PHP application..."
if [ -f "$BACKUP_DIR/php-app.tar.gz" ]; then
    rm -rf /var/www/mxa-mobile-app/current
    mkdir -p /var/www/mxa-mobile-app
    tar -xzf "$BACKUP_DIR/php-app.tar.gz" -C /var/www/mxa-mobile-app
    chown -R www-data:www-data /var/www/mxa-mobile-app
    echo "✓ PHP application restored"
else
    echo "⚠ PHP application backup not found, skipping"
fi

# Restore Python application
echo ""
echo "Restoring Python application..."
if [ -f "$BACKUP_DIR/python-app.tar.gz" ]; then
    rm -rf /opt/apps/mxa-mobile/*
    tar -xzf "$BACKUP_DIR/python-app.tar.gz" -C /opt/apps/mxa-mobile
    chown -R celery:celery /opt/apps/mxa-mobile
    echo "✓ Python application restored"
else
    echo "⚠ Python application backup not found, skipping"
fi

# Restore configuration files
echo ""
echo "Restoring configuration files..."
if [ -d "$BACKUP_DIR/config" ]; then
    # PHP .env
    if [ -f "$BACKUP_DIR/config/php.env" ]; then
        cp "$BACKUP_DIR/config/php.env" /var/www/mxa-mobile-app/current/php-app/.env
        chown www-data:www-data /var/www/mxa-mobile-app/current/php-app/.env
    fi
    
    # Python .env
    if [ -f "$BACKUP_DIR/config/python.env" ]; then
        cp "$BACKUP_DIR/config/python.env" /opt/apps/mxa-mobile/python-backend/.env
        chown celery:celery /opt/apps/mxa-mobile/python-backend/.env
    fi
    
    echo "✓ Configuration files restored"
else
    echo "⚠ Configuration backups not found, skipping"
fi

# Reinstall dependencies
echo ""
echo "Reinstalling dependencies..."

# PHP
cd /var/www/mxa-mobile-app/current/php-app
sudo -u www-data composer install --no-dev --optimize-autoloader

# Python
cd /opt/apps/mxa-mobile/python-backend
sudo -u celery bash -c "source venv/bin/activate && pip install -r requirements.txt"

echo "✓ Dependencies reinstalled"

# Start services
echo ""
echo "Starting services..."
systemctl start apache2
systemctl start mxa-mobile-api
systemctl start mxa-mobile-worker

sleep 5

# Verify services
echo ""
echo "Verifying services..."
systemctl is-active --quiet apache2 && echo "✓ Apache running" || echo "✗ Apache failed"
systemctl is-active --quiet mxa-mobile-api && echo "✓ FastAPI running" || echo "✗ FastAPI failed"
systemctl is-active --quiet mxa-mobile-worker && echo "✓ Celery running" || echo "✗ Celery failed"

# Cleanup
rm -rf "$TEMP_DIR"

echo ""
echo "=========================================="
echo "Rollback Complete!"
echo "=========================================="
echo ""
echo "System has been rolled back to backup:"
echo "  $BACKUP_FILE"
echo ""
echo "Please verify application functionality:"
echo "  http://192.168.1.66"
echo ""
