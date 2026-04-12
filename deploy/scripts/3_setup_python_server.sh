#!/bin/bash
#
# MxA Mobile - Python Server Setup (192.168.1.90)
# This script sets up Python, FastAPI, Celery, MinIO, and Redis
#
# Prerequisites:
# - Ubuntu 20.04+ or RHEL 8+
# - Internet connection for package installation
#

set -e

echo "=========================================="
echo "MxA Mobile - Python Server Setup"
echo "Server: 192.168.1.90"
echo "=========================================="

# Configuration
PYTHON_DIR="/opt/apps/mxa-mobile"
REPO_URL="${REPO_URL:-https://github.com/nkosinathil/mxa-v2.git}"
MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-}"
DB_HOST="192.168.1.66"
DB_NAME="mxa_mobile"
DB_USER="mxa_mobile_user"
DB_PASSWORD="${DB_PASSWORD:-}"
DEPLOY_REF="${DEPLOY_REF:-main}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root or with sudo"
    exit 1
fi

if [ -z "$DB_PASSWORD" ]; then
    echo "DB_PASSWORD must be set (export DB_PASSWORD=...)"
    exit 1
fi

if [ -z "$MINIO_ROOT_PASSWORD" ]; then
    echo "MINIO_ROOT_PASSWORD must be set (export MINIO_ROOT_PASSWORD=...)"
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive

echo ""
echo "Step 1: Installing Python and dependencies..."
apt-get update
apt-get install -y python3.9 python3.9-venv python3-pip redis-server \
    tesseract-ocr tesseract-ocr-eng wget curl

echo "✓ Python and base dependencies installed"

echo ""
echo "Step 2: Installing MinIO..."
if [ ! -f /usr/local/bin/minio ]; then
    wget -q https://dl.min.io/server/minio/release/linux-amd64/minio
    chmod +x minio
    mv minio /usr/local/bin/
    echo "✓ MinIO installed"
else
    echo "✓ MinIO already installed"
fi

# Install MinIO Client (mc)
if [ ! -f /usr/local/bin/mc ]; then
    wget -q https://dl.min.io/client/mc/release/linux-amd64/mc
    chmod +x mc
    mv mc /usr/local/bin/
    echo "✓ MinIO Client installed"
else
    echo "✓ MinIO Client already installed"
fi

echo ""
echo "Step 3: Creating users and directories..."

# Create MinIO user
if ! id "minio" &>/dev/null; then
    useradd -r -s /bin/false minio
    echo "✓ MinIO user created"
fi

# Create Celery user
if ! id "celery" &>/dev/null; then
    useradd -r -s /bin/bash celery
    echo "✓ Celery user created"
fi

# Create MinIO data directory
mkdir -p /mnt/minio/data
chown -R minio:minio /mnt/minio
echo "✓ MinIO data directory created"

# Create application directory
mkdir -p $PYTHON_DIR
chown -R celery:celery $PYTHON_DIR

# The FastAPI service runs as www-data (per systemd unit); add www-data to celery group
# so it can read the application files owned by celery
usermod -aG celery www-data
echo "✓ Application directory created: $PYTHON_DIR"

echo ""
echo "Step 4: Setting up MinIO systemd service..."
cat > /etc/systemd/system/minio.service <<EOF
[Unit]
Description=MinIO Object Storage
Documentation=https://docs.min.io
After=network.target

[Service]
Type=notify
User=minio
Group=minio
WorkingDirectory=/mnt/minio
Environment="MINIO_ROOT_USER=$MINIO_ROOT_USER"
Environment="MINIO_ROOT_PASSWORD=$MINIO_ROOT_PASSWORD"
ExecStart=/usr/local/bin/minio server /mnt/minio/data --address :9000 --console-address :9001
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable minio
systemctl start minio

echo "Waiting for MinIO to start..."
sleep 10

if systemctl is-active --quiet minio; then
    echo "✓ MinIO is running"
else
    echo "✗ MinIO failed to start"
    exit 1
fi

echo ""
echo "Step 5: Configuring MinIO buckets..."
# Configure mc alias
mc alias set mxa http://localhost:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD

# Create buckets
mc mb mxa/mxa-mobile-input --ignore-existing
mc mb mxa/mxa-mobile-output --ignore-existing
mc mb mxa/mxa-mobile-temp --ignore-existing
mc mb mxa/mxa-mobile-previews --ignore-existing

echo "✓ MinIO buckets created"

echo ""
echo "Step 6: Cloning repository..."
cd $PYTHON_DIR
if [ ! -d ".git" ]; then
    if [ -z "$(ls -A "$PYTHON_DIR")" ]; then
        sudo -u celery git clone "$REPO_URL" .
    else
        sudo -u celery git init .
        if ! sudo -u celery git remote get-url origin >/dev/null 2>&1; then
            sudo -u celery git remote add origin "$REPO_URL"
        else
            sudo -u celery git remote set-url origin "$REPO_URL"
        fi
        sudo -u celery git fetch --all --tags
        sudo -u celery git checkout "$DEPLOY_REF"
        if sudo -u celery git rev-parse --verify --quiet "origin/$DEPLOY_REF" >/dev/null; then
            sudo -u celery git reset --hard "origin/$DEPLOY_REF"
        fi
    fi
    sudo -u celery git checkout "$DEPLOY_REF"
    echo "✓ Repository cloned"
else
    sudo -u celery git fetch --all --tags
    sudo -u celery git checkout "$DEPLOY_REF"
    if sudo -u celery git rev-parse --verify --quiet "origin/$DEPLOY_REF" >/dev/null; then
        sudo -u celery git reset --hard "origin/$DEPLOY_REF"
    fi
    echo "✓ Repository already exists"
fi

echo ""
echo "Step 7: Setting up Python virtual environment..."
cd $PYTHON_DIR/python-backend
mkdir -p "$PYTHON_DIR/logs"
if [ ! -d "venv" ]; then
    sudo -u celery python3.9 -m venv venv
    echo "✓ Virtual environment created"
fi

# Install Python dependencies
sudo -u celery bash -c "source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"
echo "✓ Python dependencies installed"

echo ""
echo "Step 8: Creating .env file..."
if [ ! -f "$PYTHON_DIR/python-backend/.env" ]; then
    cp "$PYTHON_DIR/python-backend/.env.example" "$PYTHON_DIR/python-backend/.env"
    
    # Update configuration
    sed -i "s/DB_HOST=.*/DB_HOST=$DB_HOST/" "$PYTHON_DIR/python-backend/.env"
    sed -i "s/DB_PASSWORD=.*/DB_PASSWORD=$DB_PASSWORD/" "$PYTHON_DIR/python-backend/.env"
    sed -i "s/DB_NAME=.*/DB_NAME=$DB_NAME/" "$PYTHON_DIR/python-backend/.env"
    sed -i "s/DB_USER=.*/DB_USER=$DB_USER/" "$PYTHON_DIR/python-backend/.env"
    sed -i "s/MINIO_ACCESS_KEY=.*/MINIO_ACCESS_KEY=$MINIO_ROOT_USER/" "$PYTHON_DIR/python-backend/.env"
    sed -i "s/MINIO_SECRET_KEY=.*/MINIO_SECRET_KEY=$MINIO_ROOT_PASSWORD/" "$PYTHON_DIR/python-backend/.env"
    
    chown celery:celery "$PYTHON_DIR/python-backend/.env"
    chmod 600 "$PYTHON_DIR/python-backend/.env"
    
    echo "✓ .env file created"
else
    echo "✓ .env file already exists"
fi

echo ""
echo "Step 9: Installing systemd services..."
cp "$PYTHON_DIR/deploy/systemd/mxa-mobile-api.service" /etc/systemd/system/
cp "$PYTHON_DIR/deploy/systemd/mxa-mobile-worker.service" /etc/systemd/system/

# Create PID directory for Celery
mkdir -p /var/run/celery
chown celery:celery /var/run/celery

systemctl daemon-reload

echo "✓ Systemd services installed"

echo ""
echo "Step 10: Starting services..."
# Start Redis
systemctl enable redis-server
systemctl start redis-server

# Start FastAPI
systemctl enable mxa-mobile-api
systemctl start mxa-mobile-api

# Start Celery Worker
systemctl enable mxa-mobile-worker
systemctl start mxa-mobile-worker

echo "Waiting for services to start..."
sleep 10

# Verify services
if systemctl is-active --quiet mxa-mobile-api; then
    echo "✓ FastAPI service is running"
else
    echo "✗ FastAPI service failed to start"
fi

if systemctl is-active --quiet mxa-mobile-worker; then
    echo "✓ Celery worker is running"
else
    echo "✗ Celery worker failed to start"
fi

if systemctl is-active --quiet redis-server; then
    echo "✓ Redis is running"
else
    echo "✗ Redis failed to start"
fi

echo ""
echo "Step 11: Configuring firewall..."
if command -v ufw &>/dev/null; then
    ufw allow from 192.168.1.66 to any port 8104
    ufw allow from 192.168.1.66 to any port 9000
else
    echo "⚠ ufw not installed, skipping firewall rules"
fi

echo "✓ Firewall configured"

echo ""
echo "Step 12: Running health check..."
if curl -f http://localhost:8104/health 2>/dev/null; then
    echo "✓ FastAPI health check passed"
else
    echo "⚠ FastAPI health check failed (may still be starting)"
fi

echo ""
echo "=========================================="
echo "Python Server Setup Complete!"
echo "=========================================="
echo ""
echo "MinIO Information:"
echo "  Endpoint: http://192.168.1.90:9000"
echo "  Console: http://192.168.1.90:9001"
echo "  Access Key: $MINIO_ROOT_USER"
echo "  Secret Key: $MINIO_ROOT_PASSWORD"
echo "  Buckets: mxa-mobile-input, mxa-mobile-output, mxa-mobile-temp, mxa-mobile-previews"
echo ""
echo "FastAPI:"
echo "  URL: http://192.168.1.90:8104"
echo "  Health: http://192.168.1.90:8104/health"
echo ""
echo "Services:"
echo "  - minio (MinIO Object Storage)"
echo "  - redis-server (Message Broker)"
echo "  - mxa-mobile-api (FastAPI)"
echo "  - mxa-mobile-worker (Celery)"
echo ""
echo "Check status: systemctl status minio redis-server mxa-mobile-api mxa-mobile-worker"
echo ""
