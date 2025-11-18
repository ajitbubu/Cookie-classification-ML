"""
HTTPS redirect middleware for enforcing secure connections.
"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse
from typing import Callable

logger = logging.getLogger(__name__)


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware to redirect HTTP requests to HTTPS.
    
    This middleware enforces HTTPS by redirecting all HTTP requests
    to their HTTPS equivalents. Should only be enabled in production.
    """
    
    def __init__(self, app, enabled: bool = True, exclude_paths: list = None):
        """
        Initialize HTTPS redirect middleware.
        
        Args:
            app: FastAPI application
            enabled: Whether to enable HTTPS redirect
            exclude_paths: List of paths to exclude from redirect (e.g., health checks)
        """
        super().__init__(app)
        self.enabled = enabled
        self.exclude_paths = exclude_paths or ['/health', '/api/v1/health']
        
        if self.enabled:
            logger.info("HTTPS redirect middleware enabled")
        else:
            logger.info("HTTPS redirect middleware disabled")
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process request and redirect to HTTPS if needed.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response (redirect or normal)
        """
        # Skip if middleware is disabled
        if not self.enabled:
            return await call_next(request)
        
        # Skip excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Check if request is already HTTPS
        # Note: Check X-Forwarded-Proto header for proxy/load balancer scenarios
        forwarded_proto = request.headers.get('X-Forwarded-Proto', '').lower()
        is_secure = (
            request.url.scheme == 'https' or
            forwarded_proto == 'https'
        )
        
        if not is_secure:
            # Redirect to HTTPS
            https_url = request.url.replace(scheme='https')
            logger.info(f"Redirecting HTTP request to HTTPS: {request.url} -> {https_url}")
            return RedirectResponse(url=str(https_url), status_code=301)
        
        # Request is already HTTPS, continue
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to responses.
    
    Adds headers like HSTS, X-Content-Type-Options, etc.
    """
    
    def __init__(
        self,
        app,
        hsts_max_age: int = 31536000,  # 1 year
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False
    ):
        """
        Initialize security headers middleware.
        
        Args:
            app: FastAPI application
            hsts_max_age: HSTS max-age in seconds
            hsts_include_subdomains: Include subdomains in HSTS
            hsts_preload: Enable HSTS preload
        """
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        
        logger.info("Security headers middleware initialized")
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Add security headers to response.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response with security headers
        """
        response = await call_next(request)
        
        # Add HSTS header (HTTP Strict Transport Security)
        hsts_value = f"max-age={self.hsts_max_age}"
        if self.hsts_include_subdomains:
            hsts_value += "; includeSubDomains"
        if self.hsts_preload:
            hsts_value += "; preload"
        response.headers['Strict-Transport-Security'] = hsts_value
        
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Enable XSS protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        
        # Content Security Policy (basic)
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        
        # Referrer policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions policy (formerly Feature-Policy)
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        return response
