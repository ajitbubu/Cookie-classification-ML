"""
Health check and monitoring endpoints.
"""

from fastapi import APIRouter, status, Request, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime

from src.services.health_checker import HealthChecker
from src.api.monitoring.metrics import get_metrics_text, get_metrics_content_type

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    version: str
    components: Dict[str, Dict[str, Any]]


def get_health_checker(request: Request) -> HealthChecker:
    """Dependency to get health checker from app state."""
    return HealthChecker(
        db_pool=request.app.state.db_pool,
        redis_client=getattr(request.app.state, 'redis_client', None)
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check with component status",
    description="Check the health status of the API and all its components"
)
async def health_check(request: Request, response: Response):
    """
    Comprehensive health check endpoint.
    
    Returns health status of the API and its components including:
    - Database connectivity and pool status
    - Redis cache availability
    - Browser engine availability
    - Scheduler service status
    
    Status codes:
    - 200: System is healthy or degraded (some non-critical components down)
    - 503: System is unhealthy (critical components down)
    """
    health_checker = get_health_checker(request)
    health_status = await health_checker.check_health()
    
    # Set appropriate status code
    if health_status['status'] == 'unhealthy':
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return HealthResponse(**health_status)


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    status_code=status.HTTP_200_OK,
    summary="Prometheus metrics",
    description="Get Prometheus metrics for monitoring and observability"
)
async def prometheus_metrics(request: Request):
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus text format including:
    - Scan metrics (total scans by mode and status, scan duration, active scans)
    - API metrics (request counts by endpoint/method/status, request latency)
    - Database metrics (connection pool statistics)
    - Cache metrics (hit rate)
    
    This endpoint is designed to be scraped by Prometheus for monitoring.
    """
    # Update database connection metrics
    try:
        db_pool = request.app.state.db_pool
        if db_pool:
            from src.api.monitoring.metrics import update_db_connections
            pool_size = db_pool.get_size()
            pool_free = db_pool.get_idle_size()
            pool_used = pool_size - pool_free
            update_db_connections(pool_size, pool_used, pool_free)
    except Exception:
        pass  # Ignore errors in metric collection
    
    # Update cache hit rate
    try:
        redis_client = getattr(request.app.state, 'redis_client', None)
        if redis_client:
            from src.api.monitoring.metrics import update_cache_hit_rate
            info = redis_client.info('stats')
            hits = info.get('keyspace_hits', 0)
            misses = info.get('keyspace_misses', 0)
            total = hits + misses
            if total > 0:
                hit_rate = hits / total
                update_cache_hit_rate(hit_rate)
    except Exception:
        pass  # Ignore errors in metric collection
    
    # Return Prometheus metrics
    metrics_text = get_metrics_text()
    return PlainTextResponse(
        content=metrics_text.decode('utf-8'),
        media_type=get_metrics_content_type()
    )


@router.get(
    "/metrics/summary",
    status_code=status.HTTP_200_OK,
    summary="System metrics summary",
    description="Get system metrics summary in JSON format"
)
async def get_metrics_summary(request: Request):
    """
    Get system metrics summary endpoint.
    
    Returns metrics in JSON format including:
    - Database connection pool statistics
    - Cache hit rates and statistics
    - Scan counts (total, active, failed)
    - API request statistics (if available)
    
    This endpoint provides a human-readable JSON summary of system metrics.
    """
    health_checker = get_health_checker(request)
    metrics = await health_checker.get_metrics()
    
    return metrics


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="Check if the service is ready to accept requests"
)
async def readiness_check(request: Request, response: Response):
    """
    Readiness check for Kubernetes/container orchestration.
    
    Returns 200 if service is ready to accept traffic, 503 otherwise.
    This is a lightweight check focused on critical dependencies.
    """
    health_checker = get_health_checker(request)
    
    # Check only critical components
    db_health = await health_checker.check_database()
    
    if db_health.status == 'unhealthy':
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            'ready': False,
            'reason': 'Database unavailable'
        }
    
    return {
        'ready': True,
        'timestamp': datetime.utcnow().isoformat()
    }


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness check",
    description="Check if the service is alive"
)
async def liveness_check():
    """
    Liveness check for Kubernetes/container orchestration.
    
    Returns 200 if the service process is alive.
    This is a very lightweight check with no external dependencies.
    """
    return {
        'alive': True,
        'timestamp': datetime.utcnow().isoformat()
    }
