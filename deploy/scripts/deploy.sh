#!/bin/bash
#
# MxA Mobile Deployment Script
#
# Deploys application updates for app server, python server, or both.
#
# Usage:
#   ./deploy.sh --target app|python|all [--ref <branch-or-tag>] [--repo-url <url>] [--skip-backup]
#

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/nkosinathil/mxa-v2.git}"
APP_DIR="/var/www/mxa-mobile-app"
PYTHON_DIR="/opt/apps/mxa-mobile"
BACKUP_DIR="/var/backups/mxa-mobile"
DEPLOY_REF="${DEPLOY_REF:-main}"
TARGET="${TARGET:-auto}"
SKIP_BACKUP=false
APP_SERVER_IP="${APP_SERVER_IP:-192.168.1.66}"

usage() {
    echo "Usage: $0 --target app|python|all [--ref <branch-or-tag>] [--repo-url <url>] [--app-server-ip <ip>] [--skip-backup]"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target)
            TARGET="$2"
            shift 2
            ;;
        --ref)
            DEPLOY_REF="$2"
            shift 2
            ;;
        --repo-url)
            REPO_URL="$2"
            shift 2
            ;;
        --app-server-ip)
            APP_SERVER_IP="$2"
            shift 2
            ;;
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

if [ -z "$APP_SERVER_IP" ]; then
    echo "APP_SERVER_IP cannot be empty"
    exit 1
fi

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root or with sudo"
    exit 1
fi

if [ "$TARGET" = "auto" ]; then
    HAS_APP=false
    HAS_PYTHON=false
    [ -d "$APP_DIR/current/php-app" ] && HAS_APP=true
    [ -d "$PYTHON_DIR/python-backend" ] && HAS_PYTHON=true

    if [ "$HAS_APP" = true ] && [ "$HAS_PYTHON" = true ]; then
        TARGET="all"
    elif [ "$HAS_APP" = true ]; then
        TARGET="app"
    elif [ "$HAS_PYTHON" = true ]; then
        TARGET="python"
    else
        echo "Unable to auto-detect deployment target. Pass --target app|python|all."
        exit 1
    fi
fi

case "$TARGET" in
    app|python|all) ;;
    *)
        echo "Invalid target: $TARGET"
        usage
        exit 1
        ;;
esac

echo "=== MxA Mobile Deployment ==="
echo "Target: $TARGET"
echo "Deploy ref: $DEPLOY_REF"
echo "Repository: $REPO_URL"
echo "Starting deployment at $(date)"

run_as() {
    local user="$1"
    shift
    sudo -u "$user" "$@"
}

sync_repo() {
    local dir="$1"
    local user="$2"

    if [ ! -d "$dir/.git" ]; then
        mkdir -p "$dir"
        if [ -z "$(ls -A "$dir")" ]; then
            run_as "$user" git clone "$REPO_URL" "$dir"
        else
            run_as "$user" git -C "$dir" init
            if ! run_as "$user" git -C "$dir" remote get-url origin >/dev/null 2>&1; then
                run_as "$user" git -C "$dir" remote add origin "$REPO_URL"
            else
                run_as "$user" git -C "$dir" remote set-url origin "$REPO_URL"
            fi
        fi
    fi

    run_as "$user" git -C "$dir" fetch --all --tags
    run_as "$user" git -C "$dir" checkout "$DEPLOY_REF"

    if run_as "$user" git -C "$dir" rev-parse --verify --quiet "origin/$DEPLOY_REF" >/dev/null; then
        run_as "$user" git -C "$dir" reset --hard "origin/$DEPLOY_REF"
    fi
}

create_backup() {
    local backup_name="$1"
    local source_dir="$2"

    if [ "$SKIP_BACKUP" = true ]; then
        echo "Skipping backup for $backup_name"
        return
    fi

    if [ ! -d "$source_dir" ]; then
        echo "No source directory at $source_dir, skipping backup for $backup_name"
        return
    fi

    mkdir -p "$BACKUP_DIR"
    local backup_file="$BACKUP_DIR/${backup_name}_$(date +%Y%m%d_%H%M%S).tar.gz"
    tar -czf "$backup_file" -C "$source_dir" .
    echo "Backup saved to: $backup_file"
}

restart_or_start() {
    local service="$1"
    if systemctl is-active --quiet "$service"; then
        systemctl restart "$service"
    else
        systemctl start "$service"
    fi
}

ensure_system_user() {
    local user="$1"
    local shell="${2:-/usr/sbin/nologin}"
    local primary_group="${3:-$user}"

    if ! getent group "$primary_group" >/dev/null 2>&1; then
        groupadd --system "$primary_group"
    fi

    if ! id "$user" >/dev/null 2>&1; then
        useradd --system --create-home --gid "$primary_group" --shell "$shell" "$user"
    fi
}

deploy_app() {
    echo ""
    echo "Deploying PHP application..."
    mkdir -p "$APP_DIR"
    chown -R www-data:www-data "$APP_DIR"

    create_backup "php-app" "$APP_DIR/current"
    sync_repo "$APP_DIR/current" "www-data"

    if [ ! -f "$APP_DIR/current/php-app/.env" ]; then
        cp "$APP_DIR/current/php-app/.env.example" "$APP_DIR/current/php-app/.env"
        chown www-data:www-data "$APP_DIR/current/php-app/.env"
        chmod 600 "$APP_DIR/current/php-app/.env"
        echo "Created PHP .env from template; update secrets before go-live."
    fi

    run_as "www-data" composer --working-dir="$APP_DIR/current/php-app" install --no-dev --optimize-autoloader
    run_as "www-data" composer --working-dir="$APP_DIR/current/php-app" dump-autoload -o

    mkdir -p "$APP_DIR/current/php-app/storage/logs"
    chown -R www-data:www-data "$APP_DIR/current"
    chmod -R 755 "$APP_DIR/current"
    chmod -R 775 "$APP_DIR/current/php-app/storage"

    systemctl enable apache2
    restart_or_start apache2
    echo "✓ Apache deployment completed"
}

deploy_python() {
    echo ""
    echo "Deploying Python application..."

    ensure_system_user "celery" "/bin/bash" "celery"
    ensure_system_user "minio" "/usr/sbin/nologin" "minio"
    if id "www-data" >/dev/null 2>&1; then
        usermod -aG celery www-data || true
    fi

    mkdir -p "$PYTHON_DIR"
    chown -R celery:celery "$PYTHON_DIR"
    mkdir -p /var/run/celery
    chown celery:celery /var/run/celery

    create_backup "python-app" "$PYTHON_DIR"
    sync_repo "$PYTHON_DIR" "celery"

    if [ ! -f "$PYTHON_DIR/python-backend/.env" ]; then
        cp "$PYTHON_DIR/python-backend/.env.example" "$PYTHON_DIR/python-backend/.env"
        chown celery:celery "$PYTHON_DIR/python-backend/.env"
        chmod 600 "$PYTHON_DIR/python-backend/.env"
        echo "Created Python .env from template; update secrets before go-live."
    fi

    mkdir -p "$PYTHON_DIR/logs"
    chown -R celery:celery "$PYTHON_DIR/logs"
    chmod -R 775 "$PYTHON_DIR/logs"

    if [ -f "$PYTHON_DIR/deploy/systemd/mxa-mobile-api.service" ]; then
        cp "$PYTHON_DIR/deploy/systemd/mxa-mobile-api.service" /etc/systemd/system/
    fi
    if [ -f "$PYTHON_DIR/deploy/systemd/mxa-mobile-worker.service" ]; then
        cp "$PYTHON_DIR/deploy/systemd/mxa-mobile-worker.service" /etc/systemd/system/
    fi

    if [ ! -d "$PYTHON_DIR/python-backend/venv" ]; then
        run_as "celery" python3 -m venv "$PYTHON_DIR/python-backend/venv"
    fi

    run_as "celery" bash -lc "source '$PYTHON_DIR/python-backend/venv/bin/activate' && pip install --upgrade pip && pip install -r '$PYTHON_DIR/python-backend/requirements.txt'"

    mkdir -p "$PYTHON_DIR/logs"
    chown -R celery:celery "$PYTHON_DIR"
    chmod -R 750 "$PYTHON_DIR"

    # Ensure redis is reachable over LAN by app server.
    redis_ip="$(hostname -I | awk '{print $1}')"
    [ -n "$redis_ip" ] || redis_ip="192.168.1.90"
    for redis_conf in /etc/redis/redis.conf /etc/redis/redis-server.conf; do
        if [ -f "$redis_conf" ]; then
            if grep -q '^[#[:space:]]*bind' "$redis_conf"; then
                sed -i "s/^[#[:space:]]*bind .*/bind 127.0.0.1 $redis_ip/" "$redis_conf"
            else
                echo "bind 127.0.0.1 $redis_ip" >> "$redis_conf"
            fi
            if grep -q '^[#[:space:]]*protected-mode' "$redis_conf"; then
                sed -i "s/^[#[:space:]]*protected-mode .*/protected-mode yes/" "$redis_conf"
            else
                echo "protected-mode yes" >> "$redis_conf"
            fi
            break
        fi
    done

    if command -v ufw >/dev/null 2>&1; then
        ufw allow from "$APP_SERVER_IP" to any port 8104 || true
        ufw allow from "$APP_SERVER_IP" to any port 9000 || true
        ufw allow from "$APP_SERVER_IP" to any port 6379 || true
    fi

    systemctl daemon-reload
    systemctl enable redis-server
    systemctl enable mxa-mobile-api
    systemctl enable mxa-mobile-worker
    restart_or_start redis-server
    restart_or_start mxa-mobile-api
    restart_or_start mxa-mobile-worker
    echo "✓ Python services restarted"

    sleep 5
    if curl -fsS --max-time 10 http://localhost:8104/health >/dev/null 2>&1; then
        echo "✓ FastAPI health check passed"
    else
        echo "✗ FastAPI health check failed"
        exit 1
    fi
}

if [ "$TARGET" = "app" ] || [ "$TARGET" = "all" ]; then
    deploy_app
fi

if [ "$TARGET" = "python" ] || [ "$TARGET" = "all" ]; then
    deploy_python
fi

echo ""
echo "=== Deployment completed successfully at $(date) ==="
