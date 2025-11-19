# Cookie Scanner Platform - Architecture Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Principles](#architecture-principles)
3. [Component Architecture](#component-architecture)
4. [Data Flow](#data-flow)
5. [Database Schema](#database-schema)
6. [API Design](#api-design)
7. [Security Architecture](#security-architecture)
8. [Performance Optimizations](#performance-optimizations)
9. [Deployment Architecture](#deployment-architecture)
10. [Design Decisions](#design-decisions)

---

## System Overview

The Cookie Scanner Platform is a comprehensive cookie compliance and analytics system that enables organizations to:
- Scan websites for cookies and tracking technologies
- Categorize cookies according to compliance frameworks (GDPR, CCPA)
- Generate compliance reports and analytics
- Monitor cookie usage over time
- Receive notifications about compliance issues

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Web Dashboard                            │
│                    (Next.js + React + TypeScript)                │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTPS/REST API
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                       API Gateway                                │
│              (FastAPI + Auth + Rate Limiting)                    │
└─┬───────────┬──────────┬──────────┬──────────┬─────────────────┘
  │           │          │          │          │
  ▼           ▼          ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────────┐
│ Scan   │ │Analytics│ │Notif.  │ │Config  │ │ Scheduler    │
│ Service│ │ Module │ │Service │ │Manager │ │ Service      │
└───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └──────┬───────┘
    │          │          │          │              │
    └──────────┴──────────┴──────────┴──────────────┘
                         │
                         ▼
    ┌────────────────────────────────────────────┐
    │         Data Layer                         │
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
    │  │PostgreSQL│  │  Redis   │  │  Celery  │ │
    │  │   DB     │  │  Cache   │  │  Queue   │ │
    │  └──────────┘  └──────────┘  └──────────┘ │
    └────────────────────────────────────────────┘
```

### Technology Stack

**Backend:**
- Python 3.11+
- FastAPI (API framework)
- Playwright (browser automation)
- PostgreSQL (primary database)
- Redis (caching and rate limiting)
- Celery (async task processing)
- APScheduler (job scheduling)
- Pydantic (data validation)

**Frontend:**
- Next.js 14+ (React framework)
- TypeScript
- Tailwind CSS
- Zustand (state management)
- Chart.js/Recharts (data visualization)

**Infrastructure:**
- Docker & Docker Compose
- Nginx (reverse proxy)
- Prometheus (metrics)
- Sentry (error tracking)

---

## Architecture Principles

### 1. Modularity
Components are loosely coupled with clear interfaces, enabling independent development and testing.

### 2. Scalability
Horizontal scaling support for API servers and scan workers. Stateless design where possible.

### 3. Observability
Comprehensive logging, metrics, and health checks throughout the system.

### 4. Security
Authentication, authorization, encryption, and audit logging at every layer.

### 5. Performance
Caching, async processing, connection pooling, and query optimization.

### 6. Backward Compatibility
Maintain existing API contracts and data formats during upgrades.

---

## Component Architecture

### 1. API Gateway Layer

**Location:** `api/`

**Responsibilities:**
- Request routing and validation
- Authentication and authorization
- Rate limiting
- Request/response transformation
- OpenAPI documentation generation

**Key Files:**
- `api/main.py` - FastAPI application entry point
- `api/routers/` - API endpoint definitions
- `api/auth/` - Authentication and authorization
- `api/middleware/` - Request/response middleware
- `api/errors/` - Error handling

**Design Pattern:** Layered architecture with middleware chain

### 2. Scan Service

**Location:** `services/scan_service.py`, `cookie_scanner.py`

**Responsibilities:**
- Execute scans (quick, deep, scheduled, real-time)
- Manage browser instances via Playwright
- Collect cookies and storage data
- Categorize cookies using multi-tier system
- Store scan results in database

**Key Components:**
- `ScanService` - Main service class
- `BrowserPool` - Browser instance management
- `ParallelScanManager` - Concurrent domain scanning
- Cookie categorization (DB → IAB GVL → Rules → Fallback)

**Design Pattern:** Service layer with dependency injection

### 3. Analytics Module

**Location:** `analytics/`

**Responsibilities:**
- Generate compliance reports (PDF, HTML, JSON)
- Calculate metrics and KPIs
- Track historical trends
- Perform comparative analysis
- Detect anomalies

**Key Files:**
- `analytics/report_generator.py` - Report creation
- `analytics/metrics_calculator.py` - Metric computation
- `analytics/trend_analyzer.py` - Historical analysis
- `analytics/anomaly_detector.py` - Anomaly detection
- `analytics/comparison_generator.py` - Comparison reports

**Design Pattern:** Strategy pattern for different report types

### 4. Notification Service

**Location:** `services/notification_*.py`

**Responsibilities:**
- Multi-channel notification delivery (email, webhook, Slack)
- Event-driven notification triggers
- User preference management
- Retry logic with exponential backoff

**Key Files:**
- `services/notification_service.py` - Main service
- `services/notification_channels.py` - Channel implementations
- `services/notification_templates.py` - Message templates
- `services/notification_tasks.py` - Celery tasks
- `services/notification_retry.py` - Retry logic

**Design Pattern:** Observer pattern for event handling

### 5. Scheduler Service

**Location:** `services/enhanced_scheduler.py`, `schedule_manager.py`

**Responsibilities:**
- Job scheduling and execution
- Distributed job coordination via Redis locks
- Missed job handling
- Job history and audit trail

**Key Files:**
- `services/enhanced_scheduler.py` - APScheduler integration
- `services/scheduled_scan_executor.py` - Scan execution
- `services/distributed_lock.py` - Redis-based locking
- `services/schedule_repository.py` - Database operations

**Design Pattern:** Repository pattern for data access

### 6. Configuration Manager

**Location:** `core/config.py`, `config.py`

**Responsibilities:**
- Centralized configuration management
- Environment-based config loading
- Configuration validation
- Secret management

**Design Pattern:** Singleton pattern for global config

### 7. Dashboard (Frontend)

**Location:** `dashboard/`

**Responsibilities:**
- User interface for scan management
- Real-time scan progress monitoring
- Interactive analytics visualization
- Configuration management UI

**Key Directories:**
- `dashboard/app/` - Next.js pages and layouts
- `dashboard/components/` - React components
- `dashboard/lib/` - API client and utilities
- `dashboard/store/` - State management
- `dashboard/hooks/` - Custom React hooks

**Design Pattern:** Component-based architecture with hooks

---

## Data Flow

### Scan Execution Flow

```
1. User Request (Dashboard/API)
   ↓
2. API Gateway (Authentication + Validation)
   ↓
3. Scan Service (Create scan record)
   ↓
4. Celery Task Queue (Async execution)
   ↓
5. Scan Worker
   - Launch browser
   - Navigate pages
   - Collect cookies
   - Categorize cookies
   ↓
6. Database (Store results)
   ↓
7. Notification Service (Send alerts)
   ↓
8. Cache (Store for quick retrieval)
   ↓
9. Response to User
```

### Real-Time Scan Flow

```
1. User initiates scan with real-time mode
   ↓
2. API creates scan and returns scan_id
   ↓
3. Dashboard opens SSE connection to /scans/{scan_id}/stream
   ↓
4. Scan worker sends progress updates via SSE
   - Page visited
   - Cookies found
   - Progress percentage
   ↓
5. Dashboard updates UI in real-time
   ↓
6. Scan completes, final results sent
```

### Scheduled Scan Flow

```
1. APScheduler triggers job at scheduled time
   ↓
2. Scheduler acquires distributed lock (Redis)
   ↓
3. If lock acquired, execute scan
   ↓
4. Scan Service performs scan
   ↓
5. Results stored in database
   ↓
6. Job history updated
   ↓
7. Notification sent to subscribers
   ↓
8. Lock released
```

---

## Database Schema

### Core Tables

#### scan_results
Stores scan execution results and metadata.

```sql
CREATE TABLE scan_results (
    scan_id UUID PRIMARY KEY,
    domain_config_id UUID NOT NULL,
    domain VARCHAR(255) NOT NULL,
    scan_mode VARCHAR(50) NOT NULL,
    timestamp_utc TIMESTAMP NOT NULL,
    status VARCHAR(50) NOT NULL,
    duration_seconds FLOAT,
    total_cookies INT,
    page_count INT,
    error TEXT,
    params JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_domain_config (domain_config_id),
    INDEX idx_timestamp (timestamp_utc),
    INDEX idx_status (status)
);
```

#### cookies
Stores individual cookie data (normalized).

```sql
CREATE TABLE cookies (
    cookie_id UUID PRIMARY KEY,
    scan_id UUID REFERENCES scan_results(scan_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    path VARCHAR(500),
    hashed_value VARCHAR(64),
    category VARCHAR(50),
    vendor VARCHAR(255),
    cookie_type VARCHAR(50),
    set_after_accept BOOLEAN,
    metadata JSONB,
    INDEX idx_scan (scan_id),
    INDEX idx_name (name),
    INDEX idx_category (category)
);
```

#### schedules
Stores recurring scan schedules.

```sql
CREATE TABLE schedules (
    schedule_id UUID PRIMARY KEY,
    domain_config_id UUID NOT NULL,
    domain VARCHAR(255) NOT NULL,
    profile_id UUID,
    frequency VARCHAR(50) NOT NULL,
    time_config JSONB NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    next_run TIMESTAMP,
    last_run TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_next_run (next_run),
    INDEX idx_enabled (enabled)
);
```

#### users
Stores user accounts and authentication data.

```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### api_keys
Stores API keys for programmatic access.

```sql
CREATE TABLE api_keys (
    api_key_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    key_hash VARCHAR(64) UNIQUE NOT NULL,
    scopes JSONB,
    rate_limit INT DEFAULT 100,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);
```

### Relationships

- `scan_results` 1:N `cookies` (one scan has many cookies)
- `users` 1:N `api_keys` (one user has many API keys)
- `scan_profiles` 1:N `schedules` (one profile used by many schedules)
- `scan_results` 1:N `reports` (one scan can have multiple reports)

### Redis Cache Structure

```
# Rate limiting
rate_limit:{api_key}:{window} -> counter (TTL: window duration)

# Scan results cache
scan_result:{scan_id} -> JSON (TTL: 5 minutes)

# Analytics cache
analytics:metrics:{domain}:{date} -> JSON (TTL: 1 hour)
analytics:trends:{domain}:{metric} -> JSON (TTL: 1 hour)

# Active scans
active_scan:{scan_id} -> status JSON (TTL: 1 hour)

# Distributed locks
lock:schedule:{schedule_id} -> lock token (TTL: 60 seconds)
```

---

## API Design

### RESTful Principles

The API follows REST conventions:
- Resources identified by URIs
- Standard HTTP methods (GET, POST, PUT, DELETE)
- Stateless requests
- JSON request/response bodies
- Standard HTTP status codes

### Endpoint Structure

```
/api/v1/{resource}/{id}/{sub-resource}
```

**Examples:**
- `GET /api/v1/scans` - List scans
- `POST /api/v1/scans` - Create scan
- `GET /api/v1/scans/{scan_id}` - Get scan
- `GET /api/v1/scans/{scan_id}/stream` - Stream scan progress
- `GET /api/v1/analytics/reports/{scan_id}` - Get report

### Authentication

**API Key Authentication:**
```http
Authorization: Bearer {api_key}
```

**JWT Authentication (Dashboard):**
```http
Authorization: Bearer {jwt_token}
```

### Rate Limiting

Rate limits enforced per API key:
- Default: 100 requests/minute
- Premium: 1000 requests/minute
- Headers returned:
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset`

### Error Response Format

```json
{
  "error": {
    "code": "SCAN_TIMEOUT",
    "message": "Page load timeout after 60 seconds",
    "details": {
      "url": "https://example.com",
      "attempt": 3
    },
    "timestamp": "2025-01-15T10:30:00Z",
    "request_id": "req_abc123"
  }
}
```

### Pagination

List endpoints support pagination:

**Request:**
```http
GET /api/v1/scans?page=2&page_size=50
```

**Response:**
```json
{
  "items": [...],
  "total": 250,
  "page": 2,
  "page_size": 50,
  "has_next": true,
  "has_prev": true
}
```

---

## Security Architecture

### Authentication & Authorization

**Three-tier security model:**

1. **API Key Authentication** (External integrations)
   - SHA-256 hashed keys
   - Scoped permissions (read, write, admin)
   - Rate limiting per key
   - Expiration support

2. **JWT Authentication** (Dashboard sessions)
   - Short-lived tokens (1 hour)
   - Refresh token mechanism
   - HTTP-only secure cookies
   - CSRF protection

3. **Role-Based Access Control**
   - Admin: Full system access
   - User: Own resources only
   - Viewer: Read-only access

### Data Protection

**Cookie Value Hashing:**
All cookie values are hashed with SHA-256 before storage to protect sensitive data.

**Encryption at Rest:**
- Database-level encryption for sensitive fields
- Encrypted backups
- Secure credential storage

**Encryption in Transit:**
- HTTPS/TLS for all API endpoints
- WSS for WebSocket connections
- Secure SMTP for email notifications

### Audit Logging

All security-relevant events are logged:
- Authentication attempts (success/failure)
- API key creation/deletion
- Configuration changes
- Data access operations
- Schedule modifications

**Audit Log Structure:**
```python
{
    "timestamp": "2025-01-15T10:30:00Z",
    "user_id": "user_123",
    "action": "scan.create",
    "resource": "scan_456",
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "details": {...}
}
```

### Account Lockout

Protection against brute force attacks:
- Track failed login attempts in Redis
- Lock account after 5 failed attempts within 15 minutes
- Time-based unlock (30 minutes) or admin unlock
- Log all lockout events

---

## Performance Optimizations

### 1. Caching Strategy

**Multi-layer caching:**

**L1: Application Cache (In-memory)**
- Scan profiles
- Configuration
- User sessions

**L2: Redis Cache**
- Scan results (5 min TTL)
- Analytics metrics (1 hour TTL)
- Trend data (1 hour TTL)

**Cache Invalidation:**
- Time-based expiration (TTL)
- Event-based invalidation (new scan → invalidate analytics)
- Manual cache clearing via admin API

### 2. Database Optimizations

**Connection Pooling:**
```python
pool_size=10
max_overflow=20
pool_pre_ping=True
```

**Indexes:**
- `scan_results`: domain_config_id, timestamp_utc, status
- `cookies`: scan_id, name, category
- `schedules`: next_run, enabled

**Query Optimization:**
- Batch inserts for cookies (100 at a time)
- Prepared statements
- Query result caching
- EXPLAIN ANALYZE for slow queries

### 3. Async Processing

**Celery Task Queue:**

Long-running operations executed asynchronously:
- Report generation
- Notification delivery
- Deep scans
- Bulk operations

**Task Priority:**
- High: Real-time scans, critical notifications
- Normal: Scheduled scans, reports
- Low: Analytics computation, cleanup tasks

### 4. Browser Instance Pooling

**BrowserPool:**
- Maintain pool of 5 browser instances
- Reuse instances across scans
- Health checks and automatic replacement
- Reduces browser launch overhead (2-3 seconds per scan)

### 5. Parallel Processing

**Concurrent Scanning:**
- Semaphore-based concurrency control
- Max 10 concurrent domain scans
- Parallel page processing within a scan
- asyncio.gather for parallel operations

---

## Deployment Architecture

### Container Structure

**Services:**
1. **API Service** (3 replicas)
   - FastAPI application
   - Handles HTTP requests
   - Stateless, horizontally scalable

2. **Scanner Workers** (5 replicas)
   - Execute scan tasks
   - Playwright browser automation
   - CPU and memory intensive

3. **Scheduler Service** (1 replica)
   - APScheduler with Redis locks
   - Triggers scheduled scans
   - Single instance with HA failover

4. **Dashboard** (1 replica)
   - Next.js static site
   - Served via Nginx
   - CDN-ready

5. **Celery Workers** (3 replicas)
   - Process async tasks
   - Report generation, notifications
   - Horizontally scalable

6. **PostgreSQL** (1 instance)
   - Primary database
   - Persistent volume
   - Backup strategy

7. **Redis** (1 instance)
   - Cache and message broker
   - Persistent volume
   - Redis Sentinel for HA

### Scaling Strategy

**Horizontal Scaling:**
- API servers: Scale based on request rate (CPU > 70%)
- Scanner workers: Scale based on queue depth (> 50 pending scans)
- Celery workers: Scale based on task backlog (> 100 pending tasks)

**Vertical Scaling:**
- Database: Increase CPU/memory for large datasets
- Redis: Increase memory for cache size

**Load Balancing:**
- Nginx/HAProxy for API servers
- Round-robin for scanner workers
- Redis Sentinel for cache HA

### Health Checks

Each service exposes health endpoint:
```
GET /health
{
  "status": "healthy",
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "browser": "healthy"
  }
}
```

---

## Design Decisions

### 1. Why FastAPI over Flask?

**Decision:** Migrate from Flask to FastAPI

**Rationale:**
- Native async/await support for better performance
- Automatic OpenAPI documentation generation
- Built-in request validation with Pydantic
- Better type hints and IDE support
- Modern Python 3.11+ features

**Trade-offs:**
- Migration effort required
- Team learning curve
- Some Flask extensions not compatible

### 2. Why PostgreSQL over MongoDB?

**Decision:** Use PostgreSQL as primary database

**Rationale:**
- Structured data with clear relationships
- ACID compliance for data integrity
- Excellent query performance with proper indexes
- JSONB support for flexible fields
- Mature ecosystem and tooling

**Trade-offs:**
- Schema migrations required for changes
- Less flexible than document databases
- Vertical scaling limitations

### 3. Why Celery for Async Tasks?

**Decision:** Use Celery with Redis broker

**Rationale:**
- Mature, battle-tested task queue
- Excellent monitoring and debugging tools
- Retry logic and error handling built-in
- Supports task priorities and routing
- Large community and ecosystem

**Trade-offs:**
- Additional infrastructure (Redis broker)
- Complexity in task management
- Serialization overhead

**Alternatives Considered:**
- RQ (simpler but less features)
- Dramatiq (modern but smaller community)
- AWS SQS (vendor lock-in)

### 4. Why Next.js for Dashboard?

**Decision:** Use Next.js with React and TypeScript

**Rationale:**
- Server-side rendering for better SEO and performance
- File-based routing simplifies development
- Built-in API routes for BFF pattern
- Excellent developer experience
- Strong TypeScript support

**Trade-offs:**
- Larger bundle size than plain React
- Learning curve for Next.js-specific features
- Deployment complexity (Node.js server required)

### 5. Why Multi-Tier Cookie Categorization?

**Decision:** Implement DB → IAB GVL → Rules → Fallback cascade

**Rationale:**
- Database overrides allow manual corrections
- IAB GVL provides industry-standard categorization
- Local rules handle custom/unknown cookies
- Fallback ensures all cookies are categorized
- Flexible and extensible

**Trade-offs:**
- Complexity in categorization logic
- Multiple data sources to maintain
- Performance overhead (mitigated by caching)

### 6. Why Redis for Rate Limiting?

**Decision:** Use Redis for distributed rate limiting

**Rationale:**
- Fast in-memory operations (< 1ms)
- Atomic increment operations
- TTL support for sliding windows
- Distributed across API instances
- Simple implementation

**Trade-offs:**
- Additional infrastructure dependency
- Data loss on Redis failure (acceptable for rate limits)
- Memory usage for high-traffic scenarios

### 7. Why Playwright over Selenium?

**Decision:** Use Playwright for browser automation

**Rationale:**
- Modern API with async/await support
- Better performance and reliability
- Built-in waiting and auto-retry
- Cross-browser support (Chromium, Firefox, WebKit)
- Excellent documentation

**Trade-offs:**
- Newer tool with smaller community
- Some edge cases not well documented
- Requires Node.js installation

### 8. Why Server-Sent Events (SSE) for Real-Time Updates?

**Decision:** Use SSE instead of WebSockets for scan progress

**Rationale:**
- Simpler implementation (HTTP-based)
- Automatic reconnection in browsers
- Works through most firewalls/proxies
- Sufficient for one-way communication
- No need for WebSocket infrastructure

**Trade-offs:**
- One-way communication only (server → client)
- Less efficient than WebSockets for high-frequency updates
- Limited browser support (IE not supported)

---

## Code Examples

### Creating a Scan

```python
from services.scan_service import ScanService
from models.scan import ScanParams

# Initialize service
scan_service = ScanService()

# Create scan parameters
params = ScanParams(
    domain="https://example.com",
    scan_mode="quick",
    custom_pages=["/about", "/contact"],
    max_depth=5
)

# Execute scan
result = await scan_service.create_scan(
    domain_config_id="config_123",
    params=params
)

print(f"Scan ID: {result.scan_id}")
print(f"Total cookies: {result.total_cookies}")
```

### Generating a Report

```python
from analytics.report_generator import ReportGenerator

# Initialize generator
report_gen = ReportGenerator()

# Generate PDF report
report = await report_gen.generate_compliance_report(
    scan_id="scan_456",
    format="pdf"
)

# Save to file
with open(f"report_{scan_id}.pdf", "wb") as f:
    f.write(report.content)
```

### Creating a Schedule

```python
from services.schedule_repository import ScheduleRepository
from models.schedule import Schedule

# Initialize repository
schedule_repo = ScheduleRepository()

# Create schedule
schedule = Schedule(
    domain_config_id="config_123",
    domain="https://example.com",
    profile_id="profile_456",
    frequency="daily",
    time_config={"hour": 2, "minute": 0},
    enabled=True
)

# Save to database
await schedule_repo.create(schedule)

# Register with scheduler
from services.enhanced_scheduler import EnhancedScheduler
scheduler = EnhancedScheduler()
scheduler.register_schedule(schedule)
```

### Sending a Notification

```python
from services.notification_service import NotificationService
from models.notification import Notification, NotificationEvent

# Initialize service
notif_service = NotificationService()

# Create notification
notification = Notification(
    user_id="user_123",
    event=NotificationEvent.SCAN_COMPLETED,
    data={
        "scan_id": "scan_456",
        "domain": "example.com",
        "total_cookies": 42
    }
)

# Send via all enabled channels
await notif_service.send(notification)
```

### Using the API

```python
import requests

# Authenticate
response = requests.post(
    "https://api.example.com/api/v1/auth/login",
    json={"email": "user@example.com", "password": "password"}
)
token = response.json()["access_token"]

# Create scan
response = requests.post(
    "https://api.example.com/api/v1/scans",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "domain": "https://example.com",
        "scan_mode": "quick",
        "custom_pages": ["/about", "/contact"]
    }
)
scan_id = response.json()["scan_id"]

# Poll for results
import time
while True:
    response = requests.get(
        f"https://api.example.com/api/v1/scans/{scan_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    result = response.json()
    if result["status"] in ["success", "failed"]:
        break
    time.sleep(5)

print(f"Scan completed: {result['total_cookies']} cookies found")
```

---

## Testing Strategy

### Unit Tests

**Scope:** Individual functions and methods

**Tools:** pytest, pytest-asyncio, pytest-mock

**Coverage Target:** 80%

**Key Areas:**
- Cookie categorization logic
- Metrics calculations
- Report generation
- Authentication/authorization
- Rate limiting

**Example:**
```python
import pytest
from services.cookie_categorization import categorize_cookie

def test_categorize_cookie_from_db():
    cookie = {"name": "session_id", "domain": "example.com"}
    result = categorize_cookie(cookie)
    assert result["category"] == "Necessary"
    assert result["source"] == "DB"
```

### Integration Tests

**Scope:** Component interactions

**Tools:** pytest, testcontainers, httpx

**Setup:** Test database and Redis instances

**Key Scenarios:**
- Complete scan workflow
- Schedule creation and execution
- Report generation from scan results
- Notification delivery on events

**Example:**
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_and_retrieve_scan(client: AsyncClient):
    # Create scan
    response = await client.post(
        "/api/v1/scans",
        json={"domain": "https://example.com", "scan_mode": "quick"}
    )
    assert response.status_code == 201
    scan_id = response.json()["scan_id"]
    
    # Retrieve scan
    response = await client.get(f"/api/v1/scans/{scan_id}")
    assert response.status_code == 200
    assert response.json()["scan_id"] == scan_id
```

### End-to-End Tests

**Scope:** Complete user workflows

**Tools:** Playwright (for browser automation)

**Key Workflows:**
- User login → create scan → view results
- User schedules recurring scan → receives notification
- User generates report → downloads PDF

### Performance Tests

**Scope:** Load and stress testing

**Tools:** Locust, k6

**Targets:**
- Quick scan: < 60 seconds
- API response time: < 200ms (p95)
- Support 10 concurrent scans
- 1000 requests/minute per API server

---

## Monitoring and Observability

### Metrics (Prometheus)

**Scan Metrics:**
- `dcs_scans_total` - Counter by mode and status
- `dcs_scan_duration_seconds` - Histogram
- `dcs_active_scans` - Gauge

**API Metrics:**
- `dcs_api_requests_total` - Counter by endpoint, method, status
- `dcs_api_latency_seconds` - Histogram by endpoint

**System Metrics:**
- `dcs_db_connections` - Gauge
- `dcs_cache_hit_rate` - Gauge
- `dcs_celery_tasks_pending` - Gauge

### Structured Logging

**Format:** JSON with structured fields

**Key Fields:**
- `timestamp` - ISO 8601 format
- `level` - DEBUG, INFO, WARNING, ERROR, CRITICAL
- `message` - Human-readable message
- `request_id` - Unique request identifier
- `user_id` - User performing action
- `component` - Service/module name
- `context` - Additional structured data

**Example:**
```json
{
  "timestamp": "2025-01-15T10:30:00.123Z",
  "level": "INFO",
  "message": "Scan completed successfully",
  "request_id": "req_abc123",
  "user_id": "user_456",
  "component": "scan_service",
  "context": {
    "scan_id": "scan_789",
    "domain": "example.com",
    "duration": 45.2,
    "cookies_found": 42
  }
}
```

### Health Checks

**Endpoint:** `GET /api/v1/health`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00Z",
  "components": {
    "database": {
      "status": "healthy",
      "latency_ms": 5
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 1
    },
    "browser": {
      "status": "healthy",
      "pool_size": 5
    },
    "scheduler": {
      "status": "healthy",
      "jobs_count": 10
    }
  }
}
```

### Error Tracking (Sentry)

**Integration:** Automatic error reporting to Sentry

**Captured Data:**
- Exception type and message
- Stack trace
- Request context (URL, method, headers)
- User context (user_id, email)
- Environment (production, staging, development)
- Breadcrumbs (recent events leading to error)

---

## Migration Strategy

### Phase 1: Foundation (Weeks 1-2)
- Set up new database schema
- Implement API Gateway with authentication
- Create base models and interfaces

### Phase 2: Core Features (Weeks 3-4)
- Enhance scan engine with new modes
- Implement analytics module
- Build notification service

### Phase 3: Dashboard (Weeks 5-6)
- Develop React dashboard
- Implement real-time updates
- Create visualization components

### Phase 4: Optimization (Week 7)
- Implement caching layer
- Optimize database queries
- Add performance monitoring

### Phase 5: Testing & Deployment (Week 8)
- Comprehensive testing
- Documentation
- Production deployment

### Backward Compatibility

- Maintain existing API endpoints
- Support legacy data formats
- Provide migration scripts for existing data
- Run old and new systems in parallel during transition

---

## Additional Resources

- **API Documentation**: `/api/docs` - OpenAPI specification
- **User Guide**: `dashboard/USER_GUIDE.md` - Dashboard usage guide
- **Deployment Guide**: `DEPLOYMENT_GUIDE.md` - Setup instructions
- **Contributing Guide**: `CONTRIBUTING.md` - Development guidelines

---

**Version:** 1.0  
**Last Updated:** November 2025  
**Maintainers:** Platform Team
