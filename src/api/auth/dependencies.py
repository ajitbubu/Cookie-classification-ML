"""
FastAPI authentication dependencies.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from pydantic import UUID4

from src.api.auth.jwt import verify_token
from src.api.auth.api_key import verify_api_key, APIKeyValidator
from src.models.user import TokenData, UserRole

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> Optional[TokenData]:
    """
    Get current user from JWT token.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        TokenData if authenticated, None otherwise
        
    Raises:
        HTTPException: If token is invalid
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    token_data = verify_token(token)
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_data


async def get_current_user_from_api_key(
    api_key: Optional[str] = Security(api_key_header)
) -> Optional[TokenData]:
    """
    Get current user from API key.
    
    Args:
        api_key: API key from header
        
    Returns:
        TokenData if authenticated, None otherwise
        
    Raises:
        HTTPException: If API key is invalid
    """
    if not api_key:
        return None
    
    # Validate API key format
    validator = APIKeyValidator()
    if not validator.validate_key_format(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format"
        )
    
    # TODO: Look up API key in database and validate
    # For now, return None to indicate API key auth not fully implemented
    return None


async def get_current_user(
    token_user: Optional[TokenData] = Depends(get_current_user_from_token),
    api_key_user: Optional[TokenData] = Depends(get_current_user_from_api_key)
) -> TokenData:
    """
    Get current authenticated user from either JWT token or API key.
    
    Args:
        token_user: User from JWT token
        api_key_user: User from API key
        
    Returns:
        TokenData for authenticated user
        
    Raises:
        HTTPException: If not authenticated
    """
    user = token_user or api_key_user
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def require_role(required_role: UserRole):
    """
    Dependency factory for role-based access control.
    
    Args:
        required_role: Required user role
        
    Returns:
        Dependency function
    """
    async def role_checker(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        """Check if user has required role."""
        # Admin has access to everything
        if current_user.role == UserRole.ADMIN:
            return current_user
        
        # Check specific role
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role.value}"
            )
        
        return current_user
    
    return role_checker


def require_scope(required_scope: str):
    """
    Dependency factory for scope-based access control.
    
    Args:
        required_scope: Required scope
        
    Returns:
        Dependency function
    """
    async def scope_checker(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        """Check if user has required scope."""
        # Admin has all scopes
        if current_user.role == UserRole.ADMIN or 'admin' in current_user.scopes:
            return current_user
        
        # Check specific scope
        if required_scope not in current_user.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scope: {required_scope}"
            )
        
        return current_user
    
    return scope_checker


# Common role dependencies
require_admin = require_role(UserRole.ADMIN)
require_user = require_role(UserRole.USER)
