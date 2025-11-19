"""
User and authentication-related data models.
"""

from datetime import datetime
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field, EmailStr, validator, UUID4


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class User(BaseModel):
    """User data model."""
    user_id: Optional[UUID4] = None
    email: EmailStr = Field(..., description="User email address")
    password_hash: Optional[str] = Field(None, description="Hashed password")
    role: UserRole = Field(default=UserRole.USER, description="User role")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class UserCreate(BaseModel):
    """User creation model."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    role: UserRole = Field(default=UserRole.USER, description="User role")
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseModel):
    """User update model."""
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    role: Optional[UserRole] = None
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength if provided."""
        if v is None:
            return v
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class APIKey(BaseModel):
    """API key data model."""
    api_key_id: Optional[UUID4] = None
    user_id: UUID4 = Field(..., description="User ID this key belongs to")
    key_hash: str = Field(..., description="Hashed API key")
    scopes: List[str] = Field(default_factory=list, description="API key scopes/permissions")
    rate_limit: int = Field(default=100, ge=1, le=10000, description="Rate limit (requests per minute)")
    enabled: bool = Field(default=True, description="Whether key is enabled")
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    @validator('scopes')
    def validate_scopes(cls, v):
        """Validate API key scopes."""
        valid_scopes = {
            'scans:read',
            'scans:write',
            'schedules:read',
            'schedules:write',
            'reports:read',
            'reports:write',
            'analytics:read',
            'profiles:read',
            'profiles:write',
            'notifications:read',
            'notifications:write',
            'admin'
        }
        for scope in v:
            if scope not in valid_scopes:
                raise ValueError(f"Invalid scope: {scope}")
        return v


class APIKeyCreate(BaseModel):
    """API key creation model."""
    user_id: UUID4 = Field(..., description="User ID")
    scopes: List[str] = Field(default_factory=list, description="API key scopes")
    rate_limit: int = Field(default=100, ge=1, le=10000, description="Rate limit")
    expires_at: Optional[datetime] = None
    
    @validator('scopes')
    def validate_scopes(cls, v):
        """Validate API key scopes."""
        valid_scopes = {
            'scans:read',
            'scans:write',
            'schedules:read',
            'schedules:write',
            'reports:read',
            'reports:write',
            'analytics:read',
            'profiles:read',
            'profiles:write',
            'notifications:read',
            'notifications:write',
            'admin'
        }
        for scope in v:
            if scope not in valid_scopes:
                raise ValueError(f"Invalid scope: {scope}")
        return v


class Token(BaseModel):
    """JWT token model."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class TokenData(BaseModel):
    """Token payload data model."""
    user_id: UUID4 = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    role: UserRole = Field(..., description="User role")
    scopes: List[str] = Field(default_factory=list, description="Token scopes")
    
    class Config:
        use_enum_values = True
