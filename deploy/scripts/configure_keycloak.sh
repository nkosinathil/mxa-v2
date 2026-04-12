#!/bin/bash
#
# MxA Mobile - Keycloak Configuration Script
# Automatically configures Keycloak realm, client, and roles
#
# Prerequisites:
# - Keycloak running on 192.168.1.59:8080
# - Admin credentials available
#

set -e

echo "=========================================="
echo "MxA Mobile - Keycloak Configuration"
echo "=========================================="

# Configuration
KEYCLOAK_URL="${KEYCLOAK_URL:-http://192.168.1.59:8080}"
ADMIN_USER="${KEYCLOAK_ADMIN:-admin}"
ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-}"
REALM="forensics"
CLIENT_ID="mxa-mobile-web"
REDIRECT_URI="http://192.168.1.66/auth/callback"
WEB_ORIGINS="http://192.168.1.66"

echo "Keycloak Server: $KEYCLOAK_URL"
echo "Realm: $REALM"
echo "Client ID: $CLIENT_ID"
echo ""

if [ -z "$ADMIN_PASSWORD" ]; then
    echo "KEYCLOAK_ADMIN_PASSWORD must be set (export KEYCLOAK_ADMIN_PASSWORD=...)"
    exit 1
fi

# Function to get admin token
get_admin_token() {
    TOKEN=$(curl -s -X POST "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=$ADMIN_USER" \
        -d "password=$ADMIN_PASSWORD" \
        -d "grant_type=password" \
        -d "client_id=admin-cli" | jq -r '.access_token')
    
    if [ -z "$TOKEN" ] || [ "$TOKEN" == "null" ]; then
        echo "✗ Failed to get admin token. Check credentials."
        exit 1
    fi
    
    echo "$TOKEN"
}

echo "Step 1: Getting admin token..."
ADMIN_TOKEN=$(get_admin_token)
echo "✓ Admin token obtained"

echo ""
echo "Step 2: Creating realm '$REALM'..."
REALM_EXISTS=$(curl -s -o /dev/null -w "%{http_code}" \
    "$KEYCLOAK_URL/admin/realms/$REALM" \
    -H "Authorization: Bearer $ADMIN_TOKEN")

if [ "$REALM_EXISTS" == "200" ]; then
    echo "✓ Realm '$REALM' already exists"
else
    curl -s -X POST "$KEYCLOAK_URL/admin/realms" \
        -H "Authorization: Bearer $ADMIN_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"realm\": \"$REALM\",
            \"enabled\": true,
            \"displayName\": \"Forensics\",
            \"registrationAllowed\": false,
            \"loginWithEmailAllowed\": true,
            \"duplicateEmailsAllowed\": false,
            \"resetPasswordAllowed\": true,
            \"editUsernameAllowed\": false,
            \"bruteForceProtected\": true
        }"
    echo "✓ Realm '$REALM' created"
fi

echo ""
echo "Step 3: Creating client '$CLIENT_ID'..."
CLIENT_UUID=$(curl -s "$KEYCLOAK_URL/admin/realms/$REALM/clients" \
    -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r ".[] | select(.clientId==\"$CLIENT_ID\") | .id")

if [ ! -z "$CLIENT_UUID" ] && [ "$CLIENT_UUID" != "null" ]; then
    echo "✓ Client '$CLIENT_ID' already exists (ID: $CLIENT_UUID)"
else
    # Keycloak returns the new UUID in the Location response header (HTTP 201)
    LOCATION=$(curl -s -X POST "$KEYCLOAK_URL/admin/realms/$REALM/clients" \
        -H "Authorization: Bearer $ADMIN_TOKEN" \
        -H "Content-Type: application/json" \
        -D - -o /dev/null \
        -d "{
            \"clientId\": \"$CLIENT_ID\",
            \"name\": \"MxA Mobile Web Application\",
            \"enabled\": true,
            \"protocol\": \"openid-connect\",
            \"publicClient\": false,
            \"standardFlowEnabled\": true,
            \"implicitFlowEnabled\": false,
            \"directAccessGrantsEnabled\": true,
            \"serviceAccountsEnabled\": false,
            \"authorizationServicesEnabled\": false,
            \"redirectUris\": [\"$REDIRECT_URI\"],
            \"webOrigins\": [\"$WEB_ORIGINS\"],
            \"attributes\": {
                \"pkce.code.challenge.method\": \"S256\"
            }
        }" | grep -i "^Location:" | tr -d '\r' | awk '{print $2}')
    
    CLIENT_UUID=$(basename "$LOCATION")
    
    if [ -z "$CLIENT_UUID" ] || [ "$CLIENT_UUID" == "null" ]; then
        echo "✗ Failed to create client '$CLIENT_ID'"
        exit 1
    fi
    
    echo "✓ Client '$CLIENT_ID' created (ID: $CLIENT_UUID)"
fi

echo ""
echo "Step 4: Getting client secret..."
CLIENT_SECRET=$(curl -s "$KEYCLOAK_URL/admin/realms/$REALM/clients/$CLIENT_UUID/client-secret" \
    -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.value')

if [ ! -z "$CLIENT_SECRET" ] && [ "$CLIENT_SECRET" != "null" ]; then
    echo "✓ Client secret retrieved"
else
    # Generate new secret
    curl -s -X POST "$KEYCLOAK_URL/admin/realms/$REALM/clients/$CLIENT_UUID/client-secret" \
        -H "Authorization: Bearer $ADMIN_TOKEN"
    
    CLIENT_SECRET=$(curl -s "$KEYCLOAK_URL/admin/realms/$REALM/clients/$CLIENT_UUID/client-secret" \
        -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.value')
    
    echo "✓ New client secret generated"
fi

echo ""
echo "Step 5: Creating roles..."
for ROLE in "user" "analyst" "admin"; do
    ROLE_EXISTS=$(curl -s "$KEYCLOAK_URL/admin/realms/$REALM/roles" \
        -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r ".[] | select(.name==\"$ROLE\") | .name")
    
    if [ ! -z "$ROLE_EXISTS" ]; then
        echo "✓ Role '$ROLE' already exists"
    else
        curl -s -X POST "$KEYCLOAK_URL/admin/realms/$REALM/roles" \
            -H "Authorization: Bearer $ADMIN_TOKEN" \
            -H "Content-Type: application/json" \
            -d "{
                \"name\": \"$ROLE\",
                \"description\": \"MxA Mobile $ROLE role\"
            }"
        echo "✓ Role '$ROLE' created"
    fi
done

echo ""
echo "Step 6: Creating test users..."
# Create admin user
USER_EXISTS=$(curl -s "$KEYCLOAK_URL/admin/realms/$REALM/users?username=admin" \
    -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.[0].username')

if [ "$USER_EXISTS" == "admin" ]; then
    echo "✓ Admin user already exists"
else
    # Create user — Keycloak returns the new UUID in the Location response header (HTTP 201)
    USER_LOCATION=$(curl -s -X POST "$KEYCLOAK_URL/admin/realms/$REALM/users" \
        -H "Authorization: Bearer $ADMIN_TOKEN" \
        -H "Content-Type: application/json" \
        -D - -o /dev/null \
        -d '{
            "username": "admin",
            "email": "admin@example.com",
            "firstName": "System",
            "lastName": "Administrator",
            "enabled": true,
            "emailVerified": true
        }' | grep -i "^Location:" | tr -d '\r' | awk '{print $2}')
    
    USER_ID=$(basename "$USER_LOCATION")
    
    # Set password
    curl -s -X PUT "$KEYCLOAK_URL/admin/realms/$REALM/users/$USER_ID/reset-password" \
        -H "Authorization: Bearer $ADMIN_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "type": "password",
            "value": "admin123",
            "temporary": false
        }'
    
    # Assign admin role
    ADMIN_ROLE_ID=$(curl -s "$KEYCLOAK_URL/admin/realms/$REALM/roles/admin" \
        -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.id')
    
    curl -s -X POST "$KEYCLOAK_URL/admin/realms/$REALM/users/$USER_ID/role-mappings/realm" \
        -H "Authorization: Bearer $ADMIN_TOKEN" \
        -H "Content-Type: application/json" \
        -d "[{\"id\": \"$ADMIN_ROLE_ID\", \"name\": \"admin\"}]"
    
    echo "✓ Admin user created (username: admin, password: admin123)"
fi

echo ""
echo "=========================================="
echo "Keycloak Configuration Complete!"
echo "=========================================="
echo ""
echo "Realm: $REALM"
echo "Client ID: $CLIENT_ID"
echo "Client Secret: $CLIENT_SECRET"
echo ""
echo "Test User:"
echo "  Username: admin"
echo "  Password: admin123"
echo "  Role: admin"
echo ""
echo "IMPORTANT ACTIONS REQUIRED:"
echo "  1. Save the client secret to your .env files:"
echo "     - PHP:    /var/www/mxa-mobile-app/current/php-app/.env"
echo "     - Python: /opt/apps/mxa-mobile/python-backend/.env"
echo ""
echo "  2. Update KEYCLOAK_CLIENT_SECRET=$CLIENT_SECRET"
echo ""
echo "  3. For production, change the admin user password"
echo ""
echo "Keycloak Admin Console: $KEYCLOAK_URL"
echo ""
