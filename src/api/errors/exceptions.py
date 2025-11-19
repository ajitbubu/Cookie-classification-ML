"""
Custom exception classes for the API.
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class APIException(HTTPException):
    """Base API exception class."""
    
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(status_code=status_code, detail=message)


class ValidationException(APIException):
    """Validation error exception."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message=message,
            details=details
        )


class AuthenticationException(APIException):
    """Authentication error exception."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="AUTHENTICATION_ERROR",
            message=message
        )


class AuthorizationException(APIException):
    """Authorization error exception."""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="AUTHORIZATION_ERROR",
            message=message
        )


class NotFoundException(APIException):
    """Resource not found exception."""
    
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"{resource} with ID {resource_id} not found",
            details={"resource": resource, "resource_id": resource_id}
        )


class ConflictException(APIException):
    """Resource conflict exception."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code="CONFLICT",
            message=message,
            details=details
        )


class RateLimitException(APIException):
    """Rate limit exceeded exception."""
    
    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="RATE_LIMIT_EXCEEDED",
            message="Rate limit exceeded. Please try again later.",
            details={"retry_after": retry_after}
        )


class ScanException(APIException):
    """Scan-related exception."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="SCAN_ERROR",
            message=message,
            details=details
        )


class DatabaseException(APIException):
    """Database-related exception."""
    
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="DATABASE_ERROR",
            message=message
        )


class CacheException(APIException):
    """Cache-related exception."""
    
    def __init__(self, message: str = "Cache operation failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="CACHE_ERROR",
            message=message
        )


class ExternalServiceException(APIException):
    """External service error exception."""
    
    def __init__(self, service: str, message: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="EXTERNAL_SERVICE_ERROR",
            message=f"{service} service error: {message}",
            details={"service": service}
        )
