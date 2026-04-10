#!/bin/bash
#
# MxA Mobile - SSO Server Setup (192.168.1.59)
# This script sets up the Keycloak SSO server
#
# Prerequisites:
# - Ubuntu 20.04+ or RHEL 8+
# - Java 11+ installed
# - Keycloak downloaded or Docker available
#

set -e

echo "=========================================="
echo "MxA Mobile - SSO Server Setup"
echo "Server: 192.168.1.59"
echo "=========================================="

# Configuration
KEYCLOAK_VERSION="23.0.0"
KEYCLOAK_DIR="/opt/keycloak"
KEYCLOAK_USER="keycloak"
KEYCLOAK_ADMIN="admin"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin123}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root or with sudo"
    exit 1
fi

echo "Step 1: Installing Java..."
if command -v java &> /dev/null; then
    echo "✓ Java already installed: $(java -version 2>&1 | head -n 1)"
else
    apt-get update
    apt-get install -y openjdk-11-jdk
    echo "✓ Java installed"
fi

echo ""
echo "Step 2: Creating Keycloak user..."
if id "$KEYCLOAK_USER" &>/dev/null; then
    echo "✓ User $KEYCLOAK_USER already exists"
else
    useradd -r -s /bin/false $KEYCLOAK_USER
    echo "✓ User $KEYCLOAK_USER created"
fi

echo ""
echo "Step 3: Downloading Keycloak..."
mkdir -p /opt
if [ -d "$KEYCLOAK_DIR" ]; then
    echo "✓ Keycloak directory already exists"
else
    cd /opt
    wget -q "https://github.com/keycloak/keycloak/releases/download/${KEYCLOAK_VERSION}/keycloak-${KEYCLOAK_VERSION}.tar.gz"
    tar -xzf "keycloak-${KEYCLOAK_VERSION}.tar.gz"
    mv "keycloak-${KEYCLOAK_VERSION}" keycloak
    rm "keycloak-${KEYCLOAK_VERSION}.tar.gz"
    chown -R $KEYCLOAK_USER:$KEYCLOAK_USER $KEYCLOAK_DIR
    echo "✓ Keycloak downloaded and extracted"
fi

echo ""
echo "Step 4: Creating Keycloak systemd service..."
cat > /etc/systemd/system/keycloak.service <<EOF
[Unit]
Description=Keycloak Identity and Access Management
After=network.target

[Service]
Type=simple
User=$KEYCLOAK_USER
Group=$KEYCLOAK_USER
WorkingDirectory=$KEYCLOAK_DIR
Environment="KEYCLOAK_ADMIN=$KEYCLOAK_ADMIN"
Environment="KEYCLOAK_ADMIN_PASSWORD=$KEYCLOAK_ADMIN_PASSWORD"
ExecStart=$KEYCLOAK_DIR/bin/kc.sh start-dev --http-port=8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Systemd service created"

echo ""
echo "Step 5: Starting Keycloak..."
systemctl daemon-reload
systemctl enable keycloak
systemctl start keycloak

echo "Waiting for Keycloak to start (60 seconds)..."
sleep 60

if systemctl is-active --quiet keycloak; then
    echo "✓ Keycloak is running"
else
    echo "✗ Keycloak failed to start"
    systemctl status keycloak
    exit 1
fi

echo ""
echo "Step 6: Verifying Keycloak..."
if curl -f http://localhost:8080/health 2>/dev/null; then
    echo "✓ Keycloak is accessible"
else
    echo "⚠ Keycloak may still be starting up"
fi

echo ""
echo "=========================================="
echo "SSO Server Setup Complete!"
echo "=========================================="
echo ""
echo "Keycloak Admin Console:"
echo "  URL: http://192.168.1.59:8080"
echo "  Username: $KEYCLOAK_ADMIN"
echo "  Password: $KEYCLOAK_ADMIN_PASSWORD"
echo ""
echo "Next Steps:"
echo "  1. Access the admin console and change the default password"
echo "  2. Run: ./configure_keycloak.sh"
echo ""
