#!/bin/bash
#
# MxA Mobile - Backup Script
# Creates backups of database, configuration, and application code
#
# Usage: ./backup.sh [destination_directory]
#

set -e

echo "=========================================="
echo "MxA Mobile - Backup"
echo "=========================================="

# Configuration
BACKUP_DIR="${1:-/var/backups/mxa-mobile}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="mxa_mobile_backup_$TIMESTAMP"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

DB_HOST="${DB_HOST:-192.168.1.66}"
DB_NAME="${DB_NAME:-mxa_mobile}"
DB_USER="${DB_USER:-mxa_mobile_user}"
DB_PASSWORD="${DB_PASSWORD}"

echo "Backup destination: $BACKUP_PATH"
echo ""

# Create backup directory
mkdir -p "$BACKUP_PATH"

echo "Step 1: Backing up database..."
export PGPASSWORD="$DB_PASSWORD"
pg_dump -h "$DB_HOST" -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_PATH/database.sql.gz"
unset PGPASSWORD
echo "✓ Database backed up"

echo ""
echo "Step 2: Backing up PHP application..."
if [ -d "/var/www/mxa-mobile-app/current" ]; then
    tar -czf "$BACKUP_PATH/php-app.tar.gz" \
        -C /var/www/mxa-mobile-app current \
        --exclude='current/php-app/vendor' \
        --exclude='current/.git'
    echo "✓ PHP application backed up"
else
    echo "⚠ PHP application directory not found"
fi

echo ""
echo "Step 3: Backing up Python application..."
if [ -d "/opt/apps/mxa-mobile" ]; then
    tar -czf "$BACKUP_PATH/python-app.tar.gz" \
        -C /opt/apps/mxa-mobile . \
        --exclude='python-backend/venv' \
        --exclude='.git'
    echo "✓ Python application backed up"
else
    echo "⚠ Python application directory not found"
fi

echo ""
echo "Step 4: Backing up configuration files..."
mkdir -p "$BACKUP_PATH/config"

# PHP .env
if [ -f "/var/www/mxa-mobile-app/current/php-app/.env" ]; then
    cp /var/www/mxa-mobile-app/current/php-app/.env "$BACKUP_PATH/config/php.env"
fi

# Python .env
if [ -f "/opt/apps/mxa-mobile/python-backend/.env" ]; then
    cp /opt/apps/mxa-mobile/python-backend/.env "$BACKUP_PATH/config/python.env"
fi

# Apache config
if [ -f "/etc/apache2/sites-available/mxa-mobile.conf" ]; then
    cp /etc/apache2/sites-available/mxa-mobile.conf "$BACKUP_PATH/config/apache.conf"
fi

# Systemd services
if [ -f "/etc/systemd/system/mxa-mobile-api.service" ]; then
    cp /etc/systemd/system/mxa-mobile-api.service "$BACKUP_PATH/config/"
fi
if [ -f "/etc/systemd/system/mxa-mobile-worker.service" ]; then
    cp /etc/systemd/system/mxa-mobile-worker.service "$BACKUP_PATH/config/"
fi

echo "✓ Configuration files backed up"

echo ""
echo "Step 5: Creating backup manifest..."
cat > "$BACKUP_PATH/manifest.txt" <<EOF
MxA Mobile Backup
Created: $(date)
Backup ID: $BACKUP_NAME

Contents:
- database.sql.gz       PostgreSQL database dump
- php-app.tar.gz        PHP application code
- python-app.tar.gz     Python application code
- config/               Configuration files

Database:
- Host: $DB_HOST
- Database: $DB_NAME
- User: $DB_USER

To restore:
1. Extract archives
2. Import database: gunzip -c database.sql.gz | psql -h $DB_HOST -U $DB_USER $DB_NAME
3. Deploy application code from archives
4. Restore configuration files
5. Restart services
EOF

echo "✓ Manifest created"

echo ""
echo "Step 6: Creating compressed archive..."
cd "$BACKUP_DIR"
tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME"
BACKUP_SIZE=$(du -h "$BACKUP_NAME.tar.gz" | cut -f1)
rm -rf "$BACKUP_NAME"

echo "✓ Compressed archive created"

echo ""
echo "=========================================="
echo "Backup Complete!"
echo "=========================================="
echo ""
echo "Backup file: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
echo "Size: $BACKUP_SIZE"
echo ""
echo "To restore this backup:"
echo "  tar -xzf $BACKUP_NAME.tar.gz"
echo "  cd $BACKUP_NAME"
echo "  # Follow instructions in manifest.txt"
echo ""
