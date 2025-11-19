# API Endpoints Reference - Task 6

## Analytics Endpoints

### Get Report
```
GET /api/v1/analytics/reports/{scan_id}
```
**Description:** Retrieve or generate a compliance report for a scan  
**Auth:** Required (scope: `analytics:read`)  
**Query Parameters:**
- `format` (optional): Report format (pdf, html, json) - default: json

**Response:** Report object with generated report data

---

### Generate Custom Report
```
POST /api/v1/analytics/reports
```
**Description:** Generate a new compliance report  
**Auth:** Required (scope: `analytics:write`)  
**Request Body:**
```json
{
  "scan_id": "uuid",
  "format": "pdf|html|json"
}
```
**Response:** Report object with file path and metadata

---

### Get Trend Data
```
GET /api/v1/analytics/trends
```
**Description:** Get historical trend data for a domain  
**Auth:** Required (scope: `analytics:read`)  
**Query Parameters:**
- `domain` (required): Domain to analyze
- `metric` (optional): Metric to analyze - default: total_cookies
  - Options: total_cookies, compliance_score, third_party_ratio, first_party_ratio, cookies_after_consent, cookies_before_consent
- `days` (optional): Number of days to look back (1-365) - default: 30

**Response:** TrendData object with time series data

---

### Get Metrics Summary
```
GET /api/v1/analytics/metrics
```
**Description:** Get aggregated metrics summary for recent scans  
**Auth:** Required (scope: `analytics:read`)  
**Query Parameters:**
- `domain` (optional): Filter by domain
- `days` (optional): Number of days to look back (1-365) - default: 7

**Response:**
```json
{
  "total_scans": 100,
  "domains_scanned": 10,
  "total_cookies_found": 5000,
  "average_compliance_score": 75.5,
  "average_scan_duration": 45.2,
  "cookie_distribution": {
    "Necessary": 1000,
    "Analytics": 2000,
    "Marketing": 2000
  },
  "time_range": {
    "start": "2024-01-01T00:00:00",
    "end": "2024-01-08T00:00:00"
  }
}
```

---

## Profile Endpoints

### List Profiles
```
GET /api/v1/profiles
```
**Description:** List all scan profiles  
**Auth:** Required (scope: `profiles:read`)  
**Query Parameters:**
- `scan_mode` (optional): Filter by scan mode
- `limit` (optional): Max results (1-500) - default: 100
- `offset` (optional): Pagination offset - default: 0

**Response:** Array of ScanProfile objects

---

### Create Profile
```
POST /api/v1/profiles
```
**Description:** Create a new scan profile  
**Auth:** Required (scope: `profiles:write`)  
**Request Body:** ScanProfileCreate object

**Response:** Created ScanProfile object

---

### Get Profile
```
GET /api/v1/profiles/{profile_id}
```
**Description:** Get a specific scan profile  
**Auth:** Required (scope: `profiles:read`)

**Response:** ScanProfile object

---

### Update Profile
```
PUT /api/v1/profiles/{profile_id}
```
**Description:** Update a scan profile  
**Auth:** Required (scope: `profiles:write`)  
**Request Body:** ScanProfileUpdate object

**Response:** Updated ScanProfile object

---

### Delete Profile
```
DELETE /api/v1/profiles/{profile_id}
```
**Description:** Delete a scan profile  
**Auth:** Required (scope: `profiles:write`)

**Response:** 204 No Content

---

## Notification Endpoints

### Get Preferences
```
GET /api/v1/notifications/preferences
```
**Description:** Get notification preferences for authenticated user  
**Auth:** Required

**Response:** NotificationPreferences object

---

### Update Preferences
```
PUT /api/v1/notifications/preferences
```
**Description:** Update notification preferences  
**Auth:** Required  
**Request Body:**
```json
{
  "enabled_events": ["scan.completed", "scan.failed"],
  "enabled_channels": ["email", "slack"],
  "email_address": "user@example.com",
  "slack_webhook_url": "https://hooks.slack.com/...",
  "quiet_hours": {
    "start_hour": 22,
    "end_hour": 8
  }
}
```

**Response:** Updated NotificationPreferences object

---

### Get Notification History
```
GET /api/v1/notifications/history
```
**Description:** Get notification history for authenticated user  
**Auth:** Required  
**Query Parameters:**
- `limit` (optional): Max results (1-500) - default: 50
- `offset` (optional): Pagination offset - default: 0
- `event` (optional): Filter by event type
- `status` (optional): Filter by status (pending, sent, failed)

**Response:** Array of Notification objects

---

### Get Supported Events
```
GET /api/v1/notifications/events
```
**Description:** Get list of supported notification event types  
**Auth:** Required

**Response:** Array of event type strings

---

### Get Supported Channels
```
GET /api/v1/notifications/channels
```
**Description:** Get list of supported notification channels  
**Auth:** Required

**Response:** Array of channel type strings

---

## Health & Monitoring Endpoints

### Health Check
```
GET /api/v1/health
```
**Description:** Comprehensive health check with component status  
**Auth:** Not required

**Response:**
```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2024-01-01T00:00:00",
  "version": "2.0.0",
  "components": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful",
      "details": {
        "pool_size": 10,
        "pool_free": 8,
        "pool_used": 2
      }
    },
    "redis": {
      "status": "healthy",
      "message": "Redis connection successful"
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

**Status Codes:**
- 200: System is healthy or degraded
- 503: System is unhealthy

---

### System Metrics
```
GET /api/v1/metrics
```
**Description:** Get system metrics for monitoring  
**Auth:** Not required

**Response:**
```json
{
  "timestamp": "2024-01-01T00:00:00",
  "api": {},
  "database": {
    "pool_size": 10,
    "pool_free": 8,
    "pool_used": 2
  },
  "cache": {
    "total_connections_received": 1000,
    "total_commands_processed": 5000,
    "keyspace_hits": 4000,
    "keyspace_misses": 1000,
    "hit_rate": 0.8
  },
  "scans": {
    "total": 100,
    "active": 5,
    "failed": 2
  }
}
```

---

### Readiness Check
```
GET /api/v1/ready
```
**Description:** Kubernetes readiness probe  
**Auth:** Not required

**Response:**
```json
{
  "ready": true,
  "timestamp": "2024-01-01T00:00:00"
}
```

**Status Codes:**
- 200: Service is ready
- 503: Service is not ready

---

### Liveness Check
```
GET /api/v1/live
```
**Description:** Kubernetes liveness probe  
**Auth:** Not required

**Response:**
```json
{
  "alive": true,
  "timestamp": "2024-01-01T00:00:00"
}
```

---

## Authentication

All protected endpoints require authentication via:

### JWT Bearer Token
```
Authorization: Bearer <token>
```

### API Key
```
X-API-Key: <key>
```

## Rate Limiting

All endpoints are rate-limited. Response headers include:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset timestamp

## Error Responses

All errors follow this format:
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

## Common Status Codes

- `200 OK`: Successful request
- `201 Created`: Resource created
- `204 No Content`: Successful deletion
- `400 Bad Request`: Invalid request
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service unhealthy
