"""
Security utilities for authentication and authorization.
"""

from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from keycloak import KeycloakOpenID

from app.core.config import settings
from app.core.logging import logger


security = HTTPBearer()


# Initialize Keycloak client
keycloak_openid = KeycloakOpenID(
    server_url=settings.keycloak_server_url,
    realm_name=settings.keycloak_realm,
    client_id=settings.keycloak_client_id,
    client_secret_key=settings.keycloak_client_secret
)


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> dict:
    """
    Verify JWT token from Keycloak and return user info.
    
    Args:
        credentials: HTTP Bearer token
        
    Returns:
        User information from token
        
    Raises:
        HTTPException: If token is invalid
    """
    token = credentials.credentials
    
    try:
        # Validate token with Keycloak
        user_info = keycloak_openid.introspect(token)
        
        if not user_info.get('active'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        return user_info
        
    except Exception as e:
        logger.error(f"Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


def check_role(user_info: dict, required_role: str) -> bool:
    """
    Check if user has required role.
    
    Args:
        user_info: User information from token
        required_role: Required role name
        
    Returns:
        True if user has role, False otherwise
    """
    roles = user_info.get('realm_access', {}).get('roles', [])
    return required_role in roles


async def require_role(
    required_role: str,
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> dict:
    """
    Dependency that requires user to have specific role.
    
    Args:
        required_role: Required role name
        credentials: HTTP Bearer token
        
    Returns:
        User information
        
    Raises:
        HTTPException: If user doesn't have required role
    """
    user_info = await verify_token(credentials)
    
    if not check_role(user_info, required_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User does not have required role: {required_role}"
        )
    
    return user_info
