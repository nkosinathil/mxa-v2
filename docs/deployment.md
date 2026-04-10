# MxA Mobile - Deployment Guide

## Prerequisites

### Server Requirements

**Application Server (192.168.1.66)**
- OS: Ubuntu 20.04+ or RHEL 8+
- RAM: 8GB minimum, 16GB recommended
- Disk: 100GB minimum
- Software:
  - Apache 2.4+
  - PHP 8.1+ with extensions: pdo_pgsql, mbstring, curl, json
  - PostgreSQL 13+
  - Composer

**Python Server (192.168.1.90)**
- OS: Ubuntu 20.04+ or RHEL 8+
- RAM: 16GB minimum, 32GB recommended (for transcription)
- Disk: 500GB minimum
- Software:
  - Python 3.9+
  - Redis 6.0+
  - MinIO latest
  - Tesseract OCR
  - Optional: CUDA for GPU-accelerated transcription

**SSO Server (192.168.1.59)**
- Keycloak instance (assumed already configured)

## Deployment Steps

### 1. Application Server Setup (192.168.1.66)

#### Install Dependencies
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y apache2 php8.1 php8.1-fpm php8.1-pgsql php8.1-mbstring \
    php8.1-curl php8.1-json postgresql-13 postgresql-client-13

# RHEL/CentOS
sudo yum install -y httpd php php-fpm php-pgsql php-mbstring php-json postgresql13
```

#### Configure PostgreSQL
```bash
sudo -u postgres psql

CREATE DATABASE mxa_mobile;
CREATE USER mxa_mobile_user WITH ENCRYPTED PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE mxa_mobile TO mxa_mobile_user;
\q

# Import schema
psql -U postgres -d mxa_mobile -f database/schema.sql
```

#### Deploy PHP Application
```bash
# Create application directory
sudo mkdir -p /var/www/mxa-mobile-app/current
sudo chown -R www-data:www-data /var/www/mxa-mobile-app

# Copy files
cd /var/www/mxa-mobile-app/current
git clone <repository-url> .
cd php-app

# Install dependencies
composer install --no-dev --optimize-autoloader

# Configure environment
cp .env.example .env
nano .env  # Edit with actual configuration

# Set permissions
sudo chown -R www-data:www-data /var/www/mxa-mobile-app
sudo chmod -R 755 /var/www/mxa-mobile-app
sudo chmod -R 775 storage/logs
```

#### Configure Apache
```bash
# Copy vhost configuration
sudo cp deploy/apache/mxa-mobile.conf /etc/apache2/sites-available/

# Enable site and modules
sudo a2ensite mxa-mobile
sudo a2enmod rewrite
sudo systemctl restart apache2
```

### 2. Python Server Setup (192.168.1.90)

#### Install Dependencies
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.9 python3.9-venv python3-pip redis-server \
    tesseract-ocr tesseract-ocr-eng

# RHEL/CentOS
sudo yum install -y python39 python39-pip redis tesseract

# Install MinIO
wget https://dl.min.io/server/minio/release/linux-amd64/minio
sudo mv minio /usr/local/bin/
sudo chmod +x /usr/local/bin/minio
```

#### Deploy Python Application
```bash
# Create application directory
sudo mkdir -p /opt/apps/mxa-mobile
sudo chown -R $USER:$USER /opt/apps/mxa-mobile

cd /opt/apps/mxa-mobile
git clone <repository-url> .
cd python-backend

# Create virtual environment
python3.9 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Edit with actual configuration

# Create necessary directories
mkdir -p logs
```

#### Configure MinIO
```bash
# Create MinIO user
sudo useradd -r -s /sbin/nologin minio

# Create data directory
sudo mkdir -p /mnt/minio/data
sudo chown -R minio:minio /mnt/minio

# Create systemd service
sudo nano /etc/systemd/system/minio.service
```

```ini
[Unit]
Description=MinIO
Documentation=https://docs.min.io
Wants=network-online.target
After=network-online.target

[Service]
User=minio
Group=minio
WorkingDirectory=/mnt/minio

ExecStart=/usr/local/bin/minio server /mnt/minio/data \
    --address :9000 \
    --console-address :9001

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Start MinIO
sudo systemctl daemon-reload
sudo systemctl enable minio
sudo systemctl start minio

# Create buckets
mc alias set mxa http://localhost:9000 <access-key> <secret-key>
mc mb mxa/mxa-mobile-input
mc mb mxa/mxa-mobile-output
mc mb mxa/mxa-mobile-temp
```

#### Configure FastAPI Service
```bash
sudo cp deploy/systemd/mxa-mobile-api.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable mxa-mobile-api
sudo systemctl start mxa-mobile-api
```

#### Configure Celery Worker Service
```bash
sudo cp deploy/systemd/mxa-mobile-worker.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable mxa-mobile-worker
sudo systemctl start mxa-mobile-worker
```

### 3. Keycloak Configuration (192.168.1.59)

#### Create Realm (if not exists)
1. Login to Keycloak admin console
2. Create realm: `forensics`

#### Create Client
1. Navigate to Clients → Create
2. Client ID: `mxa-mobile-web`
3. Client Protocol: `openid-connect`
4. Access Type: `confidential`
5. Valid Redirect URIs: `http://192.168.1.66/auth/callback`
6. Web Origins: `http://192.168.1.66`

#### Create Roles
1. Navigate to Roles → Add Role
2. Create roles: `user`, `analyst`, `admin`

#### Create Users
1. Navigate to Users → Add User
2. Assign roles via Role Mappings

#### Get Client Secret
1. Clients → mxa-mobile-web → Credentials
2. Copy secret to PHP and Python .env files

## Post-Deployment Configuration

### Test Connectivity
```bash
# Test PHP to Python API
curl http://192.168.1.90:8104/health

# Test PHP to PostgreSQL
psql -h 192.168.1.66 -U mxa_mobile_user -d mxa_mobile -c "SELECT 1;"

# Test Python to MinIO
mc ls mxa/

# Test Redis
redis-cli ping
```

### Initialize Application Data
```bash
# Create initial admin user in Keycloak
# Log in to application
# Verify user record created in PostgreSQL
```

### Verify Services
```bash
# Check Apache
sudo systemctl status apache2

# Check PostgreSQL
sudo systemctl status postgresql

# Check FastAPI
sudo systemctl status mxa-mobile-api

# Check Celery
sudo systemctl status mxa-mobile-worker

# Check Redis
sudo systemctl status redis

# Check MinIO
sudo systemctl status minio
```

## Security Hardening

### PostgreSQL
```sql
-- Restrict network access
# Edit postgresql.conf
listen_addresses = 'localhost,192.168.1.66'

# Edit pg_hba.conf
host    mxa_mobile    mxa_mobile_user    192.168.1.66/32    md5
host    mxa_mobile    mxa_mobile_user    192.168.1.90/32    md5
```

### Firewall Rules
```bash
# Application Server
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow from 192.168.1.90 to any port 5432

# Python Server
sudo ufw allow from 192.168.1.66 to any port 8104
sudo ufw allow from 192.168.1.66 to any port 9000
```

### File Permissions
```bash
# PHP application
sudo chown -R www-data:www-data /var/www/mxa-mobile-app
sudo chmod -R 755 /var/www/mxa-mobile-app
sudo chmod -R 775 /var/www/mxa-mobile-app/current/storage

# Python application
sudo chown -R celery:celery /opt/apps/mxa-mobile
sudo chmod -R 750 /opt/apps/mxa-mobile
```

## Maintenance

### Backups

**Database Backup**
```bash
# Daily backup script
pg_dump -U mxa_mobile_user mxa_mobile | gzip > backup_$(date +%Y%m%d).sql.gz
```

**MinIO Backup**
```bash
mc mirror mxa/mxa-mobile-output /backups/minio/
```

### Log Rotation
```bash
# Configure logrotate for application logs
sudo nano /etc/logrotate.d/mxa-mobile
```

### Updates
```bash
# PHP application
cd /var/www/mxa-mobile-app/current/php-app
git pull
composer install --no-dev
sudo systemctl reload apache2

# Python application
cd /opt/apps/mxa-mobile/python-backend
source venv/bin/activate
git pull
pip install -r requirements.txt
sudo systemctl restart mxa-mobile-api
sudo systemctl restart mxa-mobile-worker
```

## Troubleshooting

See [troubleshooting.md](troubleshooting.md) for common issues and solutions.

## Rollback Procedure

```bash
# PHP application
cd /var/www/mxa-mobile-app/current
git checkout <previous-commit>
composer install --no-dev
sudo systemctl reload apache2

# Python application
cd /opt/apps/mxa-mobile
git checkout <previous-commit>
cd python-backend
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart mxa-mobile-api
sudo systemctl restart mxa-mobile-worker
```

## Monitoring

- Monitor service status with systemd
- Monitor logs in real-time: `tail -f /var/log/...`
- Monitor disk usage: `df -h`
- Monitor PostgreSQL: `pg_stat_activity`
- Monitor Redis: `redis-cli info`
- Monitor MinIO: Web console at port 9001
