"""
Request context middleware for structured logging.

This middleware adds request_id and user_id to the logging context
for all requests, making it easy to trace logs for a specific request.
"""

import uuid
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from core.logging_config import bind_context, clear_context, get_logger

logger = get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add request context to structured logs.
    
    Adds:
    - request_id: Unique identifier for each request
    - user_id: User ID from authentication (if available)
    - method: HTTP method
    - path: Request path
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add context to logs.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
            
        Returns:
            The response from the route handler
        """
        # Generate or extract request ID
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        
        # Extract user ID from request state (set by auth middleware)
        user_id = getattr(request.state, 'user_id', None)
        
        # Bind context for this request
        context = {
            'request_id': request_id,
            'method': request.method,
            'path': request.url.path,
        }
        
        if user_id:
            context['user_id'] = user_id
        
        bind_context(**context)
        
        try:
            # Log request start
            logger.info(
                "request_started",
                client_host=request.client.host if request.client else None,
                user_agent=request.headers.get('user-agent'),
            )
            
            # Process request
            response = await call_next(request)
            
            # Add request ID to response headers
            response.headers['X-Request-ID'] = request_id
            
            # Log request completion
            logger.info(
                "request_completed",
                status_code=response.status_code,
            )
            
            return response
            
        except Exception as e:
            # Log error
            logger.error(
                "request_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
            
        finally:
            # Clear context after request
            clear_context()
