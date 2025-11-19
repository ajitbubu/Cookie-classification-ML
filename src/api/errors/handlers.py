"""
Global exception handlers for FastAPI.
"""

import time
import logging
from typing import Union

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError

from src.api.errors.exceptions import APIException

logger = logging.getLogger(__name__)


class ErrorResponse:
    """Standardized error response format."""
    
    @staticmethod
    def create(
        code: str,
        message: str,
        details: dict = None,
        request_id: str = None,
        timestamp: float = None
    ) -> dict:
        """
        Create standardized error response.
        
        Args:
            code: Error code
            message: Error message
            details: Additional error details
            request_id: Request ID for tracking
            timestamp: Error timestamp
            
        Returns:
            Error response dictionary
        """
        return {
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
                "timestamp": timestamp or time.time(),
                "request_id": request_id
            }
        }


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """
    Handle custom API exceptions.
    
    Args:
        request: FastAPI request
        exc: API exception
        
    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", None)
    
    logger.warning(
        f"API exception: {exc.code}",
        extra={
            "request_id": request_id,
            "code": exc.code,
            "message": exc.message,
            "details": exc.details
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse.create(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=request_id
        )
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions.
    
    Args:
        request: FastAPI request
        exc: HTTP exception
        
    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", None)
    
    logger.warning(
        f"HTTP exception: {exc.status_code}",
        extra={
            "request_id": request_id,
            "status_code": exc.status_code,
            "detail": exc.detail
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse.create(
            code=f"HTTP_{exc.status_code}",
            message=exc.detail,
            request_id=request_id
        )
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle request validation errors.
    
    Args:
        request: FastAPI request
        exc: Validation error
        
    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", None)
    
    # Format validation errors
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        "Request validation failed",
        extra={
            "request_id": request_id,
            "errors": errors
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse.create(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": errors},
            request_id=request_id
        )
    )


async def pydantic_validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """
    Handle Pydantic validation errors.
    
    Args:
        request: FastAPI request
        exc: Pydantic validation error
        
    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", None)
    
    # Format validation errors
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        "Pydantic validation failed",
        extra={
            "request_id": request_id,
            "errors": errors
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse.create(
            code="VALIDATION_ERROR",
            message="Data validation failed",
            details={"errors": errors},
            request_id=request_id
        )
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.
    
    Args:
        request: FastAPI request
        exc: Exception
        
    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", None)
    
    logger.exception(
        "Unhandled exception",
        extra={
            "request_id": request_id,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc)
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse.create(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            request_id=request_id
        )
    )


def register_exception_handlers(app):
    """
    Register all exception handlers with FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Exception handlers registered")
