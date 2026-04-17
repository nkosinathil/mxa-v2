# MxA Mobile Deployment - Detailed Workflow

## Overview

This document provides a detailed step-by-step workflow for deploying MxA Mobile.

## Deployment Phases

```
Phase 1: Server Setup (30-60 minutes)
    ↓
Phase 2: Keycloak Configuration (10 minutes)
    ↓
Phase 3: Database Import (5 minutes)
    ↓
Phase 4: Application Deployment (10 minutes)
    ↓
Phase 5: Testing & Verification (10 minutes)
```

---

## Phase 1: Server Setup

### 1.1 SSO Server Setup (192.168.1.59)

**Estimated Time**: 15-20 minutes

```bash
# SSH to SSO server
ssh root@192.168.1.59

# Download repository
git clone https://github.com/nkosinathil/mxa-v2.git
cd mxa-v2/deploy/scripts

# Run setup
sudo ./1_setup_sso_server.sh
```

**What it does**:
- ✅ Installs Java 11
- ✅ Creates keycloak user
- ✅ Downloads Keycloak 23.0.0
- ✅ Creates systemd service
- ✅ Starts Keycloak

**Verification**:
```bash
systemctl status keycloak
curl http://localhost:8080/health
```

**Expected Output**: Keycloak running on port 8080

---

### 1.2 Application Server Setup (192.168.1.66)

**Estimated Time**: 20-25 minutes

```bash
# SSH to application server
ssh root@192.168.1.66

# Download repository
git clone https://github.com/nkosinathil/mxa-v2.git
cd mxa-v2/deploy/scripts

# Set database password
export DB_PASSWORD="YourSecurePassword123!"

# Run setup
sudo -E ./2_setup_app_server.sh
```

**What it does**:
- ✅ Installs Apache 2.4 + PHP 8.1
- ✅ Installs PostgreSQL
- ✅ Creates database and user
- ✅ Clones application code
- ✅ Installs Composer dependencies
- ✅ Configures Apache
- ✅ Creates .env file

**Verification**:
```bash
systemctl status apache2
systemctl status postgresql
curl http://localhost
psql -U mxa_mobile_user -d mxa_mobile -c "SELECT 1"
```

**Expected Output**: 
- Apache running on port 80
- PostgreSQL running on port 5432
- Database accessible

---

### 1.3 Python Server Setup (192.168.1.90)

**Estimated Time**: 25-30 minutes

```bash
# SSH to Python server
ssh root@192.168.1.90

# Download repository
git clone https://github.com/nkosinathil/mxa-v2.git
cd mxa-v2/deploy/scripts

# Set passwords
export DB_PASSWORD="YourSecurePassword123!"
export MINIO_ROOT_USER="minioadmin"
export MINIO_ROOT_PASSWORD="MinIOPassword123!"

# Run setup
sudo -E ./3_setup_python_server.sh
```

**What it does**:
- ✅ Installs Python 3.9
- ✅ Installs Redis
- ✅ Installs MinIO
- ✅ Creates MinIO buckets
- ✅ Creates virtual environment
- ✅ Installs Python dependencies
- ✅ Creates systemd services
- ✅ Starts all services

**Verification**:
```bash
systemctl status minio
systemctl status redis-server
systemctl status mxa-mobile-api
systemctl status mxa-mobile-worker
curl http://localhost:8104/health
```

**Expected Output**: All services running

---

## Phase 2: Keycloak Configuration

**Estimated Time**: 10 minutes

```bash
# From any server with network access
cd mxa-v2/deploy/scripts

# Install jq (if needed)
sudo apt-get install -y jq

# Set admin password
export KEYCLOAK_ADMIN_PASSWORD="admin123"

# Run configuration
./configure_keycloak.sh
```

**What it does**:
- ✅ Creates realm: `forensics`
- ✅ Creates client: `mxa-mobile-web`
- ✅ Generates client secret
- ✅ Creates roles: user, analyst, admin
- ✅ Creates test user: admin

**Important Output**:
```
Client Secret: abc123def456...
```

**⚠️ COPY THIS SECRET! You'll need it in the next step.**

**Verification**:
- Access http://192.168.1.59:8080
- Login with admin/admin123
- Check realm "forensics" exists

---

## Phase 3: Configuration Update

**Estimated Time**: 5 minutes

### 3.1 Update PHP Configuration

```bash
# On application server (192.168.1.66)
sudo nano /var/www/mxa-mobile-app/current/php-app/.env

# Update these values:
DB_PASSWORD=YourSecurePassword123!
KEYCLOAK_CLIENT_ID=mxa-mobile-web
KEYCLOAK_CLIENT_SECRET=<paste-client-secret-here>
KEYCLOAK_SERVER_URL=http://192.168.1.59:8080
KEYCLOAK_REALM=forensics
PYTHON_API_URL=http://192.168.1.90:8104

# Save and exit
```

### 3.2 Update Python Configuration

```bash
# On Python server (192.168.1.90)
sudo nano /opt/apps/mxa-mobile/python-backend/.env

# Update these values:
DB_HOST=192.168.1.66
DB_PASSWORD=YourSecurePassword123!
MINIO_ENDPOINT=192.168.1.90:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=MinIOPassword123!
KEYCLOAK_SERVER_URL=http://192.168.1.59:8080
KEYCLOAK_REALM=forensics
KEYCLOAK_CLIENT_ID=mxa-mobile-web
KEYCLOAK_CLIENT_SECRET=<paste-client-secret-here>

# Save and exit
```

### 3.3 Restart Services

```bash
# On application server
sudo systemctl restart apache2

# On Python server
sudo systemctl restart mxa-mobile-api
sudo systemctl restart mxa-mobile-worker
```

---

## Phase 4: Database Import

**Estimated Time**: 5 minutes

```bash
# On application server (192.168.1.66)
cd mxa-v2/deploy/scripts

export DB_PASSWORD="YourSecurePassword123!"
./import_database.sh
```

**What it does**:
- ✅ Tests database connection
- ✅ Creates backup (if tables exist)
- ✅ Imports schema.sql
- ✅ Verifies all tables created

**Verification**:
```bash
psql -h localhost -U mxa_mobile_user -d mxa_mobile -c "\dt"
```

**Expected Output**: List of 10+ tables

---

## Phase 5: Testing & Verification

**Estimated Time**: 10 minutes

```bash
# From any server
cd mxa-v2/deploy/scripts

export DB_PASSWORD="YourSecurePassword123!"
./test_deployment.sh
```

**What it tests**:
- ✅ Keycloak accessibility
- ✅ Web application
- ✅ PostgreSQL
- ✅ FastAPI health
- ✅ MinIO
- ✅ Redis
- ✅ All systemd services
- ✅ Network connectivity
- ✅ Database schema

**Expected Output**:
```
Passed: 20
Failed: 0
✓ All tests passed!
```

---

## Phase 6: Manual Verification

### 6.1 Test Web Access

```bash
# From your browser
http://192.168.1.66
```

**Expected**: Login page

### 6.2 Test Login

- Username: `admin`
- Password: `admin123`

**Expected**: Dashboard page

### 6.3 Test API

```bash
curl http://192.168.1.90:8104/health
```

**Expected**: `{"status":"healthy"}`

### 6.4 Test MinIO

```bash
# From your browser
http://192.168.1.90:9001

# Login:
# Username: minioadmin
# Password: MinIOPassword123!
```

**Expected**: MinIO console with 4 buckets

---

## Post-Deployment Tasks

### Immediate (Required)

1. **Change Default Passwords**
```bash
# Keycloak admin password
# Test user password (admin/admin123)
# Database password (use stronger password)
# MinIO root password
```

2. **Update Environment Files**
```bash
# Set strong random secrets
# Update production URLs
# Configure email settings
```

3. **Set Up Backups**
```bash
# Add to crontab
0 2 * * * /path/to/backup.sh
```

### Short-term (Within 1 week)

4. **SSL/TLS Configuration**
```bash
# Install Let's Encrypt certificates
# Configure Apache for HTTPS
# Update all URLs to HTTPS
```

5. **Monitoring Setup**
```bash
# Set up log rotation
# Configure alerting
# Set up health check cron
```

6. **User Training**
```bash
# Create user accounts
# Assign roles
# Conduct training sessions
```

### Ongoing

7. **Regular Maintenance**
```bash
# Weekly backups
# Monthly updates
# Log review
# Performance monitoring
```

---

## Rollback Procedure

If something goes wrong:

```bash
# Stop services
sudo systemctl stop mxa-mobile-api
sudo systemctl stop mxa-mobile-worker
sudo systemctl stop apache2

# Run rollback
./rollback.sh /var/backups/mxa-mobile/mxa_mobile_backup_YYYYMMDD_HHMMSS.tar.gz

# Verify
./test_deployment.sh
```

---

## Success Criteria

✅ All three servers configured
✅ All services running
✅ Database schema imported
✅ All tests passing
✅ Web UI accessible
✅ Login working
✅ API responding
✅ No errors in logs

---

## Next Steps

1. Create additional user accounts
2. Configure organization-specific settings
3. Set up regular backups
4. Configure SSL certificates
5. Train end users
6. Monitor system health
7. Plan for scaling

---

**Deployment Complete!** 🎉

Your MxA Mobile system is now ready for use.
