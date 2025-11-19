"""
Prometheus metrics for monitoring and observability.

This module defines and manages all Prometheus metrics for the DCS platform,
including scan metrics, API metrics, database metrics, and cache metrics.
"""

import logging
from typing import Optional

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST
)

logger = logging.getLogger(__name__)

# Create a custom registry for our metrics
metrics_registry = CollectorRegistry()

# ============================================================================
# Scan Metrics
# ============================================================================

scan_counter = Counter(
    'dcs_scans_total',
    'Total number of scans by mode and status',
    ['scan_mode', 'status'],
    registry=metrics_registry
)

scan_duration_histogram = Histogram(
    'dcs_scan_duration_seconds',
    'Scan duration in seconds',
    ['scan_mode'],
    buckets=(10, 30, 60, 120, 300, 600, 1800, 3600),  # 10s to 1h
    registry=metrics_registry
)

active_scans_gauge = Gauge(
    'dcs_active_scans',
    'Number of currently active scans',
    registry=metrics_registry
)

# ============================================================================
# API Metrics
# ============================================================================

api_request_counter = Counter(
    'dcs_api_requests_total',
    'Total API requests by endpoint, method, and status',
    ['endpoint', 'method', 'status'],
    registry=metrics_registry
)

api_latency_histogram = Histogram(
    'dcs_api_latency_seconds',
    'API request latency in seconds',
    ['endpoint'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),  # 10ms to 10s
    registry=metrics_registry
)

# ============================================================================
# Database Metrics
# ============================================================================

db_connections_gauge = Gauge(
    'dcs_db_connections',
    'Database connection pool statistics',
    ['state'],  # 'total', 'used', 'free'
    registry=metrics_registry
)

# ============================================================================
# Cache Metrics
# ============================================================================

cache_hit_rate_gauge = Gauge(
    'dcs_cache_hit_rate',
    'Cache hit rate (0.0 to 1.0)',
    registry=metrics_registry
)

# ============================================================================
# Helper Functions
# ============================================================================

def record_scan_started(scan_mode: str):
    """
    Record that a scan has started.
    
    Args:
        scan_mode: The scan mode (quick, deep, scheduled, realtime)
    """
    try:
        scan_counter.labels(scan_mode=scan_mode, status='started').inc()
        logger.debug(f"Recorded scan start: mode={scan_mode}")
    except Exception as e:
        logger.error(f"Failed to record scan start metric: {e}")


def record_scan_completed(scan_mode: str, duration_seconds: float):
    """
    Record that a scan has completed successfully.
    
    Args:
        scan_mode: The scan mode (quick, deep, scheduled, realtime)
        duration_seconds: Duration of the scan in seconds
    """
    try:
        scan_counter.labels(scan_mode=scan_mode, status='completed').inc()
        scan_duration_histogram.labels(scan_mode=scan_mode).observe(duration_seconds)
        logger.debug(f"Recorded scan completion: mode={scan_mode}, duration={duration_seconds}s")
    except Exception as e:
        logger.error(f"Failed to record scan completion metric: {e}")


def record_scan_failed(scan_mode: str, duration_seconds: Optional[float] = None):
    """
    Record that a scan has failed.
    
    Args:
        scan_mode: The scan mode (quick, deep, scheduled, realtime)
        duration_seconds: Duration before failure (optional)
    """
    try:
        scan_counter.labels(scan_mode=scan_mode, status='failed').inc()
        if duration_seconds is not None:
            scan_duration_histogram.labels(scan_mode=scan_mode).observe(duration_seconds)
        logger.debug(f"Recorded scan failure: mode={scan_mode}")
    except Exception as e:
        logger.error(f"Failed to record scan failure metric: {e}")


def record_api_request(endpoint: str, method: str, status_code: int, latency_seconds: float):
    """
    Record an API request.
    
    Args:
        endpoint: The API endpoint path (e.g., '/api/v1/scans')
        method: HTTP method (GET, POST, etc.)
        status_code: HTTP status code
        latency_seconds: Request latency in seconds
    """
    try:
        # Normalize endpoint to remove IDs and query params
        normalized_endpoint = _normalize_endpoint(endpoint)
        
        api_request_counter.labels(
            endpoint=normalized_endpoint,
            method=method,
            status=str(status_code)
        ).inc()
        
        api_latency_histogram.labels(endpoint=normalized_endpoint).observe(latency_seconds)
        
        logger.debug(
            f"Recorded API request: endpoint={normalized_endpoint}, "
            f"method={method}, status={status_code}, latency={latency_seconds}s"
        )
    except Exception as e:
        logger.error(f"Failed to record API request metric: {e}")


def update_active_scans(count: int):
    """
    Update the number of active scans.
    
    Args:
        count: Current number of active scans
    """
    try:
        active_scans_gauge.set(count)
        logger.debug(f"Updated active scans: count={count}")
    except Exception as e:
        logger.error(f"Failed to update active scans metric: {e}")


def update_db_connections(total: int, used: int, free: int):
    """
    Update database connection pool statistics.
    
    Args:
        total: Total number of connections in pool
        used: Number of connections currently in use
        free: Number of free connections
    """
    try:
        db_connections_gauge.labels(state='total').set(total)
        db_connections_gauge.labels(state='used').set(used)
        db_connections_gauge.labels(state='free').set(free)
        logger.debug(f"Updated DB connections: total={total}, used={used}, free={free}")
    except Exception as e:
        logger.error(f"Failed to update DB connections metric: {e}")


def update_cache_hit_rate(hit_rate: float):
    """
    Update cache hit rate.
    
    Args:
        hit_rate: Cache hit rate as a float between 0.0 and 1.0
    """
    try:
        # Ensure hit_rate is between 0 and 1
        hit_rate = max(0.0, min(1.0, hit_rate))
        cache_hit_rate_gauge.set(hit_rate)
        logger.debug(f"Updated cache hit rate: {hit_rate:.3f}")
    except Exception as e:
        logger.error(f"Failed to update cache hit rate metric: {e}")


def _normalize_endpoint(endpoint: str) -> str:
    """
    Normalize endpoint path by replacing UUIDs and IDs with placeholders.
    
    This prevents high cardinality in metrics by grouping similar endpoints.
    
    Args:
        endpoint: Raw endpoint path
        
    Returns:
        Normalized endpoint path
    """
    import re
    
    # Replace UUIDs with {id}
    endpoint = re.sub(
        r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
        '/{id}',
        endpoint,
        flags=re.IGNORECASE
    )
    
    # Replace numeric IDs with {id}
    endpoint = re.sub(r'/\d+', '/{id}', endpoint)
    
    # Remove query parameters
    endpoint = endpoint.split('?')[0]
    
    return endpoint


def get_metrics_text() -> bytes:
    """
    Get Prometheus metrics in text format.
    
    Returns:
        Metrics in Prometheus text format
    """
    return generate_latest(metrics_registry)


def get_metrics_content_type() -> str:
    """
    Get the content type for Prometheus metrics.
    
    Returns:
        Content type string
    """
    return CONTENT_TYPE_LATEST


# ============================================================================
# Initialization
# ============================================================================

logger.info("Prometheus metrics initialized")
