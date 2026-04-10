#!/bin/bash
#
# MxA Mobile - Master Deployment Script
# Orchestrates the complete deployment across all servers
#
# Usage:
#   ./deploy_all.sh [--skip-setup] [--skip-keycloak] [--skip-db]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse arguments
SKIP_SETUP=false
SKIP_KEYCLOAK=false
SKIP_DB=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-setup)
            SKIP_SETUP=true
            shift
            ;;
        --skip-keycloak)
            SKIP_KEYCLOAK=true
            shift
            ;;
        --skip-db)
            SKIP_DB=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--skip-setup] [--skip-keycloak] [--skip-db]"
            exit 1
            ;;
    esac
done

echo "=========================================="
echo "MxA Mobile - Master Deployment"
echo "=========================================="
echo ""
echo "This script will deploy MxA Mobile across:"
echo "  - SSO Server:         192.168.1.59"
echo "  - Application Server: 192.168.1.66"
echo "  - Python Server:      192.168.1.90"
echo ""
read -p "Continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Deployment cancelled"
    exit 0
fi

# Step 1: Server Setup
if [ "$SKIP_SETUP" = false ]; then
    echo ""
    echo "=========================================="
    echo "Phase 1: Server Setup"
    echo "=========================================="
    
    echo ""
    echo "1.1: Setting up SSO Server (192.168.1.59)..."
    read -p "Run SSO server setup? (yes/no): " RUN_SSO
    if [ "$RUN_SSO" = "yes" ]; then
        echo "Please run on 192.168.1.59:"
        echo "  sudo bash $SCRIPT_DIR/1_setup_sso_server.sh"
        read -p "Press Enter when complete..."
    fi
    
    echo ""
    echo "1.2: Setting up Application Server (192.168.1.66)..."
    read -p "Run application server setup? (yes/no): " RUN_APP
    if [ "$RUN_APP" = "yes" ]; then
        if [ "$(hostname -I | grep -c '192.168.1.66')" -gt 0 ]; then
            sudo bash "$SCRIPT_DIR/2_setup_app_server.sh"
        else
            echo "Please run on 192.168.1.66:"
            echo "  sudo bash $SCRIPT_DIR/2_setup_app_server.sh"
            read -p "Press Enter when complete..."
        fi
    fi
    
    echo ""
    echo "1.3: Setting up Python Server (192.168.1.90)..."
    read -p "Run Python server setup? (yes/no): " RUN_PYTHON
    if [ "$RUN_PYTHON" = "yes" ]; then
        if [ "$(hostname -I | grep -c '192.168.1.90')" -gt 0 ]; then
            sudo bash "$SCRIPT_DIR/3_setup_python_server.sh"
        else
            echo "Please run on 192.168.1.90:"
            echo "  sudo bash $SCRIPT_DIR/3_setup_python_server.sh"
            read -p "Press Enter when complete..."
        fi
    fi
    
    echo ""
    echo "✓ Server setup phase complete"
fi

# Step 2: Keycloak Configuration
if [ "$SKIP_KEYCLOAK" = false ]; then
    echo ""
    echo "=========================================="
    echo "Phase 2: Keycloak Configuration"
    echo "=========================================="
    
    read -p "Configure Keycloak? (yes/no): " CONFIGURE_KC
    if [ "$CONFIGURE_KC" = "yes" ]; then
        # Check if jq is installed
        if ! command -v jq &> /dev/null; then
            echo "Installing jq..."
            sudo apt-get install -y jq
        fi
        
        bash "$SCRIPT_DIR/configure_keycloak.sh"
        
        echo ""
        echo "IMPORTANT: Save the client secret displayed above!"
        read -p "Press Enter to continue..."
        
        echo ""
        echo "Phase 2b: Updating .env files with Keycloak secret..."
        read -p "Update .env files now? (yes/no): " UPDATE_ENV
        if [ "$UPDATE_ENV" = "yes" ]; then
            bash "$SCRIPT_DIR/update_env.sh"
        fi
    fi
fi

# Step 3: Database Import
if [ "$SKIP_DB" = false ]; then
    echo ""
    echo "=========================================="
    echo "Phase 3: Database Schema Import"
    echo "=========================================="
    
    read -p "Import database schema? (yes/no): " IMPORT_DB
    if [ "$IMPORT_DB" = "yes" ]; then
        bash "$SCRIPT_DIR/import_database.sh"
    fi
fi

# Step 4: Application Deployment
echo ""
echo "=========================================="
echo "Phase 4: Application Deployment"
echo "=========================================="

read -p "Deploy application code? (yes/no): " DEPLOY_APP
if [ "$DEPLOY_APP" = "yes" ]; then
    bash "$SCRIPT_DIR/deploy.sh"
fi

# Step 5: Testing
echo ""
echo "=========================================="
echo "Phase 5: Deployment Testing"
echo "=========================================="

read -p "Run deployment tests? (yes/no): " RUN_TESTS
if [ "$RUN_TESTS" = "yes" ]; then
    bash "$SCRIPT_DIR/test_deployment.sh"
fi

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Access the application:"
echo "  Web UI:  http://192.168.1.66"
echo "  API:     http://192.168.1.90:8104"
echo "  Keycloak: http://192.168.1.59:8080"
echo ""
echo "Default credentials:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
echo "IMPORTANT: Change default passwords in production!"
echo ""
