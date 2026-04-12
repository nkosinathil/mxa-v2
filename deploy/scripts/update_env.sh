#!/bin/bash
#
# MxA Mobile - Update .env Files
# Injects shared configuration (Keycloak client secret, DB password, MinIO key)
# into both the PHP and Python .env files after initial setup.
#
# Usage (non-interactive):
#   KEYCLOAK_CLIENT_SECRET=<secret> DB_PASSWORD=<pass> MINIO_SECRET_KEY=<secret> ./update_env.sh
#

set -euo pipefail

echo "=========================================="
echo "MxA Mobile - Update .env Files"
echo "=========================================="

PHP_ENV="/var/www/mxa-mobile-app/current/php-app/.env"
PYTHON_ENV="/opt/apps/mxa-mobile/python-backend/.env"
KEYCLOAK_CLIENT_SECRET="${KEYCLOAK_CLIENT_SECRET:-}"
DB_PASSWORD="${DB_PASSWORD:-}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-${MINIO_ROOT_PASSWORD:-}}"
APP_KEY="${APP_KEY:-}"

if [ -z "$KEYCLOAK_CLIENT_SECRET" ] && [ -z "$DB_PASSWORD" ] && [ -z "$MINIO_SECRET_KEY" ] && [ -z "$APP_KEY" ]; then
    echo "At least one of KEYCLOAK_CLIENT_SECRET, DB_PASSWORD, MINIO_SECRET_KEY/MINIO_ROOT_PASSWORD, or APP_KEY must be set."
    exit 1
fi

# ─────────────────────────────────────────────
# Helper: update or append a key=value in a file
# ─────────────────────────────────────────────
upsert_env() {
    local file="$1"
    local key="$2"
    local value="$3"

    if [ -z "$value" ]; then
        return
    fi

    # Escape special characters in value for sed
    local escaped
    escaped=$(printf '%s\n' "$value" | sed 's/[\/&]/\\&/g')

    if grep -q "^${key}=" "$file" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${escaped}|" "$file"
    else
        echo "${key}=${escaped}" >> "$file"
    fi
}

# ─────────────────────────────────────────────
# Update PHP .env
# ─────────────────────────────────────────────
echo ""
echo "Step 1: Updating PHP .env ($PHP_ENV)..."
if [ ! -f "$PHP_ENV" ]; then
    echo "✗ PHP .env not found: $PHP_ENV"
    echo "  Run 2_setup_app_server.sh first."
else
    PHP_APP_KEY="$APP_KEY"
    if [ -z "$PHP_APP_KEY" ]; then
        CURRENT_APP_KEY="$(sed -n 's/^APP_KEY=//p' "$PHP_ENV" | head -n 1)"
        if [ -z "$CURRENT_APP_KEY" ]; then
            PHP_APP_KEY="$(openssl rand -base64 32)"
            echo "Generated PHP APP_KEY."
        fi
    fi

    upsert_env "$PHP_ENV" "KEYCLOAK_CLIENT_SECRET" "$KEYCLOAK_CLIENT_SECRET"
    upsert_env "$PHP_ENV" "DB_PASSWORD"            "$DB_PASSWORD"
    upsert_env "$PHP_ENV" "APP_KEY"                "$PHP_APP_KEY"

    chown www-data:www-data "$PHP_ENV"
    chmod 600 "$PHP_ENV"
    echo "✓ PHP .env updated"
fi

# ─────────────────────────────────────────────
# Update Python .env
# ─────────────────────────────────────────────
echo ""
echo "Step 2: Updating Python .env ($PYTHON_ENV)..."
if [ ! -f "$PYTHON_ENV" ]; then
    echo "✗ Python .env not found: $PYTHON_ENV"
    echo "  Run 3_setup_python_server.sh first."
else
    upsert_env "$PYTHON_ENV" "KEYCLOAK_CLIENT_SECRET" "$KEYCLOAK_CLIENT_SECRET"
    upsert_env "$PYTHON_ENV" "DB_PASSWORD"             "$DB_PASSWORD"
    upsert_env "$PYTHON_ENV" "MINIO_SECRET_KEY"        "$MINIO_SECRET_KEY"

    chown celery:celery "$PYTHON_ENV"
    chmod 600 "$PYTHON_ENV"
    echo "✓ Python .env updated"
fi

# ─────────────────────────────────────────────
# Restart services so they pick up new config
# ─────────────────────────────────────────────
echo ""
echo "Step 3: Restarting services..."

if systemctl is-active --quiet apache2 2>/dev/null; then
    systemctl reload apache2
    echo "✓ Apache reloaded"
fi

if systemctl is-active --quiet mxa-mobile-api 2>/dev/null; then
    systemctl restart mxa-mobile-api
    echo "✓ FastAPI restarted"
fi

if systemctl is-active --quiet mxa-mobile-worker 2>/dev/null; then
    systemctl restart mxa-mobile-worker
    echo "✓ Celery worker restarted"
fi

echo ""
echo "=========================================="
echo "Configuration update complete!"
echo "=========================================="
echo ""
echo "Run tests to verify:"
echo "  ./test_deployment.sh"
echo ""
