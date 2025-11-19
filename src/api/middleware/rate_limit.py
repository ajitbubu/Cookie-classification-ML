"""
Rate limiting middleware using Redis.
"""

import time
import logging
from typing import Callable, Optional
from functools import wraps

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from redis import Redis
from redis.exceptions import RedisError

from src.core.config import get_config

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Redis-based rate limiter using sliding window algorithm.
    """
    
    def __init__(self, redis_client: Optional[Redis] = None):
        """
        Initialize rate limiter.
        
        Args:
            redis_client: Redis client instance (optional)
        """
        self.redis = redis_client
        self.config = get_config()
    
    def _get_redis_client(self) -> Optional[Redis]:
        """Get or create Redis client."""
        if self.redis is None:
            try:
                # Create Redis client from config
                redis_url = str(self.config.redis.url)
                self.redis = Redis.from_url(
                    redis_url,
                    max_connections=self.config.redis.max_connections,
                    socket_timeout=self.config.redis.socket_timeout,
                    socket_connect_timeout=self.config.redis.socket_connect_timeout,
                    decode_responses=self.config.redis.decode_responses
                )
            except Exception as e:
                logger.error(f"Failed to create Redis client: {e}")
                return None
        return self.redis
    
    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window: int = 60
    ) -> tuple[bool, dict]:
        """
        Check if request is within rate limit using sliding window.
        
        Args:
            key: Rate limit key (e.g., API key or user ID)
            limit: Maximum requests allowed in window
            window: Time window in seconds (default: 60)
            
        Returns:
            Tuple of (is_allowed, info_dict)
            info_dict contains: remaining, reset_time, limit
        """
        redis = self._get_redis_client()
        
        # If Redis is unavailable, allow the request (fail open)
        if redis is None:
            logger.warning("Redis unavailable, rate limiting disabled")
            return True, {
                "limit": limit,
                "remaining": limit,
                "reset": int(time.time() + window)
            }
        
        try:
            current_time = time.time()
            window_start = current_time - window
            
            # Redis key for this rate limit
            redis_key = f"rate_limit:{key}:{window}"
            
            # Use Redis sorted set with timestamps as scores
            pipe = redis.pipeline()
            
            # Remove old entries outside the window
            pipe.zremrangebyscore(redis_key, 0, window_start)
            
            # Count requests in current window
            pipe.zcard(redis_key)
            
            # Add current request
            pipe.zadd(redis_key, {str(current_time): current_time})
            
            # Set expiration on the key
            pipe.expire(redis_key, window + 10)
            
            # Execute pipeline
            results = pipe.execute()
            request_count = results[1]  # Count from zcard
            
            # Check if limit exceeded
            is_allowed = request_count < limit
            remaining = max(0, limit - request_count - 1)
            reset_time = int(current_time + window)
            
            return is_allowed, {
                "limit": limit,
                "remaining": remaining,
                "reset": reset_time
            }
            
        except RedisError as e:
            logger.error(f"Redis error in rate limiting: {e}")
            # Fail open - allow request if Redis fails
            return True, {
                "limit": limit,
                "remaining": limit,
                "reset": int(time.time() + window)
            }
    
    async def get_rate_limit_info(self, key: str, window: int = 60) -> dict:
        """
        Get current rate limit information for a key.
        
        Args:
            key: Rate limit key
            window: Time window in seconds
            
        Returns:
            Dictionary with current count and window info
        """
        redis = self._get_redis_client()
        
        if redis is None:
            return {"count": 0, "window": window}
        
        try:
            current_time = time.time()
            window_start = current_time - window
            redis_key = f"rate_limit:{key}:{window}"
            
            # Remove old entries and count
            pipe = redis.pipeline()
            pipe.zremrangebyscore(redis_key, 0, window_start)
            pipe.zcard(redis_key)
            results = pipe.execute()
            
            return {
                "count": results[1],
                "window": window,
                "window_start": window_start,
                "current_time": current_time
            }
            
        except RedisError as e:
            logger.error(f"Redis error getting rate limit info: {e}")
            return {"count": 0, "window": window}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for applying rate limits to API requests.
    """
    
    def __init__(self, app: ASGIApp, redis_client: Optional[Redis] = None):
        super().__init__(app)
        self.rate_limiter = RateLimiter(redis_client)
        self.default_limit = 100  # Default: 100 requests per minute
        self.default_window = 60  # 60 seconds
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and apply rate limiting.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response from handler or 429 if rate limited
        """
        # Skip rate limiting for health check and docs
        if request.url.path in ["/api/v1/health", "/api/docs", "/api/redoc", "/api/openapi.json", "/"]:
            return await call_next(request)
        
        # Determine rate limit key (API key, user ID, or IP address)
        rate_limit_key = self._get_rate_limit_key(request)
        
        # Get rate limit for this key (could be customized per user/API key)
        limit = self.default_limit
        window = self.default_window
        
        # Check rate limit
        is_allowed, info = await self.rate_limiter.check_rate_limit(
            rate_limit_key,
            limit,
            window
        )
        
        # Add rate limit headers to response
        if not is_allowed:
            # Rate limit exceeded
            return Response(
                content='{"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Rate limit exceeded. Please try again later."}}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info["reset"]),
                    "Retry-After": str(window),
                    "Content-Type": "application/json"
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to successful response
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])
        
        return response
    
    def _get_rate_limit_key(self, request: Request) -> str:
        """
        Determine rate limit key from request.
        
        Priority:
        1. API key from X-API-Key header
        2. User ID from JWT token
        3. Client IP address
        
        Args:
            request: Incoming request
            
        Returns:
            Rate limit key
        """
        # Check for API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key}"
        
        # Check for JWT token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            # Use token as key (in production, decode and use user ID)
            return f"token:{token[:16]}"  # Use first 16 chars as key
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"


def rate_limit(limit: int = 100, window: int = 60):
    """
    Decorator for applying rate limits to specific endpoints.
    
    Args:
        limit: Maximum requests allowed in window
        window: Time window in seconds
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request from kwargs
            request = kwargs.get("request")
            if not request:
                # Try to find request in args
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if request:
                rate_limiter = RateLimiter()
                
                # Get rate limit key
                api_key = request.headers.get("X-API-Key")
                if api_key:
                    key = f"api_key:{api_key}"
                else:
                    client_ip = request.client.host if request.client else "unknown"
                    key = f"ip:{client_ip}"
                
                # Check rate limit
                is_allowed, info = await rate_limiter.check_rate_limit(key, limit, window)
                
                if not is_allowed:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded",
                        headers={
                            "X-RateLimit-Limit": str(info["limit"]),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(info["reset"]),
                            "Retry-After": str(window)
                        }
                    )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
