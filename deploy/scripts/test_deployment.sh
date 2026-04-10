#!/bin/bash
#
# MxA Mobile - End-to-End Deployment Test
# Tests all components of the deployment
#
# Prerequisites:
# - All servers set up and services running
#

set -e

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

# Test function
test_endpoint() {
    local name="$1"
    local url="$2"
    local expected_code="${3:-200}"
    
    echo -n "Testing $name... "
    
    http_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" --max-time 10)
    
    if [ "$http_code" == "$expected_code" ]; then
        echo "✓ PASS (HTTP $http_code)"
        ((PASSED++))
        return 0
    else
        echo "✗ FAIL (HTTP $http_code, expected $expected_code)"
        ((FAILED++))
        return 1
    fi
}

# Test PostgreSQL
test_postgresql() {
    echo -n "Testing PostgreSQL... "
    
    export PGPASSWORD="$DB_PASSWORD"
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" &>/dev/null; then
        echo "✓ PASS"
        ((PASSED++))
        unset PGPASSWORD
        return 0
    else
        echo "✗ FAIL"
        ((FAILED++))
        unset PGPASSWORD
        return 1
    fi
}

# Test MinIO
test_minio() {
    echo -n "Testing MinIO... "
    
    http_code=$(curl -s -o /dev/null -w "%{http_code}" "$MINIO_URL/minio/health/live" --max-time 10)
    
    if [ "$http_code" == "200" ]; then
        echo "✓ PASS"
        ((PASSED++))
        return 0
    else
        echo "✗ FAIL (HTTP $http_code)"
        ((FAILED++))
        return 1
    fi
}

# Test Redis
test_redis() {
    echo -n "Testing Redis... "
    
    if timeout 2 bash -c "cat < /dev/null > /dev/tcp/192.168.1.90/6379" 2>/dev/null; then
        echo "✓ PASS (port 6379 reachable)"
        ((PASSED++))
        return 0
    else
        echo "✗ FAIL (port 6379 not reachable)"
        ((FAILED++))
        return 1
    fi
}

# Test systemd services
test_service() {
    local service="$1"
    local host="${2:-localhost}"
    
    echo -n "Testing service $service... "
    
    if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$host" "systemctl is-active --quiet $service" 2>/dev/null; then
        echo "✓ PASS"
        ((PASSED++))
        return 0
    else
        # If SSH fails, try local
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            echo "✓ PASS (local)"
            ((PASSED++))
            return 0
        else
            echo "✗ FAIL"
            ((FAILED++))
            return 1
        fi
    fi
}

echo ""
echo "=== Testing SSO Server (192.168.1.59) ==="
test_endpoint "Keycloak" "$SSO_URL/health"

echo ""
echo "=== Testing Application Server (192.168.1.66) ==="
test_endpoint "PHP Web Application" "$APP_URL" "200"
test_postgresql
test_service "apache2"
test_service "postgresql"

echo ""
echo "=== Testing Python Server (192.168.1.90) ==="
test_endpoint "FastAPI Health" "$PYTHON_URL/health"
test_endpoint "FastAPI Readiness" "$PYTHON_URL/health/ready"
test_minio
test_redis
test_service "mxa-mobile-api"
test_service "mxa-mobile-worker"
test_service "minio"
test_service "redis-server"

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

if [ "$TABLE_COUNT" -gt 10 ]; then
    echo "✓ PASS ($TABLE_COUNT tables)"
    ((PASSED++))
else
    echo "✗ FAIL ($TABLE_COUNT tables, expected > 10)"
    ((FAILED++))
fi

echo ""
echo "=== Testing Network Connectivity ==="
echo -n "Testing App Server -> Python Server... "
if curl -f -s --max-time 5 "$PYTHON_URL/health" > /dev/null 2>&1; then
    echo "✓ PASS"
    ((PASSED++))
else
    echo "✗ FAIL"
    ((FAILED++))
fi

echo -n "Testing App Server -> SSO Server... "
if curl -f -s --max-time 5 "$SSO_URL/health" > /dev/null 2>&1; then
    echo "✓ PASS"
    ((PASSED++))
else
    echo "✗ FAIL"
    ((FAILED++))
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
