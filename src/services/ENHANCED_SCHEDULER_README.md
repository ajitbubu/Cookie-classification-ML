# Enhanced Scheduler Service

## Overview

The Enhanced Scheduler Service is a robust, production-ready scheduler that replaces the basic `schedule_manager.py` with advanced features including:

- **Distributed Locking**: Prevents duplicate job execution across multiple scheduler instances using Redis
- **Database Persistence**: Stores schedules in PostgreSQL instead of fetching from API
- **Dynamic Updates**: Monitors database for schedule changes and updates jobs without restart
- **Job History & Audit Trail**: Tracks all job executions with detailed status and error information

## Architecture

### Components

1. **DistributedLock** (`services/distributed_lock.py`)
   - Redis-based distributed locking
   - Prevents duplicate job execution across instances
   - Automatic lock expiration and renewal

2. **DatabaseConnection** (`database/connection.py`)
   - PostgreSQL connection pooling
   - Thread-safe connection management
   - Health check support

3. **ScheduleRepository** (`services/schedule_repository.py`)
   - CRUD operations for schedules
   - Sync schedules from API to database
   - Query schedules by domain, config ID, etc.

4. **ScheduleWatcher** (`services/schedule_watcher.py`)
   - Monitors database for schedule changes
   - Detects additions, modifications, and deletions
   - Triggers scheduler updates dynamically

5. **JobHistory** (`services/job_history.py`)
   - Tracks all job executions
   - Records start time, end time, duration
   - Stores error details and scan results
   - Provides execution statistics

6. **EnhancedScheduler** (`services/enhanced_scheduler.py`)
   - Main scheduler orchestrator
   - Integrates all components
   - Manages APScheduler jobs

## Database Schema

### Schedules Table

```sql
CREATE TABLE schedules (
    schedule_id UUID PRIMARY KEY,
    domain_config_id UUID NOT NULL,
    domain VARCHAR(255) NOT NULL,
    profile_id UUID REFERENCES scan_profiles(profile_id),
    frequency VARCHAR(50) NOT NULL,
    time_config JSONB NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    next_run TIMESTAMP,
    last_run TIMESTAMP,
    last_status VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Job Executions Table

```sql
CREATE TABLE job_executions (
    execution_id UUID PRIMARY KEY,
    schedule_id UUID REFERENCES schedules(schedule_id),
    job_id VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    domain_config_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds FLOAT,
    scan_id UUID,
    error_message TEXT,
    error_details JSONB,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/cookie_scanner

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # Optional

# Scheduler
MAX_WORKERS=5
JOB_REPLACE_EXISTING_INSTANCE=True
JOB_MAX_INSTANCES=1
JOB_COALESCE=true
JOB_MISFIRE_GRACE_TIME=300

# API Sync (optional)
API_URL=http://api.example.com/schedules
REQUEST_TIMEOUT=10
```

## Usage

### Running Migrations

Before using the enhanced scheduler, run the database migrations:

```bash
# Set DATABASE_URL environment variable
export DATABASE_URL="postgresql://user:password@localhost:5432/cookie_scanner"

# Run migrations
python run_migrations.py
```

### Starting the Enhanced Scheduler

```python
from services.enhanced_scheduler import EnhancedScheduler

# Create scheduler instance
scheduler = EnhancedScheduler(
    max_workers=5,
    enable_api_sync=True,  # Sync from API periodically
    api_sync_interval=300,  # Sync every 5 minutes
    schedule_check_interval=60  # Check for DB changes every minute
)

# Start scheduler (blocking)
scheduler.run()
```

### Command Line

```bash
# Run enhanced scheduler
python services/enhanced_scheduler.py
```

## Features

### 1. Distributed Locking

Prevents duplicate job execution when running multiple scheduler instances:

```python
# Automatically handled by EnhancedScheduler
# Each job acquires a lock before execution
# If lock is held by another instance, job is skipped
```

### 2. Database Persistence

Schedules are stored in PostgreSQL and can be managed via the repository:

```python
from services.schedule_repository import get_schedule_repository

repo = get_schedule_repository()

# Create a schedule
schedule_id = repo.create_schedule(
    domain_config_id="abc-123",
    domain="example.com",
    frequency="daily",
    time_config={"hour": 2, "minute": 0},
    enabled=True
)

# Update a schedule
repo.update_schedule(
    schedule_id=schedule_id,
    frequency="weekly",
    time_config={"day": "monday", "hour": 2, "minute": 0}
)

# Delete a schedule
repo.delete_schedule(schedule_id)
```

### 3. Dynamic Updates

The scheduler automatically detects and applies schedule changes:

```python
# Changes are detected every schedule_check_interval seconds
# No restart required when:
# - New schedules are added
# - Existing schedules are modified
# - Schedules are deleted or disabled
```

### 4. Job History & Audit Trail

All job executions are tracked in the database:

```python
from services.job_history import get_job_history

history = get_job_history()

# Get recent executions
recent = history.get_recent_executions(hours=24)

# Get executions for a specific schedule
executions = history.get_executions_by_schedule(schedule_id)

# Get execution statistics
stats = history.get_execution_statistics(days=7)
# Returns: {
#   'total_executions': 100,
#   'successful': 95,
#   'failed': 5,
#   'success_rate': 95.0,
#   'avg_duration': 45.2,
#   'min_duration': 30.1,
#   'max_duration': 120.5
# }
```

## API Integration

### Syncing from External API

The scheduler can sync schedules from an external API:

```python
# Enable API sync
scheduler = EnhancedScheduler(
    enable_api_sync=True,
    api_sync_interval=300  # Sync every 5 minutes
)

# Manual sync
stats = scheduler.sync_schedules_from_api()
# Returns: {'created': 5, 'updated': 3, 'skipped': 2}
```

### API Schedule Format

Expected format from API:

```json
{
  "data": [
    {
      "domain_config_id": "abc-123",
      "data": {
        "domain": "example.com",
        "description": "Example domain",
        "allow_deep_scan": true,
        "maxPages": 50,
        "scanDepth": 5,
        "maxRetries": 3,
        "customPages": ["/page1", "/page2"],
        "accept_selector": "button[data-role='accept']",
        "schedule": {
          "frequency": "daily",
          "time": {
            "hour": 2,
            "minute": 0
          }
        }
      }
    }
  ]
}
```

## Monitoring

### Health Checks

```python
# Check Redis connectivity
redis_client = get_redis_client()
is_healthy = redis_client.ping()

# Check database connectivity
db = get_db_connection()
is_healthy = db.ping()
```

### Metrics

The scheduler logs important metrics:

- Job execution count
- Success/failure rates
- Execution duration
- Lock acquisition failures
- Schedule sync statistics

### Logging

All components use structured logging:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Logs include:
# - Job start/completion
# - Lock acquisition/release
# - Schedule changes detected
# - Errors and exceptions
```

## Migration from Old Scheduler

### Step 1: Run Migrations

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/cookie_scanner"
python run_migrations.py
```

### Step 2: Sync Existing Schedules

```python
from services.enhanced_scheduler import EnhancedScheduler

scheduler = EnhancedScheduler(enable_api_sync=True)
scheduler.start()

# This will:
# 1. Fetch schedules from API
# 2. Store them in database
# 3. Load them into APScheduler
```

### Step 3: Update Startup Script

Replace:
```python
from schedule_manager import run_scheduler
run_scheduler()
```

With:
```python
from services.enhanced_scheduler import run_enhanced_scheduler
run_enhanced_scheduler()
```

### Step 4: Verify

Check that schedules are running:

```python
from services.job_history import get_job_history

history = get_job_history()
recent = history.get_recent_executions(hours=1)
print(f"Recent executions: {len(recent)}")
```

## Troubleshooting

### Issue: Jobs not executing

**Check:**
1. Schedules are enabled: `SELECT * FROM schedules WHERE enabled = TRUE`
2. Redis is accessible: `redis_client.ping()`
3. Database is accessible: `db.ping()`
4. Locks are not stuck: Check Redis keys `lock:schedule:*`

### Issue: Duplicate job executions

**Check:**
1. Distributed locking is working
2. Multiple scheduler instances have unique instance IDs
3. Redis is shared across all instances

### Issue: Schedule changes not detected

**Check:**
1. Schedule watcher is running
2. `schedule_check_interval` is not too long
3. Database connection is healthy
4. Schedule hashes are being computed correctly

## Performance Considerations

### Connection Pooling

- Database: 1-10 connections per instance
- Redis: 50 max connections per instance

### Lock Timeouts

- Default lock timeout: 60 seconds
- Adjust based on average scan duration
- Locks auto-expire to prevent deadlocks

### Schedule Check Interval

- Default: 60 seconds
- Lower for faster updates (higher DB load)
- Higher for less DB load (slower updates)

### Job History Cleanup

Periodically clean up old job execution records:

```python
from services.job_history import get_job_history

history = get_job_history()
deleted = history.cleanup_old_executions(days=90)
print(f"Deleted {deleted} old execution records")
```

## Best Practices

1. **Run multiple scheduler instances** for high availability
2. **Monitor job execution statistics** to detect issues
3. **Set appropriate lock timeouts** based on scan duration
4. **Clean up old job history** periodically
5. **Use database indexes** for better query performance
6. **Monitor Redis memory usage** for lock keys
7. **Set up alerts** for failed job executions
8. **Back up the database** regularly

## Requirements

- Python 3.7+
- PostgreSQL 12+
- Redis 5+
- APScheduler 3.9+
- psycopg2-binary 2.9+
- redis 4.5+

## License

Same as parent project.
