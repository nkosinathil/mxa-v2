# MxA Mobile - Quick Deployment Guide

## 🚀 One-Command Deployment (Non-Interactive)

```bash
cd /home/runner/work/mxa-v2/mxa-v2/deploy/scripts
chmod +x *.sh
./deploy_all.sh \
  --db-password "SecurePassword123!" \
  --minio-root-password "MinIOPassword123!" \
  --keycloak-admin-password "StrongAdminPassword123!"
```

The script runs unattended over SSH.

---

## 📋 Pre-Deployment Checklist

- [ ] Three servers available (Ubuntu 20.04+)
- [ ] Root/sudo access on all servers
- [ ] Network connectivity between servers
- [ ] Passwords prepared:
  - [ ] Database password
  - [ ] MinIO password
  - [ ] Keycloak admin password

---

## 🖥️ Server Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     MxA Mobile System                        │
└─────────────────────────────────────────────────────────────┘

┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│  SSO Server      │         │  App Server      │         │  Python Server   │
│  192.168.1.59    │◄───────►│  192.168.1.66    │◄───────►│  192.168.1.90    │
└──────────────────┘         └──────────────────┘         └──────────────────┘
│                            │                            │
│ • Keycloak               │ • Apache 2.4              │ • FastAPI (8104)
│   :8080                   │ • PHP 8.1                 │ • Celery Workers
│                            │ • PostgreSQL :5432       │ • MinIO :9000
│                            │ • MxA Web UI             │ • Redis :6379
│                            │                            │
└─────────────────────────────────────────────────────────────┘

User → PHP (66) → FastAPI (90) → Celery → Processing
                      ↓              ↓
                 PostgreSQL (66)  MinIO (90)
```

---

## ⚡ Quick Start Commands

### On SSO Server (192.168.1.59)
```bash
sudo ./1_setup_sso_server.sh
```

### On Application Server (192.168.1.66)
```bash
export DB_PASSWORD="SecurePassword123!"
sudo -E ./2_setup_app_server.sh
```

### On Python Server (192.168.1.90)
```bash
export DB_PASSWORD="SecurePassword123!"
export MINIO_ROOT_PASSWORD="MinIOPassword123!"
sudo -E ./3_setup_python_server.sh
```

### Configure Keycloak (from any server)
```bash
export KEYCLOAK_ADMIN_PASSWORD="admin123"
./configure_keycloak.sh
```
**IMPORTANT**: Copy the client secret shown at the end!

### Import Database (on app server)
```bash
export DB_PASSWORD="SecurePassword123!"
./import_database.sh
```

### Update Configuration Files

**PHP (.env)**: `/var/www/mxa-mobile-app/current/php-app/.env`
```bash
DB_PASSWORD=SecurePassword123!
KEYCLOAK_CLIENT_SECRET=<paste-from-keycloak-setup>
```

**Python (.env)**: `/opt/apps/mxa-mobile/python-backend/.env`
```bash
DB_PASSWORD=SecurePassword123!
MINIO_SECRET_KEY=MinIOPassword123!
KEYCLOAK_CLIENT_SECRET=<paste-from-keycloak-setup>
```

### Test Everything
```bash
export DB_PASSWORD="SecurePassword123!"
./test_deployment.sh
```

---

## 🔧 Daily Operations

### Check System Health
```bash
./health_check.sh
```

### Create Backup
```bash
export DB_PASSWORD="SecurePassword123!"
./backup.sh
```

### Deploy Updates
```bash
sudo ./deploy.sh
```

### Rollback to Previous Version
```bash
./rollback.sh /var/backups/mxa-mobile/mxa_mobile_backup_YYYYMMDD_HHMMSS.tar.gz
```

---

## 🌐 Access URLs

After successful deployment:

- **Web Application**: http://192.168.1.66
- **API Documentation**: http://192.168.1.90:8104/docs
- **Keycloak Admin**: http://192.168.1.59:8080
- **MinIO Console**: http://192.168.1.90:9001

**Default Credentials**:
- Username: `admin`
- Password: `admin123`

⚠️ **CHANGE THESE IMMEDIATELY IN PRODUCTION!**

---

## 🐛 Troubleshooting

### Service Not Starting
```bash
# Check status
systemctl status mxa-mobile-api

# View logs
journalctl -u mxa-mobile-api -n 50 --no-pager

# Restart
systemctl restart mxa-mobile-api
```

### Database Connection Failed
```bash
# Test connection
psql -h 192.168.1.66 -U mxa_mobile_user -d mxa_mobile

# Check PostgreSQL
systemctl status postgresql
```

### Keycloak Not Accessible
```bash
# Check Keycloak
systemctl status keycloak

# Test endpoint
curl http://192.168.1.59:8080/health
```

### Network Issues
```bash
# Test connectivity
ping 192.168.1.59
ping 192.168.1.66
ping 192.168.1.90

# Check firewall
sudo ufw status
```

---

## 📞 Support

1. Check `/docs/troubleshooting.md`
2. Review service logs: `journalctl -u <service-name>`
3. Run health check: `./health_check.sh`
4. Contact development team

---

## ✅ Post-Deployment Tasks

- [ ] Change all default passwords
- [ ] Set up SSL/TLS certificates
- [ ] Configure automated backups (cron)
- [ ] Set up monitoring/alerting
- [ ] Document custom configurations
- [ ] Train users
- [ ] Create runbook for common issues
- [ ] Schedule regular updates

---

**Version**: MxA Mobile v2.0  
**Last Updated**: 2026-04-10
