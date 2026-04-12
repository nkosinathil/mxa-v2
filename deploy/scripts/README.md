# MxA Mobile Deployment Scripts

This directory contains all scripts needed to deploy and manage the MxA Mobile application across three servers.

## Quick Start

### Prerequisites

- Three Ubuntu 20.04+ servers:
  - **SSO Server**: 192.168.1.59 (Keycloak)
  - **Application Server**: 192.168.1.66 (Apache, PHP, PostgreSQL)
  - **Python Server**: 192.168.1.90 (FastAPI, Celery, MinIO, Redis)
- Root/sudo access on all servers
- Network connectivity between servers

### Complete Deployment (Guided)

Run the master deployment script on any server with access to all three:

```bash
cd deploy/scripts
chmod +x *.sh
./deploy_all.sh
```

This script will guide you through:
1. Setting up all three servers
2. Configuring Keycloak
3. Importing the database schema
4. Deploying the application on app and python servers
5. Running tests

### Manual Step-by-Step Deployment

#### Step 1: Set up servers

On **SSO Server (192.168.1.59)**:
```bash
export KEYCLOAK_ADMIN_PASSWORD="StrongAdminPassword"
sudo -E ./1_setup_sso_server.sh
```

On **Application Server (192.168.1.66)**:
```bash
export DB_PASSWORD="YourSecurePassword"
export DEPLOY_REF="main"  # or release tag/branch
sudo -E ./2_setup_app_server.sh
```

On **Python Server (192.168.1.90)**:
```bash
export DB_PASSWORD="YourSecurePassword"
export MINIO_ROOT_USER="minioadmin"
export MINIO_ROOT_PASSWORD="YourMinIOPassword"
export DEPLOY_REF="main"  # or release tag/branch
sudo -E ./3_setup_python_server.sh
```

#### Step 2: Configure Keycloak

From any server with network access:
```bash
export KEYCLOAK_ADMIN_PASSWORD="admin123"
./configure_keycloak.sh
```

**Important**: Save the client secret displayed at the end!

#### Step 3: Update configuration files

On **Application Server**:
```bash
sudo nano /var/www/mxa-mobile-app/current/php-app/.env
# Update:
# - DB_PASSWORD
# - KEYCLOAK_CLIENT_SECRET
```

On **Python Server**:
```bash
sudo nano /opt/apps/mxa-mobile/python-backend/.env
# Update:
# - DB_PASSWORD
# - MINIO_SECRET_KEY
# - KEYCLOAK_CLIENT_SECRET
```

#### Step 4: Import database schema

On **Application Server**:
```bash
export DB_PASSWORD="YourSecurePassword"
./import_database.sh
```

#### Step 5: Deploy application

On **Application Server**:
```bash
sudo ./deploy.sh --target app --ref main
```

On **Python Server**:
```bash
sudo ./deploy.sh --target python --ref main
```

#### Step 6: Test deployment

From any server:
```bash
export DB_PASSWORD="YourSecurePassword"
./test_deployment.sh
```

## Script Reference

### Setup Scripts

| Script | Purpose | Server | Prerequisites |
|--------|---------|--------|---------------|
| `1_setup_sso_server.sh` | Install and configure Keycloak | 192.168.1.59 | Java 11+ |
| `2_setup_app_server.sh` | Install Apache, PHP, PostgreSQL | 192.168.1.66 | Ubuntu 20.04+ |
| `3_setup_python_server.sh` | Install Python, FastAPI, Celery, MinIO, Redis | 192.168.1.90 | Ubuntu 20.04+ |

### Configuration Scripts

| Script | Purpose | Required Environment Variables |
|--------|---------|-------------------------------|
| `configure_keycloak.sh` | Set up Keycloak realm, client, roles | `KEYCLOAK_ADMIN_PASSWORD` |
| `import_database.sh` | Import PostgreSQL schema | `DB_PASSWORD` |

### Deployment Scripts

| Script | Purpose | Notes |
|--------|---------|-------|
| `deploy_all.sh` | Master deployment orchestration | Interactive guided workflow across hosts |
| `deploy.sh` | Deploy/update application code | Run with explicit target (`app` or `python`) |

### Utility Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `test_deployment.sh` | End-to-end testing | Verifies all components |
| `backup.sh` | Create backup | `./backup.sh [destination]` |
| `rollback.sh` | Rollback to backup | `./rollback.sh <backup_file.tar.gz>` |
| `health_check.sh` | System health monitoring | Run periodically or via cron |

## Environment Variables

### Required for setup:

```bash
# Database (set on Application and Python servers)
export DB_PASSWORD="YourSecurePassword"

# MinIO (set on Python server)
export MINIO_ROOT_USER="minioadmin"
export MINIO_ROOT_PASSWORD="YourMinIOPassword"

# Keycloak (set when running configure_keycloak.sh)
export KEYCLOAK_ADMIN_PASSWORD="admin123"

# Repository (optional)
export REPO_URL="https://github.com/nkosinathil/mxa-v2.git"
```

## Post-Deployment Checklist

- [ ] Change default Keycloak admin password
- [ ] Change default test user password
- [ ] Update all `.env` files with production values
- [ ] Set up SSL/TLS certificates
- [ ] Configure firewall rules
- [ ] Set up backup cron jobs
- [ ] Set up monitoring/alerting
- [ ] Test end-to-end workflow
- [ ] Document custom configurations
- [ ] Train users on the system

## Maintenance

### Daily Health Check

```bash
./health_check.sh
```

### Weekly Backup

```bash
export DB_PASSWORD="YourPassword"
./backup.sh
```

### Update Application

```bash
# On app server
sudo ./deploy.sh --target app --ref main

# On python server
sudo ./deploy.sh --target python --ref main
```

### Rollback

```bash
./rollback.sh /var/backups/mxa-mobile/mxa_mobile_backup_YYYYMMDD_HHMMSS.tar.gz
```

## Troubleshooting

### Services not starting

Check service status:
```bash
systemctl status mxa-mobile-api
systemctl status mxa-mobile-worker
journalctl -u mxa-mobile-api -n 50
```

### Database connection issues

Test connection:
```bash
psql -h 192.168.1.66 -U mxa_mobile_user -d mxa_mobile
```

### Keycloak authentication issues

Verify Keycloak is accessible:
```bash
curl http://192.168.1.59:8080/health
```

Check client secret matches in both `.env` files.

### Network connectivity issues

Test connectivity:
```bash
ping 192.168.1.59
ping 192.168.1.66
ping 192.168.1.90
```

Check firewall rules:
```bash
sudo ufw status
```

## Security Notes

1. **Change all default passwords** immediately after deployment
2. **Use strong passwords** for database and MinIO
3. **Enable firewall** on all servers
4. **Restrict network access** between servers
5. **Enable SSL/TLS** for production
6. **Regular backups** are essential
7. **Keep systems updated**: `apt update && apt upgrade`
8. **Monitor logs** for suspicious activity

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review service logs
3. Consult the main documentation in `/docs`
4. Contact the development team

## Version

These scripts are for MxA Mobile v2.0.
Last updated: 2026-04-10
