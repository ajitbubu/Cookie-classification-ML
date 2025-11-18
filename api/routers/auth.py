"""
Authentication endpoints.
"""

from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel, EmailStr, Field

from api.auth.password import hash_password, verify_password
from api.auth.jwt import create_access_token
from api.auth.api_key import generate_api_key, hash_api_key
from api.auth.dependencies import get_current_user
from api.auth.lockout import get_lockout_manager
from api.auth.audit import get_audit_logger
from models.user import Token, TokenData, UserRole, APIKeyCreate
from core.config import get_config

router = APIRouter()


class LoginRequest(BaseModel):
    """Login request model."""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LockoutResponse(BaseModel):
    """Account lockout response model."""
    locked: bool = True
    message: str
    unlock_time: Optional[str] = None
    failed_attempts: int
    max_attempts: int


class APIKeyResponse(BaseModel):
    """API key response model."""
    api_key: str = Field(..., description="Generated API key (save this, it won't be shown again)")
    api_key_id: str = Field(..., description="API key ID")
    key_hash: str = Field(..., description="Hashed API key for storage")


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticate user and receive JWT access token"
)
async def login(request: LoginRequest, http_request: Request):
    """
    Authenticate user with email and password.
    
    Returns JWT access token for subsequent API calls.
    
    Implements account lockout after 5 failed attempts within 15 minutes.
    Locked accounts are automatically unlocked after 15 minutes.
    
    **Note**: This is a placeholder implementation. In production, this should:
    - Query the database for the user
    - Verify the password hash
    """
    lockout_manager = get_lockout_manager()
    audit_logger = get_audit_logger()
    
    # Get client IP address
    ip_address = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")
    
    # Check if account is locked
    is_locked, unlock_time = lockout_manager.is_locked(request.email)
    if is_locked:
        # Log failed login attempt due to lockout
        audit_logger.log_authentication(
            success=False,
            email=request.email,
            ip_address=ip_address,
            user_agent=user_agent,
            reason="Account locked"
        )
        
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail={
                "error": "account_locked",
                "message": f"Account is locked due to too many failed login attempts. Try again after {unlock_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                "unlock_time": unlock_time.isoformat() if unlock_time else None,
                "locked_for_seconds": int((unlock_time - __import__('datetime').datetime.utcnow()).total_seconds()) if unlock_time else None
            }
        )
    
    # TODO: Implement actual database lookup and password verification
    # This is a placeholder for demonstration
    
    # Simulate user lookup (replace with actual database query)
    # For now, accept any email/password for testing
    authentication_successful = bool(request.email and request.password)
    
    if not authentication_successful:
        # Record failed attempt
        should_lock, attempt_count, unlock_time = lockout_manager.record_failed_attempt(
            request.email,
            ip_address
        )
        
        # Log failed authentication
        audit_logger.log_authentication(
            success=False,
            email=request.email,
            ip_address=ip_address,
            user_agent=user_agent,
            reason="Invalid credentials"
        )
        
        if should_lock:
            # Account has been locked
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail={
                    "error": "account_locked",
                    "message": f"Account locked due to too many failed login attempts ({attempt_count}). Try again after {unlock_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    "unlock_time": unlock_time.isoformat() if unlock_time else None,
                    "failed_attempts": attempt_count
                }
            )
        else:
            # Not locked yet, but show remaining attempts
            remaining = lockout_manager.max_attempts - attempt_count
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "invalid_credentials",
                    "message": f"Invalid credentials. {remaining} attempts remaining before account lockout.",
                    "failed_attempts": attempt_count,
                    "remaining_attempts": remaining
                }
            )
    
    # Authentication successful - reset failed attempts
    lockout_manager.reset_attempts(request.email)
    
    # Create mock user data (replace with actual user from database)
    from uuid import uuid4
    user_id = uuid4()
    
    # Log successful authentication
    audit_logger.log_authentication(
        success=True,
        email=request.email,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    config = get_config()
    
    # Create access token
    access_token = create_access_token(
        user_id=user_id,
        email=request.email,
        role=UserRole.USER,
        scopes=["scans:read", "scans:write", "schedules:read", "schedules:write", "analytics:read"]
    )
    
    expires_in = config.auth.jwt_expiration_hours * 3600  # Convert to seconds
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in
    )


@router.post(
    "/api-keys",
    response_model=APIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate API key",
    description="Generate a new API key for programmatic access"
)
async def create_api_key(
    request: APIKeyCreate,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Generate a new API key.
    
    **Important**: The plain API key is only returned once. Store it securely.
    
    **Note**: This is a placeholder implementation. In production, this should:
    - Store the hashed key in the database
    - Associate it with the user
    - Set expiration and rate limits
    """
    # Generate API key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    
    # TODO: Store in database
    from uuid import uuid4
    api_key_id = str(uuid4())
    
    return APIKeyResponse(
        api_key=api_key,
        api_key_id=api_key_id,
        key_hash=key_hash
    )


@router.get(
    "/me",
    response_model=TokenData,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get information about the currently authenticated user"
)
async def get_me(current_user: TokenData = Depends(get_current_user)):
    """
    Get current authenticated user information.
    
    Returns user details from the JWT token.
    """
    return current_user
