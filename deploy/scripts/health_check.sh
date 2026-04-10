#!/bin/bash
#
# MxA Mobile - System Health Check
# Monitors system health and reports status
#

echo "=========================================="
echo "MxA Mobile - Health Check"
echo "=========================================="
echo "Time: $(date)"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check function
check_service() {
    local service=$1
    local name=$2
    
    if systemctl is-active --quiet "$service"; then
        echo -e "${GREEN}✓${NC} $name is running"
        return 0
    else
        echo -e "${RED}✗${NC} $name is NOT running"
        return 1
    fi
}

check_port() {
    local host=$1
    local port=$2
    local name=$3
    
    if timeout 2 bash -c "cat < /dev/null > /dev/tcp/$host/$port" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $name is accessible ($host:$port)"
        return 0
    else
        echo -e "${RED}✗${NC} $name is NOT accessible ($host:$port)"
        return 1
    fi
}

check_url() {
    local url=$1
    local name=$2
    
    if curl -f -s --max-time 5 "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $name is responding ($url)"
        return 0
    else
        echo -e "${RED}✗${NC} $name is NOT responding ($url)"
        return 1
    fi
}

# System Resources
echo "=== System Resources ==="
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1"%"}')"
echo "Memory Usage: $(free -m | awk 'NR==2{printf "%.2f%%", $3*100/$2 }')"
echo "Disk Usage: $(df -h / | awk 'NR==2{print $5}')"
echo ""

# Services
echo "=== Services Status ==="
check_service "apache2" "Apache Web Server"
check_service "postgresql" "PostgreSQL"
check_service "mxa-mobile-api" "FastAPI Service"
check_service "mxa-mobile-worker" "Celery Worker"
check_service "redis-server" "Redis"
check_service "minio" "MinIO"
echo ""

# Network Connectivity
echo "=== Network Connectivity ==="
check_port "192.168.1.59" "8080" "Keycloak SSO"
check_port "192.168.1.66" "80" "Web Application"
check_port "192.168.1.66" "5432" "PostgreSQL"
check_port "192.168.1.90" "8104" "FastAPI"
check_port "192.168.1.90" "9000" "MinIO"
check_port "192.168.1.90" "6379" "Redis"
echo ""

# HTTP Endpoints
echo "=== HTTP Endpoints ==="
check_url "http://192.168.1.59:8080/health" "Keycloak"
check_url "http://192.168.1.66" "Web Application"
check_url "http://192.168.1.90:8104/health" "FastAPI Health"
check_url "http://192.168.1.90:8104/health/ready" "FastAPI Readiness"
check_url "http://192.168.1.90:9000/minio/health/live" "MinIO"
echo ""

# Database
echo "=== Database ==="
if [ ! -z "$DB_PASSWORD" ]; then
    export PGPASSWORD="$DB_PASSWORD"
    if psql -h 192.168.1.66 -U mxa_mobile_user -d mxa_mobile -c "SELECT 1" &>/dev/null; then
        echo -e "${GREEN}✓${NC} PostgreSQL is accessible"
        
        # Count records
        USERS=$(psql -h 192.168.1.66 -U mxa_mobile_user -d mxa_mobile -t -c "SELECT COUNT(*) FROM users" 2>/dev/null | tr -d ' ')
        CASES=$(psql -h 192.168.1.66 -U mxa_mobile_user -d mxa_mobile -t -c "SELECT COUNT(*) FROM cases" 2>/dev/null | tr -d ' ')
        JOBS=$(psql -h 192.168.1.66 -U mxa_mobile_user -d mxa_mobile -t -c "SELECT COUNT(*) FROM processing_jobs" 2>/dev/null | tr -d ' ')
        
        echo "  Users: $USERS"
        echo "  Cases: $CASES"
        echo "  Jobs: $JOBS"
    else
        echo -e "${RED}✗${NC} PostgreSQL is NOT accessible"
    fi
    unset PGPASSWORD
else
    echo -e "${YELLOW}⚠${NC} DB_PASSWORD not set, skipping database checks"
fi
echo ""

# Disk Space
echo "=== Disk Space Warnings ==="
df -h | awk '$5+0 > 80 {print "⚠ " $6 " is " $5 " full"}'
if [ $(df -h | awk '$5+0 > 80' | wc -l) -eq 0 ]; then
    echo "No warnings"
fi
echo ""

# Recent Errors
echo "=== Recent Application Errors ==="
if [ -f "/var/www/mxa-mobile-app/current/php-app/storage/logs/app.log" ]; then
    ERROR_COUNT=$(grep -i error /var/www/mxa-mobile-app/current/php-app/storage/logs/app.log 2>/dev/null | tail -24h | wc -l)
    echo "PHP errors (last 24h): $ERROR_COUNT"
fi

if [ -f "/opt/apps/mxa-mobile/logs/api.log" ]; then
    ERROR_COUNT=$(grep -i error /opt/apps/mxa-mobile/logs/api.log 2>/dev/null | tail -24h | wc -l)
    echo "Python errors (last 24h): $ERROR_COUNT"
fi
echo ""

echo "=========================================="
echo "Health check complete"
echo "=========================================="
