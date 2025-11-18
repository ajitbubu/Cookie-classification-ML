# Monitoring and Observability

This document describes the monitoring and observability features implemented in the Dynamic Cookie Scanning Service (DCS) platform.

## Overview

The DCS platform includes comprehensive monitoring and observability features:

1. **Prometheus Metrics** - For monitoring system performance and health
2. **Health Checks** - For service health monitoring and orchestration
3. **Structured Logging** - For detailed, searchable logs with context
4. **Error Tracking** - Optional Sentry integration for error monitoring

## 1. Prometheus Metrics

### Available Metrics

The platform exposes the following Prometheus metrics:

#### Scan Metrics

- `dcs_scans_total` (Counter) - Total number of scans by mode and status
  - Labels: `scan_mode` (quick, deep, scheduled, realtime), `status` (started, completed, failed)
  
- `dcs_scan_duration_seconds` (Histogram) - Scan duration in seconds
  - Labels: `scan_mode`
  - Buckets: 10s, 30s, 60s, 120s, 300s, 600s, 1800s, 3600s

- `dcs_active_scans` (Gauge) - Number of currently active scans

#### API Metrics

- `dcs_api_requests_total` (Counter) - Total API requests by endpoint, method, and status
  - Labels: `endpoint`, `method`, `status`
  
- `dcs_api_latency_seconds` (Histogram) - API request latency in seconds
  - Labels: `endpoint`
  - Buckets: 10ms, 50ms, 100ms, 250ms, 500ms, 1s, 2.5s, 5s, 10s

#### Database Metrics

- `dcs_db_connections` (Gauge) - Database connection pool statistics
  - Labels: `state` (total, used, free)

#### Cache Metrics

- `dcs_cache_hit_rate` (Gauge) - Cache hit rate (0.0 to 1.0)

### Accessing Metrics

#### Prometheus Format

The metrics are available in Prometheus text format at:

```
GET /api/v1/metrics
```

This endpoint is designed to be scraped by Prometheus. Configure your Prometheus server:

```yaml
scrape_configs:
  - job_name: 'dcs-api'
    scrape_interval: 15s
    static_configs:
      - targets: ['api.example.com:8000']
    metrics_path: '/api/v1/metrics'
```

#### JSON Summary

For human-readable metrics, use:

```
GET /api/v1/metrics/summary
```

This returns metrics in JSON format including database stats, cache stats, and scan counts.

### Recording Metrics

Metrics are automatically recorded by the `MetricsMiddleware` for API requests. For scan metrics, use the helper functions:

```python
from api.monitoring.metrics import (
    record_scan_started,
    record_scan_completed,
    record_scan_failed,
    update_active_scans
)

# Record scan start
record_scan_started(scan_mode='quick')

# Update active scans count
update_active_scans(5)

# Record scan completion
record_scan_completed(scan_mode='quick', duration_seconds=45.2)

# Record scan failure
record_scan_failed(scan_mode='deep', duration_seconds=120.5)
```

## 2. Health Checks

### Endpoints

#### Comprehensive Health Check

```
GET /api/v1/health
```

Returns detailed health status of all components:

```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00Z",
  "version": "2.0.0",
  "components": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful",
      "details": {
        "pool_size": 10,
        "pool_free": 7,
        "pool_used": 3
      }
    },
    "redis": {
      "status": "healthy",
      "message": "Redis connection successful",
      "details": {
        "redis_version": "7.0.0",
        "uptime_seconds": 86400
      }
    },
    "browser": {
      "status": "healthy",
      "message": "Browser engine available"
    },
    "scheduler": {
      "status": "healthy",
      "message": "Scheduler service operational"
    }
  }
}
```

Status codes:
- `200` - System is healthy or degraded
- `503` - System is unhealthy (critical components down)

#### Readiness Check

```
GET /api/v1/ready
```

Lightweight check for Kubernetes/container orchestration. Returns 200 if ready to accept traffic.

#### Liveness Check

```
GET /api/v1/live
```

Very lightweight check with no external dependencies. Returns 200 if the service process is alive.

### Kubernetes Configuration

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: dcs-api
spec:
  containers:
  - name: api
    image: dcs-api:2.0.0
    livenessProbe:
      httpGet:
        path: /api/v1/live
        port: 8000
      initialDelaySeconds: 10
      periodSeconds: 30
    readinessProbe:
      httpGet:
        path: /api/v1/ready
        port: 8000
      initialDelaySeconds: 5
      periodSeconds: 10
```

## 3. Structured Logging

### Configuration

Structured logging is configured using `structlog` and provides JSON-formatted logs with contextual information.

Configuration in `core/logging_config.py`:

```python
from core.logging_config import configure_structlog

configure_structlog(
    log_level='INFO',
    json_logs=True,
    development_mode=False
)
```

### Log Format

Logs are output in JSON format with the following fields:

```json
{
  "event": "request_completed",
  "level": "info",
  "timestamp": "2025-01-15T10:30:00.123456Z",
  "app": "dynamic-cookie-scanner",
  "version": "2.0.0",
  "request_id": "abc123",
  "user_id": "user456",
  "method": "POST",
  "path": "/api/v1/scans",
  "status_code": 201,
  "filename": "main.py",
  "lineno": 42,
  "func_name": "create_scan"
}
```

### Using Structured Logging

```python
from core.logging_config import get_logger, bind_context

# Get logger
logger = get_logger(__name__)

# Bind context (automatically included in all logs)
bind_context(request_id="abc123", user_id="user456")

# Log with structured data
logger.info("scan_started", scan_id="scan789", domain="example.com")
logger.error("scan_failed", scan_id="scan789", error="timeout", duration=120.5)

# Clear context when done
from core.logging_config import clear_context
clear_context()
```

### Request Context

The `RequestContextMiddleware` automatically adds the following context to all logs within a request:

- `request_id` - Unique identifier for the request
- `user_id` - User ID from authentication (if available)
- `method` - HTTP method
- `path` - Request path

### Log Levels

- `DEBUG` - Detailed information for debugging
- `INFO` - General informational messages
- `WARNING` - Warning messages for potentially harmful situations
- `ERROR` - Error messages for failures
- `CRITICAL` - Critical errors that may cause system failure

### Log Aggregation

Structured JSON logs can be easily ingested by log aggregation tools:

#### ELK Stack (Elasticsearch, Logstash, Kibana)

```conf
# Logstash configuration
input {
  file {
    path => "/var/log/dcs/*.log"
    codec => json
  }
}

filter {
  # Logs are already in JSON format
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "dcs-logs-%{+YYYY.MM.dd}"
  }
}
```

#### Datadog

```python
# Add Datadog handler
import logging
from datadog import initialize, statsd

# Configure Datadog
initialize(api_key='YOUR_API_KEY')

# Logs will be automatically sent to Datadog
```

## 4. Error Tracking with Sentry

### Configuration

Sentry integration is optional and configured via environment variables:

```bash
SENTRY_DSN=https://xxx@sentry.io/xxx
```

### Initialization

Sentry is automatically initialized in `api/main.py` if a DSN is configured:

```python
from core.sentry_config import init_sentry

init_sentry(
    dsn=config.monitoring.sentry_dsn,
    environment=config.environment,
    release='2.0.0',
    traces_sample_rate=0.1,
    enable_tracing=True
)
```

### Features

#### Automatic Error Capture

All unhandled exceptions are automatically captured and sent to Sentry.

#### Manual Error Capture

```python
from core.sentry_config import capture_exception, capture_message

try:
    # ... code that might fail
    pass
except Exception as e:
    capture_exception(
        e,
        tags={'scan_mode': 'quick'},
        extras={'domain': 'example.com'}
    )
```

#### Breadcrumbs

Add breadcrumbs for debugging context:

```python
from core.sentry_config import add_breadcrumb

add_breadcrumb(
    "Starting scan",
    category="scan",
    level="info",
    data={"domain": "example.com", "scan_mode": "quick"}
)
```

#### User Context

Set user context for better error tracking:

```python
from core.sentry_config import set_user_context

set_user_context(
    user_id="user123",
    email="user@example.com",
    username="john_doe"
)
```

#### Custom Context

Add custom context to errors:

```python
from core.sentry_config import set_context

set_context("scan", {
    "scan_id": "scan789",
    "domain": "example.com",
    "mode": "quick"
})
```

### Performance Monitoring

Sentry automatically tracks:
- API endpoint performance
- Database query performance
- Redis operations
- Async task performance

Configure sampling rate in production:

```python
init_sentry(
    dsn=dsn,
    traces_sample_rate=0.1,  # Sample 10% of transactions
    profiles_sample_rate=0.1  # Profile 10% of transactions
)
```

## Best Practices

### 1. Metrics

- Use counters for events that only increase (requests, errors)
- Use gauges for values that can go up and down (active scans, connections)
- Use histograms for distributions (latency, duration)
- Keep label cardinality low (avoid user IDs, scan IDs in labels)

### 2. Logging

- Use structured logging with meaningful event names
- Include relevant context (IDs, domains, modes)
- Use appropriate log levels
- Avoid logging sensitive data (passwords, API keys, cookie values)
- Use request_id to trace requests across services

### 3. Error Tracking

- Add breadcrumbs before critical operations
- Set user context for authenticated requests
- Use tags for filtering (environment, scan_mode, etc.)
- Add custom context for debugging
- Filter out expected errors (404s, validation errors)

### 4. Alerting

Set up alerts in Prometheus/Grafana:

```yaml
groups:
  - name: dcs_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(dcs_api_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
          
      - alert: SlowScans
        expr: histogram_quantile(0.95, dcs_scan_duration_seconds) > 300
        for: 10m
        annotations:
          summary: "Scans are taking too long"
          
      - alert: DatabaseConnectionPoolExhausted
        expr: dcs_db_connections{state="free"} < 2
        for: 5m
        annotations:
          summary: "Database connection pool nearly exhausted"
```

## Troubleshooting

### Metrics Not Appearing

1. Check that `MetricsMiddleware` is registered in `api/main.py`
2. Verify Prometheus is scraping the correct endpoint
3. Check for errors in application logs

### Logs Not Structured

1. Verify `configure_structlog()` is called before any logging
2. Check that `json_logs=True` in configuration
3. Ensure using `get_logger()` from `core.logging_config`

### Sentry Not Capturing Errors

1. Verify `SENTRY_DSN` is set correctly
2. Check Sentry initialization logs
3. Test with `capture_message()` to verify connection
4. Check Sentry project settings and rate limits

## Example Dashboard

### Grafana Dashboard

Import this dashboard JSON to visualize DCS metrics:

```json
{
  "dashboard": {
    "title": "DCS Monitoring",
    "panels": [
      {
        "title": "API Request Rate",
        "targets": [
          {
            "expr": "rate(dcs_api_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Scan Duration (p95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, dcs_scan_duration_seconds)"
          }
        ]
      },
      {
        "title": "Active Scans",
        "targets": [
          {
            "expr": "dcs_active_scans"
          }
        ]
      },
      {
        "title": "Database Connections",
        "targets": [
          {
            "expr": "dcs_db_connections"
          }
        ]
      }
    ]
  }
}
```

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Structlog Documentation](https://www.structlog.org/)
- [Sentry Documentation](https://docs.sentry.io/)
- [FastAPI Monitoring](https://fastapi.tiangolo.com/advanced/monitoring/)
