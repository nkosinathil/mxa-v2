#!/bin/bash
#
# MxA Mobile - Update .env Files
# Injects shared configuration (Keycloak client secret, DB password, MinIO key)
# into both the PHP and Python .env files after initial setup.
#
# Usage:
#   KEYCLOAK_CLIENT_SECRET=<secret> DB_PASSWORD=<pass> ./update_env.sh
#
# Or interactively (prompts for each value if not set via environment):
#   ./update_env.sh
#

set -e

echo "=========================================="
echo "MxA Mobile - Update .env Files"
echo "=========================================="

PHP_ENV="/var/www/mxa-mobile-app/current/php-app/.env"
PYTHON_ENV="/opt/apps/mxa-mobile/python-backend/.env"

# ─────────────────────────────────────────────
# Gather values (env var or prompt)
# ─────────────────────────────────────────────

get_value() {
    local var_name="$1"
    local prompt_text="$2"
    local current="${!var_name}"

    if [ -n "$current" ]; then
        echo "$current"
    else
        read -rsp "$prompt_text: " val
        echo ""
        echo "$val"
    fi
}

echo ""
echo "Enter configuration values (press Enter to skip / keep existing)."
echo ""

KEYCLOAK_CLIENT_SECRET=$(get_value "KEYCLOAK_CLIENT_SECRET" "Keycloak Client Secret")
DB_PASSWORD=$(get_value "DB_PASSWORD"              "Database Password")
MINIO_SECRET_KEY=$(get_value "MINIO_SECRET_KEY"        "MinIO Secret Key")
APP_KEY=$(get_value "APP_KEY"                  "PHP App Key (leave blank to auto-generate)")

if [ -z "$APP_KEY" ]; then
    APP_KEY=$(openssl rand -base64 32)
    echo "Generated PHP APP_KEY."
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
    upsert_env "$PHP_ENV" "KEYCLOAK_CLIENT_SECRET" "$KEYCLOAK_CLIENT_SECRET"
    upsert_env "$PHP_ENV" "DB_PASSWORD"            "$DB_PASSWORD"
    upsert_env "$PHP_ENV" "APP_KEY"                "$APP_KEY"

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
