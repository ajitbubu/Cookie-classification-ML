"""
Metrics middleware for automatic API request tracking.
"""

import time
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.monitoring.metrics import record_api_request

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically track API request metrics.
    
    Records:
    - Request count by endpoint, method, and status
    - Request latency by endpoint
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and record metrics.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
            
        Returns:
            The response from the route handler
        """
        # Record start time
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            # Record error and re-raise
            latency = time.time() - start_time
            record_api_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=500,
                latency_seconds=latency
            )
            raise
        
        # Calculate latency
        latency = time.time() - start_time
        
        # Record metrics (skip health/metrics endpoints to avoid noise)
        if not request.url.path.startswith('/api/v1/health') and \
           not request.url.path.startswith('/api/v1/metrics'):
            record_api_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=status_code,
                latency_seconds=latency
            )
        
        return response
