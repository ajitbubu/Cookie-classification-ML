"""
FastAPI application main entry point.
"""

import time
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

import asyncpg
from redis import Redis

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.config import get_config
from core.logging_config import configure_structlog, get_logger as get_struct_logger
from core.sentry_config import init_sentry
from api.middleware.logging import LoggingMiddleware
from api.middleware.metrics import MetricsMiddleware
from api.middleware.request_context import RequestContextMiddleware
from api.errors.handlers import register_exception_handlers
from api.routers import scans, schedules, analytics, profiles, notifications, health, auth, ml_admin

# Get config
config = get_config()

# Initialize structured logging
configure_structlog(
    log_level=config.monitoring.log_level,
    json_logs=(config.monitoring.log_format == 'json'),
    development_mode=(config.environment == 'development')
)

# Initialize Sentry (if configured)
if config.monitoring.sentry_dsn:
    init_sentry(
        dsn=config.monitoring.sentry_dsn,
        environment=config.environment,
        release='2.0.0',
        traces_sample_rate=0.1 if config.environment == 'production' else 1.0,
        enable_tracing=True
    )

logger = logging.getLogger(__name__)
struct_logger = get_struct_logger(__name__)

# Global references for dependency injection
_db_pool: Optional[asyncpg.Pool] = None
_redis_client: Optional[Redis] = None


def get_db_pool() -> asyncpg.Pool:
    """Get database pool instance."""
    if _db_pool is None:
        raise RuntimeError("Database pool not initialized")
    return _db_pool


def get_redis_client() -> Optional[Redis]:
    """Get Redis client instance."""
    return _redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    global _db_pool, _redis_client
    
    # Startup
    logger.info("Starting Dynamic Cookie Scanning Service API Gateway")
    config = get_config()
    logger.info(f"Environment: {config.environment}")
    logger.info(f"API running on {config.api.host}:{config.api.port}")
    
    # Initialize database pool
    try:
        logger.info("Initializing database connection pool...")
        _db_pool = await asyncpg.create_pool(
            dsn=config.database.url,
            min_size=5,
            max_size=config.database.pool_size + config.database.max_overflow,
            command_timeout=60
        )
        app.state.db_pool = _db_pool
        logger.info("Database pool initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")
        raise
    
    # Initialize Redis client (optional)
    try:
        if hasattr(config, 'redis') and config.redis.url:
            logger.info("Initializing Redis client...")
            _redis_client = Redis.from_url(
                config.redis.url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            _redis_client.ping()
            app.state.redis_client = _redis_client
            logger.info("Redis client initialized successfully")
        else:
            logger.info("Redis not configured, caching disabled")
            app.state.redis_client = None
    except Exception as e:
        logger.warning(f"Failed to initialize Redis client: {e} (continuing without cache)")
        _redis_client = None
        app.state.redis_client = None
    
    yield
    
    # Shutdown
    logger.info("Shutting down Dynamic Cookie Scanning Service API Gateway")
    
    # Close database pool
    if _db_pool:
        logger.info("Closing database pool...")
        await _db_pool.close()
        logger.info("Database pool closed")
    
    # Close Redis client
    if _redis_client:
        logger.info("Closing Redis client...")
        _redis_client.close()
        logger.info("Redis client closed")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    config = get_config()
    
    # OpenAPI metadata
    description = """
## Dynamic Cookie Scanning Service API

A comprehensive cookie compliance and analytics platform for automated website scanning,
cookie categorization, and compliance reporting.

### Features

* **Scan Management**: Create and manage cookie scans with multiple modes (quick, deep, scheduled, real-time)
* **Schedule Management**: Set up recurring scans with flexible scheduling options
* **Analytics**: Generate compliance reports and track trends over time
* **Notifications**: Multi-channel notifications for scan events and compliance issues
* **Authentication**: Secure API access with JWT tokens and API keys
* **Rate Limiting**: Built-in rate limiting to prevent abuse

### Authentication

This API supports two authentication methods:

1. **JWT Bearer Token**: For dashboard and user sessions
   - Obtain token via `/api/v1/auth/login`
   - Include in requests: `Authorization: Bearer <token>`

2. **API Key**: For programmatic access
   - Generate via `/api/v1/auth/api-keys`
   - Include in requests: `X-API-Key: <key>`

### Rate Limiting

All endpoints are rate-limited. Rate limit information is included in response headers:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when limit resets

### Error Responses

All errors follow a standardized format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {},
    "timestamp": 1234567890.123,
    "request_id": "uuid"
  }
}
```
    """
    
    app = FastAPI(
        title="Dynamic Cookie Scanning Service API",
        description=description,
        version="2.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
        contact={
            "name": "DCS Support",
            "email": "support@example.com"
        },
        license_info={
            "name": "Proprietary"
        },
        openapi_tags=[
            {
                "name": "Authentication",
                "description": "User authentication and API key management"
            },
            {
                "name": "Scans",
                "description": "Cookie scan creation and management"
            },
            {
                "name": "Schedules",
                "description": "Recurring scan schedule management"
            },
            {
                "name": "Analytics",
                "description": "Reports, metrics, and trend analysis"
            },
            {
                "name": "Profiles",
                "description": "Scan profile configuration"
            },
            {
                "name": "Notifications",
                "description": "Notification preferences and history"
            },
            {
                "name": "Health",
                "description": "System health and monitoring"
            }
        ]
    )
    
    # Configure CORS - allow all origins for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"]
    )
    logger.info("CORS enabled for all origins (development mode)")
    
    # Add gzip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Add request context middleware (for structured logging)
    app.add_middleware(RequestContextMiddleware)
    
    # Add custom logging middleware
    app.add_middleware(LoggingMiddleware)
    
    # Add metrics middleware
    app.add_middleware(MetricsMiddleware)
    
    # Include routers
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(scans.router, prefix="/api/v1/scans", tags=["Scans"])
    app.include_router(schedules.router, prefix="/api/v1/schedules", tags=["Schedules"])
    app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
    app.include_router(profiles.router, prefix="/api/v1/profiles", tags=["Profiles"])
    app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])
    app.include_router(ml_admin.router, prefix="/api/v1/ml", tags=["ML Administration"])
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    
    # Register exception handlers
    register_exception_handlers(app)
    
    logger.info("FastAPI application created successfully")
    return app


# Create app instance
app = create_app()


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint."""
    return {
        "service": "Dynamic Cookie Scanning Service",
        "version": "2.0.0",
        "docs": "/api/docs",
        "health": "/api/v1/health"
    }
