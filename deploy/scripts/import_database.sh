#!/bin/bash
#
# MxA Mobile - Database Schema Import
# Imports the PostgreSQL database schema
#
# Prerequisites:
# - PostgreSQL installed and running on 192.168.1.66
# - Database and user already created
#

set -e

echo "=========================================="
echo "MxA Mobile - Database Schema Import"
echo "=========================================="

# Configuration
DB_HOST="${DB_HOST:-192.168.1.66}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-mxa_mobile}"
DB_USER="${DB_USER:-mxa_mobile_user}"
DB_PASSWORD="${DB_PASSWORD:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SCHEMA_FILE="$REPO_ROOT/database/schema.sql"

echo "Database: $DB_NAME@$DB_HOST:$DB_PORT"
echo "User: $DB_USER"
echo "Schema file: $SCHEMA_FILE"
echo ""

if [ -z "$DB_PASSWORD" ]; then
    echo "DB_PASSWORD must be set (export DB_PASSWORD=...)"
    exit 1
fi

# Check if schema file exists
if [ ! -f "$SCHEMA_FILE" ]; then
    echo "✗ Schema file not found: $SCHEMA_FILE"
    exit 1
fi

echo "Step 1: Testing database connection..."
export PGPASSWORD="$DB_PASSWORD"

if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" &>/dev/null; then
    echo "✓ Database connection successful"
else
    echo "✗ Database connection failed"
    echo "  Please check:"
    echo "  - Database server is running"
    echo "  - Database credentials are correct"
    echo "  - Network connectivity to $DB_HOST"
    exit 1
fi

echo ""
echo "Step 2: Checking existing schema..."
TABLE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'" | tr -d ' ')

if [ "$TABLE_COUNT" -gt 0 ]; then
    echo "⚠ Database already contains $TABLE_COUNT tables"
    read -p "Do you want to drop existing tables and reimport? (yes/no): " CONFIRM
    
    if [ "$CONFIRM" != "yes" ]; then
        echo "Import cancelled"
        exit 0
    fi
    
    echo ""
    echo "Step 3: Backing up existing database..."
    BACKUP_FILE="/tmp/mxa_mobile_backup_$(date +%Y%m%d_%H%M%S).sql"
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" > "$BACKUP_FILE"
    echo "✓ Backup saved to: $BACKUP_FILE"
    
    echo ""
    echo "Step 4: Dropping existing tables..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
DO \$\$ DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
END \$\$;
EOF
    echo "✓ Existing tables dropped"
fi

echo ""
echo "Step 5: Importing schema..."
if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SCHEMA_FILE" &>/dev/null; then
    echo "✓ Schema imported successfully"
else
    echo "✗ Schema import failed"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SCHEMA_FILE"
    exit 1
fi

echo ""
echo "Step 6: Verifying schema..."
TABLES=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
    "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")

echo "✓ Tables created:"
echo "$TABLES" | sed 's/^/  - /'

# Count tables
TABLE_COUNT=$(echo "$TABLES" | wc -l)
echo ""
echo "Total tables: $TABLE_COUNT"

# Verify key tables exist
EXPECTED_TABLES=("users" "cases" "processing_jobs" "communications" "attachments" "tags")
echo ""
echo "Verifying key tables..."
for TABLE in "${EXPECTED_TABLES[@]}"; do
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT 1 FROM information_schema.tables WHERE table_name='$TABLE'" | grep -q 1; then
        echo "  ✓ $TABLE"
    else
        echo "  ✗ $TABLE (MISSING!)"
    fi
done

echo ""
echo "Step 7: Checking schema version..."
SCHEMA_VERSION=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
    "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1" 2>/dev/null | tr -d ' ')

if [ ! -z "$SCHEMA_VERSION" ]; then
    echo "✓ Schema version: $SCHEMA_VERSION"
else
    echo "⚠ No schema version found"
fi

unset PGPASSWORD

echo ""
echo "=========================================="
echo "Database Schema Import Complete!"
echo "=========================================="
echo ""
echo "Database: $DB_NAME@$DB_HOST"
echo "Tables: $TABLE_COUNT"
echo ""
if [ ! -z "$BACKUP_FILE" ]; then
    echo "Backup: $BACKUP_FILE"
    echo ""
fi
echo "You can now:"
echo "  1. Run the application deployment: ./deploy.sh"
echo "  2. Test the deployment: ./test_deployment.sh"
echo ""
