"""
Monitoring and observability module.
"""

from api.monitoring.metrics import (
    metrics_registry,
    scan_counter,
    scan_duration_histogram,
    active_scans_gauge,
    api_request_counter,
    api_latency_histogram,
    db_connections_gauge,
    cache_hit_rate_gauge,
    record_scan_started,
    record_scan_completed,
    record_scan_failed,
    record_api_request,
    update_active_scans,
    update_db_connections,
    update_cache_hit_rate
)

__all__ = [
    'metrics_registry',
    'scan_counter',
    'scan_duration_histogram',
    'active_scans_gauge',
    'api_request_counter',
    'api_latency_histogram',
    'db_connections_gauge',
    'cache_hit_rate_gauge',
    'record_scan_started',
    'record_scan_completed',
    'record_scan_failed',
    'record_api_request',
    'update_active_scans',
    'update_db_connections',
    'update_cache_hit_rate'
]
