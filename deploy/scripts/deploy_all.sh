#!/bin/bash
#
# MxA Mobile - Master Deployment Script (Non-Interactive)
# Orchestrates deployment across all servers via SSH.
#
# Usage:
#   ./deploy_all.sh --db-password <pass> --minio-root-password <pass> --keycloak-admin-password <pass> [options]
#

set -euo pipefail

SSO_HOST="${SSO_HOST:-192.168.1.59}"
APP_HOST="${APP_HOST:-192.168.1.66}"
PYTHON_HOST="${PYTHON_HOST:-192.168.1.90}"
SSH_USER="${SSH_USER:-root}"
SSH_OPTS=(-o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=10)

SKIP_SETUP=false
SKIP_KEYCLOAK=false
SKIP_DB=false
SKIP_DEPLOY=false
SKIP_TESTS=false
DEPLOY_REF="${DEPLOY_REF:-main}"
REPO_URL="${REPO_URL:-https://github.com/nkosinathil/mxa-v2.git}"

DB_PASSWORD="${DB_PASSWORD:-}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-}"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-}"
KEYCLOAK_HOSTNAME="${KEYCLOAK_HOSTNAME:-$SSO_HOST}"
KEYCLOAK_CLIENT_SECRET="${KEYCLOAK_CLIENT_SECRET:-}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-}"

quote_sq() {
    printf "%s" "$1" | sed "s/'/'\"'\"'/g"
}

usage() {
    cat <<EOF
Usage:
  $0 --db-password <pass> --minio-root-password <pass> --keycloak-admin-password <pass> [options]

Required:
  --db-password <pass>
  --minio-root-password <pass>
  --keycloak-admin-password <pass>

Optional:
  --ref <branch-or-tag>           Deployment git ref (default: main)
  --repo-url <url>                Repository URL
  --ssh-user <user>               SSH user for all hosts (default: root)
  --sso-host <host>               SSO host/IP (default: 192.168.1.59)
  --app-host <host>               App host/IP (default: 192.168.1.66)
  --python-host <host>            Python host/IP (default: 192.168.1.90)
  --keycloak-hostname <host>      Keycloak external hostname (default: sso-host)
  --keycloak-client-secret <sec>  Skip Keycloak config and use provided client secret for .env updates
  --minio-secret-key <sec>        Secret written to Python .env (defaults to --minio-root-password)
  --skip-setup                    Skip all server setup scripts
  --skip-keycloak                 Skip Keycloak configure script
  --skip-db                       Skip DB import
  --skip-deploy                   Skip deploy.sh runs
  --skip-tests                    Skip test_deployment.sh
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-setup) SKIP_SETUP=true; shift ;;
        --skip-keycloak) SKIP_KEYCLOAK=true; shift ;;
        --skip-db) SKIP_DB=true; shift ;;
        --skip-deploy) SKIP_DEPLOY=true; shift ;;
        --skip-tests) SKIP_TESTS=true; shift ;;
        --ref) DEPLOY_REF="$2"; shift 2 ;;
        --repo-url) REPO_URL="$2"; shift 2 ;;
        --ssh-user) SSH_USER="$2"; shift 2 ;;
        --sso-host) SSO_HOST="$2"; shift 2 ;;
        --app-host) APP_HOST="$2"; shift 2 ;;
        --python-host) PYTHON_HOST="$2"; shift 2 ;;
        --db-password) DB_PASSWORD="$2"; shift 2 ;;
        --minio-root-password) MINIO_ROOT_PASSWORD="$2"; shift 2 ;;
        --keycloak-admin-password) KEYCLOAK_ADMIN_PASSWORD="$2"; shift 2 ;;
        --keycloak-hostname) KEYCLOAK_HOSTNAME="$2"; shift 2 ;;
        --keycloak-client-secret) KEYCLOAK_CLIENT_SECRET="$2"; shift 2 ;;
        --minio-secret-key) MINIO_SECRET_KEY="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
done

if [ -z "$DB_PASSWORD" ] || [ -z "$MINIO_ROOT_PASSWORD" ] || [ -z "$KEYCLOAK_ADMIN_PASSWORD" ]; then
    echo "Missing required secrets."
    usage
    exit 1
fi

if [ -z "$MINIO_SECRET_KEY" ]; then
    MINIO_SECRET_KEY="$MINIO_ROOT_PASSWORD"
fi

q_repo_url="$(quote_sq "$REPO_URL")"
q_deploy_ref="$(quote_sq "$DEPLOY_REF")"
q_db_password="$(quote_sq "$DB_PASSWORD")"
q_minio_root_password="$(quote_sq "$MINIO_ROOT_PASSWORD")"
q_keycloak_admin_password="$(quote_sq "$KEYCLOAK_ADMIN_PASSWORD")"
q_keycloak_hostname="$(quote_sq "$KEYCLOAK_HOSTNAME")"
q_sso_host="$(quote_sq "$SSO_HOST")"
q_app_host="$(quote_sq "$APP_HOST")"
q_python_host="$(quote_sq "$PYTHON_HOST")"
q_minio_secret_key="$(quote_sq "$MINIO_SECRET_KEY")"

echo "=========================================="
echo "MxA Mobile - Non-Interactive Deployment"
echo "=========================================="
echo "SSO Host:        $SSO_HOST"
echo "App Host:        $APP_HOST"
echo "Python Host:     $PYTHON_HOST"
echo "SSH User:        $SSH_USER"
echo "Deploy Ref:      $DEPLOY_REF"
echo "Repo URL:        $REPO_URL"
echo ""

ssh_host() {
    local host="$1"
    shift
    ssh "${SSH_OPTS[@]}" "${SSH_USER}@${host}" "$@"
}

sync_repo_on_host() {
    local host="$1"
    ssh_host "$host" "set -euo pipefail; if [ ! -d ~/mxa-v2/.git ]; then rm -rf ~/mxa-v2; git clone '$q_repo_url' ~/mxa-v2; fi; git -C ~/mxa-v2 fetch --all --tags; git -C ~/mxa-v2 checkout '$q_deploy_ref'; if git -C ~/mxa-v2 rev-parse --verify --quiet 'origin/$q_deploy_ref' >/dev/null; then git -C ~/mxa-v2 reset --hard 'origin/$q_deploy_ref'; fi"
}

run_remote_script() {
    local host="$1"
    local script_rel="$2"
    local env_exports="$3"
    local script_args="${4:-}"
    ssh_host "$host" "set -euo pipefail; cd ~/mxa-v2; chmod +x deploy/scripts/*.sh; export REPO_URL='$q_repo_url' DEPLOY_REF='$q_deploy_ref'; $env_exports; sudo -E bash '$script_rel' $script_args"
}

require_tools_on_host() {
    local host="$1"
    shift
    local tools=("$@")
    local missing=()
    for tool in "${tools[@]}"; do
        if ! ssh_host "$host" "command -v '$tool' >/dev/null 2>&1"; then
            missing+=("$tool")
        fi
    done
    if [ "${#missing[@]}" -gt 0 ]; then
        echo "Host $host is missing required tools: ${missing[*]}"
        exit 1
    fi
}

if [ "$SKIP_SETUP" = false ]; then
    echo "Phase 1: server setup"
    require_tools_on_host "$SSO_HOST" git sudo
    require_tools_on_host "$APP_HOST" git sudo
    require_tools_on_host "$PYTHON_HOST" git sudo
    sync_repo_on_host "$SSO_HOST"
    sync_repo_on_host "$APP_HOST"
    sync_repo_on_host "$PYTHON_HOST"

    run_remote_script "$SSO_HOST" "deploy/scripts/1_setup_sso_server.sh" "export KEYCLOAK_ADMIN_PASSWORD='$q_keycloak_admin_password' KEYCLOAK_HOSTNAME='$q_keycloak_hostname'"
    run_remote_script "$APP_HOST" "deploy/scripts/2_setup_app_server.sh" "export DB_PASSWORD='$q_db_password'"
    run_remote_script "$PYTHON_HOST" "deploy/scripts/3_setup_python_server.sh" "export DB_PASSWORD='$q_db_password' MINIO_ROOT_PASSWORD='$q_minio_root_password'"
fi

if [ "$SKIP_KEYCLOAK" = false ]; then
    echo "Phase 2: Keycloak configuration"
    require_tools_on_host "$SSO_HOST" awk sed tee jq
    sync_repo_on_host "$SSO_HOST"
    ssh_host "$SSO_HOST" "set -euo pipefail; cd ~/mxa-v2; chmod +x deploy/scripts/*.sh; export KEYCLOAK_ADMIN_PASSWORD='$q_keycloak_admin_password' KEYCLOAK_URL='http://$q_sso_host:8080'; ./deploy/scripts/configure_keycloak.sh | tee /tmp/mxa_keycloak_config.log"

    KEYCLOAK_CLIENT_SECRET="$(ssh_host "$SSO_HOST" "set -euo pipefail; awk -F': ' '/Client Secret:/ {print \$2}' /tmp/mxa_keycloak_config.log | tail -n1")"
    if [ -z "${KEYCLOAK_CLIENT_SECRET:-}" ]; then
        echo "Failed to extract Keycloak client secret from configure_keycloak.sh output."
        exit 1
    fi
fi

if [ -z "${KEYCLOAK_CLIENT_SECRET:-}" ]; then
    echo "No KEYCLOAK_CLIENT_SECRET available. Pass --keycloak-client-secret or run without --skip-keycloak."
    exit 1
fi
q_keycloak_client_secret="$(quote_sq "$KEYCLOAK_CLIENT_SECRET")"

echo "Phase 2b: Updating .env files"
sync_repo_on_host "$APP_HOST"
sync_repo_on_host "$PYTHON_HOST"
run_remote_script "$APP_HOST" "deploy/scripts/update_env.sh" "export KEYCLOAK_CLIENT_SECRET='$q_keycloak_client_secret' DB_PASSWORD='$q_db_password'"
run_remote_script "$PYTHON_HOST" "deploy/scripts/update_env.sh" "export KEYCLOAK_CLIENT_SECRET='$q_keycloak_client_secret' DB_PASSWORD='$q_db_password' MINIO_SECRET_KEY='$q_minio_secret_key'"

if [ "$SKIP_DB" = false ]; then
    echo "Phase 3: database import"
    run_remote_script "$APP_HOST" "deploy/scripts/import_database.sh" "export DB_PASSWORD='$q_db_password' FORCE_REIMPORT=true"
fi

if [ "$SKIP_DEPLOY" = false ]; then
    echo "Phase 4: application deployment"
    run_remote_script "$APP_HOST" "deploy/scripts/deploy.sh" "" "--target app --app-server-ip '$q_app_host'"
    run_remote_script "$PYTHON_HOST" "deploy/scripts/deploy.sh" "" "--target python --app-server-ip '$q_app_host'"
fi

if [ "$SKIP_TESTS" = false ]; then
    echo "Phase 5: deployment tests"
    run_remote_script "$APP_HOST" "deploy/scripts/test_deployment.sh" "export DB_PASSWORD='$q_db_password' SSO_URL='http://$q_sso_host:8080' APP_URL='http://$q_app_host' PYTHON_URL='http://$q_python_host:8104' MINIO_URL='http://$q_python_host:9000'"
fi

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo "Web UI:   http://$APP_HOST"
echo "API:      http://$PYTHON_HOST:8104"
echo "Keycloak: http://$SSO_HOST:8080"
