# Prometheus Metrics Implementation Guide

## Overview

Task 11.1 has been successfully implemented. The Dynamic Cookie Scanning Service now exposes comprehensive Prometheus metrics for monitoring and observability.

## Implementation Details

### 1. Metrics Module (`api/monitoring/metrics.py`)

The metrics module defines all Prometheus metrics using the `prometheus_client` library:

#### Scan Metrics
- **`dcs_scans_total`** (Counter): Total number of scans by mode and status
  - Labels: `scan_mode` (quick, deep, scheduled, realtime), `status` (started, completed, failed)
- **`dcs_scan_duration_seconds`** (Histogram): Scan duration in seconds
  - Labels: `scan_mode`
  - Buckets: 10s, 30s, 60s, 120s, 300s, 600s, 1800s, 3600s
- **`dcs_active_scans`** (Gauge): Number of currently active scans

#### API Metrics
- **`dcs_api_requests_total`** (Counter): Total API requests by endpoint, method, and status
  - Labels: `endpoint`, `method`, `status`
- **`dcs_api_latency_seconds`** (Histogram): API request latency in seconds
  - Labels: `endpoint`
  - Buckets: 10ms, 50ms, 100ms, 250ms, 500ms, 1s, 2.5s, 5s, 10s

#### Database Metrics
- **`dcs_db_connections`** (Gauge): Database connection pool statistics
  - Labels: `state` (total, used, free)

#### Cache Metrics
- **`dcs_cache_hit_rate`** (Gauge): Cache hit rate (0.0 to 1.0)

### 2. Helper Functions

The module provides convenient helper functions for recording metrics:

```python
from api.monitoring.metrics import (
    record_scan_started,
    record_scan_completed,
    record_scan_failed,
    record_api_request,
    update_active_scans,
    update_db_connections,
    update_cache_hit_rate
)

# Record scan metrics
record_scan_started("quick")
record_scan_completed("quick", duration_seconds=45.5)
record_scan_failed("deep", duration_seconds=120.0)
update_active_scans(5)

# Record API metrics (done automatically by middleware)
record_api_request("/api/v1/scans", "POST", 201, 0.123)

# Update database metrics
update_db_connections(total=10, used=7, free=3)

# Update cache metrics
update_cache_hit_rate(0.85)
```

### 3. Metrics Endpoint (`/api/v1/metrics`)

The metrics endpoint is implemented in `api/routers/health.py` and exposes metrics in Prometheus text format:

```bash
# Access metrics endpoint
curl http://localhost:8000/api/v1/metrics

# Example output:
# HELP dcs_scans_total Total number of scans by mode and status
# TYPE dcs_scans_total counter
dcs_scans_total{scan_mode="quick",status="completed"} 42.0
dcs_scans_total{scan_mode="deep",status="completed"} 15.0

# HELP dcs_scan_duration_seconds Scan duration in seconds
# TYPE dcs_scan_duration_seconds histogram
dcs_scan_duration_seconds_bucket{le="60.0",scan_mode="quick"} 38.0
dcs_scan_duration_seconds_sum{scan_mode="quick"} 1823.5
dcs_scan_duration_seconds_count{scan_mode="quick"} 42.0
```

### 4. Automatic API Tracking

The `MetricsMiddleware` (`api/middleware/metrics.py`) automatically tracks all API requests:

- Records request count by endpoint, method, and status code
- Measures request latency
- Normalizes endpoints to prevent high cardinality (replaces UUIDs with `{id}`)
- Excludes health and metrics endpoints from tracking to reduce noise

### 5. Integration with Main App

The metrics system is fully integrated into the FastAPI application (`api/main.py`):

```python
# Middleware is added automatically
app.add_middleware(MetricsMiddleware)

# Health router (containing metrics endpoint) is registered
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
```

## Usage

### For Developers

When implementing scan functionality, use the helper functions to record metrics:

```python
from api.monitoring.metrics import (
    record_scan_started,
    record_scan_completed,
    update_active_scans
)

async def execute_scan(scan_id: str, scan_mode: str):
    # Record scan start
    record_scan_started(scan_mode)
    update_active_scans(get_active_count() + 1)
    
    start_time = time.time()
    try:
        # Execute scan
        result = await perform_scan()
        
        # Record success
        duration = time.time() - start_time
        record_scan_completed(scan_mode, duration)
        
    except Exception as e:
        # Record failure
        duration = time.time() - start_time
        record_scan_failed(scan_mode, duration)
        raise
    finally:
        update_active_scans(get_active_count() - 1)
```

### For DevOps/SRE

#### Prometheus Configuration

Add the following to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'dcs-api'
    scrape_interval: 15s
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/api/v1/metrics'
```

#### Example Queries

```promql
# Scan success rate
rate(dcs_scans_total{status="completed"}[5m]) / rate(dcs_scans_total[5m])

# Average scan duration by mode
rate(dcs_scan_duration_seconds_sum[5m]) / rate(dcs_scan_duration_seconds_count[5m])

# API request rate by endpoint
rate(dcs_api_requests_total[5m])

# API p95 latency
histogram_quantile(0.95, rate(dcs_api_latency_seconds_bucket[5m]))

# Database connection pool utilization
dcs_db_connections{state="used"} / dcs_db_connections{state="total"}

# Cache hit rate
dcs_cache_hit_rate
```

#### Grafana Dashboard

Create dashboards with panels for:
1. Scan throughput and success rate
2. Active scans over time
3. API request rate and latency
4. Database connection pool usage
5. Cache hit rate

## Testing

Verify the metrics endpoint is working:

```bash
# Check metrics endpoint
curl http://localhost:8000/api/v1/metrics

# Check health endpoint (includes component status)
curl http://localhost:8000/api/v1/health

# Check metrics summary (JSON format)
curl http://localhost:8000/api/v1/metrics/summary
```

## Requirements Satisfied

This implementation satisfies **Requirement 10.3** from the requirements document:

> THE DCS SHALL emit metrics including scan duration, success rate, and API response times

All required metrics are implemented and exposed via the `/api/v1/metrics` endpoint in Prometheus format.

## Related Files

- `api/monitoring/metrics.py` - Metrics definitions and helper functions
- `api/routers/health.py` - Health and metrics endpoints
- `api/middleware/metrics.py` - Automatic API request tracking
- `api/main.py` - Application setup with middleware integration
- `requirements.txt` - Includes `prometheus-client>=0.17.0`

## Next Steps

1. Configure Prometheus to scrape the metrics endpoint
2. Set up Grafana dashboards for visualization
3. Configure alerting rules for critical metrics
4. Integrate metrics recording into scan service implementation
5. Monitor and tune metric collection performance
