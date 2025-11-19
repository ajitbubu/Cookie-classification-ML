"""
JWT token creation and verification utilities.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID
from jose import JWTError, jwt
from pydantic import UUID4

from src.core.config import get_config
from src.models.user import TokenData, UserRole


def create_access_token(
    user_id: UUID4,
    email: str,
    role: UserRole,
    scopes: list = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: User ID
        email: User email
        role: User role
        scopes: Token scopes/permissions
        expires_delta: Token expiration time delta
        
    Returns:
        Encoded JWT token
    """
    config = get_config()
    
    if expires_delta is None:
        expires_delta = timedelta(hours=config.auth.jwt_expiration_hours)
    
    expire = datetime.utcnow() + expires_delta
    
    to_encode = {
        "sub": str(user_id),
        "email": email,
        "role": role.value if isinstance(role, UserRole) else role,
        "scopes": scopes or [],
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        config.auth.jwt_secret_key,
        algorithm=config.auth.jwt_algorithm
    )
    
    return encoded_jwt


def verify_token(token: str) -> Optional[TokenData]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token to verify

    Returns:
        TokenData if valid, None otherwise
    """
    import logging
    logger = logging.getLogger(__name__)

    config = get_config()

    try:
        payload = jwt.decode(
            token,
            config.auth.jwt_secret_key,
            algorithms=[config.auth.jwt_algorithm]
        )

        logger.info(f"JWT payload decoded successfully: {payload}")

        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        role: str = payload.get("role")
        scopes: list = payload.get("scopes", [])

        if user_id is None or email is None or role is None:
            logger.error(f"Missing required fields in JWT payload. user_id={user_id}, email={email}, role={role}")
            return None

        logger.info(f"Creating TokenData with user_id={user_id}, email={email}, role={role}, scopes={scopes}")

        return TokenData(
            user_id=UUID(user_id),
            email=email,
            role=UserRole(role),
            scopes=scopes
        )
    except JWTError as e:
        logger.error(f"JWT verification error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {type(e).__name__}: {str(e)}")
        return None


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode a JWT token without verification (for debugging).
    
    Args:
        token: JWT token to decode
        
    Returns:
        Decoded payload or None
    """
    try:
        return jwt.decode(
            token,
            options={"verify_signature": False}
        )
    except Exception:
        return None
