#!/bin/bash
#
# MxA Mobile - End-to-End Deployment Test
# Tests all components of the deployment
#
# Prerequisites:
# - All servers set up and services running
#

set -euo pipefail

echo "=========================================="
echo "MxA Mobile - Deployment Test"
echo "=========================================="

# Configuration
SSO_URL="${SSO_URL:-http://192.168.1.59:8080}"
APP_URL="${APP_URL:-http://192.168.1.66}"
PYTHON_URL="${PYTHON_URL:-http://192.168.1.90:8104}"
MINIO_URL="${MINIO_URL:-http://192.168.1.90:9000}"
DB_HOST="${DB_HOST:-192.168.1.66}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-mxa_mobile}"
DB_USER="${DB_USER:-mxa_mobile_user}"
DB_PASSWORD="${DB_PASSWORD}"

PASSED=0
FAILED=0
CURRENT_HOST_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"

if [ -z "${DB_PASSWORD:-}" ]; then
    echo "DB_PASSWORD must be set (export DB_PASSWORD=...)"
    exit 1
fi

# Test function
test_endpoint() {
    local name="$1"
    local url="$2"
    local expected_code="${3:-200}"
    
    echo -n "Testing $name... "
    
    http_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" --max-time 10 || true)
    if [ -z "$http_code" ]; then
        http_code="000"
    fi
    
    if [ "$http_code" == "$expected_code" ]; then
        echo "✓ PASS (HTTP $http_code)"
        PASSED=$((PASSED + 1))
    else
        echo "✗ FAIL (HTTP $http_code, expected $expected_code)"
        FAILED=$((FAILED + 1))
    fi

    return 0
}

# Test PostgreSQL
test_postgresql() {
    echo -n "Testing PostgreSQL... "
    
    export PGPASSWORD="$DB_PASSWORD"
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" &>/dev/null; then
        echo "✓ PASS"
        PASSED=$((PASSED + 1))
        unset PGPASSWORD
    else
        echo "✗ FAIL"
        FAILED=$((FAILED + 1))
        unset PGPASSWORD
    fi

    return 0
}

# Test MinIO
test_minio() {
    echo -n "Testing MinIO... "
    
    http_code=$(curl -s -o /dev/null -w "%{http_code}" "$MINIO_URL/minio/health/live" --max-time 10 || true)
    if [ -z "$http_code" ]; then
        http_code="000"
    fi
    
    if [ "$http_code" == "200" ]; then
        echo "✓ PASS"
        PASSED=$((PASSED + 1))
    else
        echo "✗ FAIL (HTTP $http_code)"
        FAILED=$((FAILED + 1))
    fi

    return 0
}

# Test Redis
test_redis() {
    echo -n "Testing Redis... "
    local redis_host redis_port
    redis_host="$(echo "$PYTHON_URL" | sed -E 's#^https?://([^:/]+).*$#\1#')"
    redis_port="${REDIS_PORT:-6379}"
    
    if timeout 2 bash -c "cat < /dev/null > /dev/tcp/$redis_host/$redis_port" 2>/dev/null; then
        echo "✓ PASS (port $redis_port reachable)"
        PASSED=$((PASSED + 1))
    else
        echo "✗ FAIL (port $redis_port not reachable)"
        FAILED=$((FAILED + 1))
    fi

    return 0
}

# Test systemd service on an explicit host.
# If host is local, check locally. For remote host, require SSH check.
test_service() {
    local service="$1"
    local host="$2"
    
    echo -n "Testing service $service on $host... "
    
    if [ "$host" = "localhost" ] || [ "$host" = "127.0.0.1" ] || [ "$host" = "$CURRENT_HOST_IP" ]; then
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            echo "✓ PASS"
            PASSED=$((PASSED + 1))
            return 0
        fi
        echo "✗ FAIL"
        FAILED=$((FAILED + 1))
        return 0
    fi

    if ssh -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no "$host" "systemctl is-active --quiet $service" 2>/dev/null; then
        echo "✓ PASS"
        PASSED=$((PASSED + 1))
        return 0
    fi

    echo "✗ FAIL (remote check failed; ensure SSH access)"
    FAILED=$((FAILED + 1))
    return 0
}

echo ""
echo "=== Testing SSO Server ==="
test_endpoint "Keycloak OIDC discovery" "$SSO_URL/realms/master/.well-known/openid-configuration"

echo ""
echo "=== Testing Application Server ==="
test_endpoint "PHP Web Application" "$APP_URL" "200"
test_postgresql
test_service "apache2" "192.168.1.66"
test_service "postgresql" "192.168.1.66"

echo ""
echo "=== Testing Python Server ==="
test_endpoint "FastAPI Health" "$PYTHON_URL/health"
test_endpoint "FastAPI Readiness" "$PYTHON_URL/health/ready"
test_minio
test_redis
test_service "mxa-mobile-api" "192.168.1.90"
test_service "mxa-mobile-worker" "192.168.1.90"
test_service "minio" "192.168.1.90"
test_service "redis-server" "192.168.1.90"

echo ""
echo "=== Testing API Endpoints ==="
test_endpoint "Jobs API" "$PYTHON_URL/api/jobs" "401"  # Expected 401 without auth
test_endpoint "Cases API" "$PYTHON_URL/api/cases" "401"  # Expected 401 without auth

echo ""
echo "=== Testing Database Schema ==="
echo -n "Checking tables... "
export PGPASSWORD="$DB_PASSWORD"
TABLE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'" 2>/dev/null | tr -d ' ')
unset PGPASSWORD

if ! [[ "${TABLE_COUNT:-}" =~ ^[0-9]+$ ]]; then
    TABLE_COUNT=0
fi

if [ "$TABLE_COUNT" -gt 10 ]; then
    echo "✓ PASS ($TABLE_COUNT tables)"
    PASSED=$((PASSED + 1))
else
    echo "✗ FAIL ($TABLE_COUNT tables, expected > 10)"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "=== Testing Network Connectivity ==="
echo -n "Testing App Server -> Python Server... "
if curl -f -s --max-time 5 "$PYTHON_URL/health" > /dev/null 2>&1; then
    echo "✓ PASS"
    PASSED=$((PASSED + 1))
else
    echo "✗ FAIL"
    FAILED=$((FAILED + 1))
fi

echo -n "Testing App Server -> SSO Server... "
if curl -f -s --max-time 5 "$SSO_URL/realms/master/.well-known/openid-configuration" > /dev/null 2>&1; then
    echo "✓ PASS"
    PASSED=$((PASSED + 1))
else
    echo "✗ FAIL"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "=========================================="
echo "Test Results Summary"
echo "=========================================="
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "Total:  $((PASSED + FAILED))"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "✓ All tests passed!"
    echo ""
    echo "Deployment is ready for use:"
    echo "  Web Application: $APP_URL"
    echo "  Admin Console: $SSO_URL"
    echo ""
    echo "Test credentials:"
    echo "  Username: admin"
    echo "  Password: admin123"
    echo ""
    exit 0
else
    echo "✗ Some tests failed!"
    echo ""
    echo "Please check:"
    echo "  - All services are running"
    echo "  - Network connectivity between servers"
    echo "  - Configuration files (.env)"
    echo "  - Logs in /var/log/ and service logs"
    echo ""
    exit 1
fi
