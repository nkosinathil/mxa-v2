#!/bin/bash
#
# MxA Mobile - Application Server Setup (192.168.1.66)
# This script sets up Apache, PHP, and PostgreSQL
#
# Prerequisites:
# - Ubuntu 20.04+ or RHEL 8+
# - Internet connection for package installation
#

set -e

echo "=========================================="
echo "MxA Mobile - Application Server Setup"
echo "Server: 192.168.1.66"
echo "=========================================="

# Configuration
APP_DIR="/var/www/mxa-mobile-app"
DB_NAME="mxa_mobile"
DB_USER="mxa_mobile_user"
DB_PASSWORD="${DB_PASSWORD:-}"
DB_PASSWORD_SQL_ESCAPED="${DB_PASSWORD//\'/\'\'}"
REPO_URL="${REPO_URL:-https://github.com/nkosinathil/mxa-v2.git}"
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

export DEBIAN_FRONTEND=noninteractive

echo ""
echo "Step 1: Installing Apache and PHP..."
apt-get update
apt-get install -y apache2 php8.1 php8.1-fpm php8.1-cli php8.1-common \
    php8.1-pgsql php8.1-mbstring php8.1-curl php8.1-xml \
    libapache2-mod-php8.1 composer git

echo "✓ Apache and PHP installed"

echo ""
echo "Step 2: Installing PostgreSQL..."
apt-get install -y postgresql postgresql-contrib postgresql-client

echo "✓ PostgreSQL installed"

echo ""
echo "Step 3: Configuring PostgreSQL..."
systemctl start postgresql
systemctl enable postgresql

# Wait for PostgreSQL to be ready
sleep 5

# Create database and user
sudo -u postgres psql <<EOF
-- Create or update user
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB_USER') THEN
        CREATE ROLE $DB_USER LOGIN ENCRYPTED PASSWORD '$DB_PASSWORD_SQL_ESCAPED';
    ELSE
        ALTER ROLE $DB_USER WITH LOGIN ENCRYPTED PASSWORD '$DB_PASSWORD_SQL_ESCAPED';
    END IF;
END
\$\$;

-- Create database if needed
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

-- Connect to database and grant schema privileges
\c $DB_NAME
GRANT ALL ON SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;

\q
EOF

echo "✓ PostgreSQL configured"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"

echo ""
echo "Step 4: Creating application directory..."
mkdir -p $APP_DIR
chown -R www-data:www-data $APP_DIR

echo "✓ Application directory created: $APP_DIR"

echo ""
echo "Step 5: Cloning repository..."
cd $APP_DIR
if [ ! -d "current" ]; then
    sudo -u www-data git clone "$REPO_URL" current
    sudo -u www-data git -C current checkout "$DEPLOY_REF"
    if sudo -u www-data git -C current rev-parse --verify --quiet "origin/$DEPLOY_REF" >/dev/null; then
        sudo -u www-data git -C current reset --hard "origin/$DEPLOY_REF"
    fi
    echo "✓ Repository cloned"
else
    sudo -u www-data git -C current fetch --all --tags
    sudo -u www-data git -C current checkout "$DEPLOY_REF"
    if sudo -u www-data git -C current rev-parse --verify --quiet "origin/$DEPLOY_REF" >/dev/null; then
        sudo -u www-data git -C current reset --hard "origin/$DEPLOY_REF"
    fi
    echo "✓ Repository updated"
fi

echo ""
echo "Step 6: Installing PHP dependencies..."
cd $APP_DIR/current/php-app
sudo -u www-data composer install --no-dev --optimize-autoloader

echo "✓ PHP dependencies installed"

echo ""
echo "Step 7: Creating .env file..."
if [ ! -f "$APP_DIR/current/php-app/.env" ]; then
    cp "$APP_DIR/current/php-app/.env.example" "$APP_DIR/current/php-app/.env"
    
    # Update database credentials
    sed -i "s/DB_PASSWORD=.*/DB_PASSWORD=$DB_PASSWORD/" "$APP_DIR/current/php-app/.env"
    sed -i "s/DB_NAME=.*/DB_NAME=$DB_NAME/" "$APP_DIR/current/php-app/.env"
    sed -i "s/DB_USER=.*/DB_USER=$DB_USER/" "$APP_DIR/current/php-app/.env"
    
    chown www-data:www-data "$APP_DIR/current/php-app/.env"
    chmod 600 "$APP_DIR/current/php-app/.env"
    
    echo "✓ .env file created (IMPORTANT: Update Keycloak credentials manually!)"
else
    echo "✓ .env file already exists"
fi

echo ""
echo "Step 8: Setting permissions..."
chown -R www-data:www-data $APP_DIR
chmod -R 755 $APP_DIR
mkdir -p $APP_DIR/current/php-app/storage/logs
chmod -R 775 $APP_DIR/current/php-app/storage

echo "✓ Permissions set"

echo ""
echo "Step 9: Configuring Apache..."
# Copy Apache configuration
cp "$APP_DIR/current/deploy/apache/mxa-mobile.conf" /etc/apache2/sites-available/

# Enable required modules
a2enmod rewrite
a2enmod headers
a2enmod proxy_fcgi
a2enmod setenvif
a2enconf php8.1-fpm

# Enable site
a2ensite mxa-mobile.conf
a2dissite 000-default.conf

# Test configuration
apache2ctl configtest

# Restart Apache
systemctl restart apache2
systemctl enable apache2

echo "✓ Apache configured and restarted"

echo ""
echo "Step 10: Configuring firewall..."
if command -v ufw &>/dev/null; then
    ufw allow 'Apache Full'
    ufw allow from 192.168.1.90 to any port 5432
else
    echo "⚠ ufw not installed, skipping firewall rules"
fi

echo "✓ Firewall configured"

echo ""
echo "=========================================="
echo "Application Server Setup Complete!"
echo "=========================================="
echo ""
echo "Database Information:"
echo "  Host: 192.168.1.66"
echo "  Port: 5432"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo "  Password: $DB_PASSWORD"
echo ""
echo "Web Application:"
echo "  URL: http://192.168.1.66"
echo "  Document Root: $APP_DIR/current/php-app/public"
echo ""
echo "IMPORTANT NEXT STEPS:"
echo "  1. Edit $APP_DIR/current/php-app/.env"
echo "  2. Update Keycloak credentials (KEYCLOAK_CLIENT_SECRET)"
echo "  3. Run: ./import_database.sh"
echo "  4. Verify: curl http://192.168.1.66"
echo ""
