# Three-Tier Scanning System - Deployment Guide

## Overview

This guide walks you through deploying the complete three-tier scanning system with Quick Scan, Deep Scan, and Scheduled Scan capabilities.

## Prerequisites

- PostgreSQL 12+ database
- Redis 6+ server (for distributed locking)
- Python 3.9+
- Node.js 16+ (for Playwright browsers)
- 8GB+ RAM recommended (16GB for deep scans)

## Step-by-Step Deployment

### Step 1: Apply Database Migration

The new scan_type and scan_params columns need to be added to the schedules table.

```bash
# Navigate to project directory
cd /Users/ajitsahu/Code-base/dynamic_cookie_scanning_sep29

# Apply migration
psql -U your_user -d your_database -f database/migrations/005_schedule_scan_types.sql
```

**Verification:**
```sql
-- Verify columns exist
SELECT column_name, data_type, column_default, is_nullable
FROM information_schema.columns
WHERE table_name = 'schedules'
AND column_name IN ('scan_type', 'scan_params');

-- Expected output:
-- column_name | data_type | column_default | is_nullable
-- scan_type   | varchar   | 'quick'        | NO
-- scan_params | jsonb     | '{}'           | YES
```

### Step 2: Install Dependencies

Ensure all required Python packages are installed:

```bash
# Install/upgrade required packages
pip install playwright playwright-stealth asyncpg apscheduler redis requests

# Install Playwright browsers
playwright install
```

### Step 3: Configure Environment Variables

Update your environment configuration:

```bash
# Database
export DATABASE_URL="postgresql://user:password@localhost:5432/cookie_scanner"

# Redis (for distributed locking)
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export REDIS_DB="0"
export REDIS_PASSWORD=""  # Optional

# Scheduler Settings
export MAX_WORKERS="10"  # Maximum concurrent scan workers
export SCHEDULE_CHECK_INTERVAL="60"  # Check for schedule changes every 60 seconds
export ENABLE_API_SYNC="false"  # Set to true if syncing from external API

# API Settings
export API_HOST="0.0.0.0"
export API_PORT="8000"
```

### Step 4: Restart API Server

Restart the FastAPI server to load the new schedule endpoints:

```bash
# Stop existing server (if running)
pkill -f "uvicorn api.main:app"

# Start server with new code
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Verification:**
```bash
# Check API is running
curl http://localhost:8000/api/v1/health

# Check schedule endpoints are available
curl http://localhost:8000/docs

# Look for /api/v1/schedules endpoints in Swagger UI
```

### Step 5: Start Enhanced Scheduler Service

The scheduler runs as a separate background service:

```bash
# Start scheduler
python -m services.enhanced_scheduler
```

**Expected output:**
```
INFO - EnhancedScheduler initialized
INFO - Redis client initialized
INFO - Database connection initialized
INFO - Distributed lock manager initialized
INFO - Schedule repository initialized
INFO - Job history initialized
INFO - Schedule watcher initialized
INFO - Scheduled scan executor initialized
INFO - Enhanced scheduler started successfully
```

**Run as background service (recommended):**
```bash
# Using systemd
sudo cp deployment/scheduler.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable scheduler
sudo systemctl start scheduler

# Check status
sudo systemctl status scheduler

# View logs
sudo journalctl -u scheduler -f
```

### Step 6: Verify Installation

Run the test script to verify all components are working:

```bash
# Make test script executable
chmod +x scripts/test_three_tier_system.py

# Run tests (requires API authentication)
python scripts/test_three_tier_system.py --token YOUR_JWT_TOKEN
```

**Expected output:**
```
================================================================================
  Three-Tier Scanning System Tests
================================================================================

API URL: http://localhost:8000
Test Domain: https://example.com
Auth: Enabled

================================================================================
  TIER 3: Scheduled Scan Test
================================================================================

Test 1: Create quick scheduled scan
✅ PASS: Created quick schedule: 550e8400-e29b-41d4-a716-446655440000
✅ PASS: Scan type: quick
✅ PASS: Frequency: daily

Test 2: Create deep scheduled scan
✅ PASS: Created deep schedule: 660e8400-e29b-41d4-a716-446655440001
✅ PASS: Max pages: 5000

...

================================================================================
  OVERALL: 3/3 tiers passed
================================================================================
```

## Configuration

### Quick Scan Configuration

Quick scans are configured via the parallel scanner:

```python
# In services/scheduled_scan_executor.py
init_scheduled_scan_executor(
    max_concurrent_quick=5,  # Concurrent pages for quick scans
    browser_pool_size=5,     # Not used for quick scans
    pages_per_browser=20     # Not used for quick scans
)
```

### Deep Scan Configuration

Deep scans use the enterprise scanner with browser pool:

```python
# In services/scheduled_scan_executor.py
init_scheduled_scan_executor(
    max_concurrent_quick=5,   # Not used for deep scans
    browser_pool_size=5,      # Number of browser instances
    pages_per_browser=20      # Concurrent pages per browser
)

# Total concurrency for deep scans = browser_pool_size × pages_per_browser
# Default: 5 × 20 = 100 concurrent pages
```

**Adjusting for your environment:**

| Server RAM | browser_pool_size | pages_per_browser | Total Concurrency |
|------------|-------------------|-------------------|-------------------|
| 8 GB | 3 | 10 | 30 |
| 16 GB | 5 | 20 | 100 |
| 32 GB | 8 | 30 | 240 |
| 64 GB | 10 | 50 | 500 (maximum) |

### Scheduler Configuration

The scheduler checks for changes every 60 seconds by default:

```python
# In services/enhanced_scheduler.py
scheduler = EnhancedScheduler(
    max_workers=10,                   # Thread pool size
    enable_api_sync=False,            # External API sync
    api_sync_interval=300,            # API sync interval (5 minutes)
    schedule_check_interval=60        # Database check interval (1 minute)
)
```

## Creating Schedules

### Example 1: Daily Quick Scan

Scan important pages every day at 9:00 AM:

```bash
curl -X POST http://localhost:8000/api/v1/schedules \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "https://example.com",
    "domain_config_id": "550e8400-e29b-41d4-a716-446655440000",
    "scan_type": "quick",
    "scan_params": {
      "custom_pages": ["/", "/about", "/privacy", "/terms"]
    },
    "frequency": "daily",
    "time_config": {
      "hour": 9,
      "minute": 0
    },
    "enabled": true
  }'
```

### Example 2: Weekly Deep Scan

Full website scan every Monday at 2:00 AM:

```bash
curl -X POST http://localhost:8000/api/v1/schedules \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "https://example.com",
    "domain_config_id": "550e8400-e29b-41d4-a716-446655440000",
    "scan_type": "deep",
    "scan_params": {
      "max_pages": 10000,
      "chunk_size": 1000,
      "browser_pool_size": 5,
      "pages_per_browser": 20
    },
    "frequency": "weekly",
    "time_config": {
      "day_of_week": "monday",
      "hour": 2,
      "minute": 0
    },
    "enabled": true
  }'
```

### Example 3: Hourly Quick Scan

Monitor key pages every hour:

```bash
curl -X POST http://localhost:8000/api/v1/schedules \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "https://example.com",
    "domain_config_id": "550e8400-e29b-41d4-a716-446655440000",
    "scan_type": "quick",
    "scan_params": {
      "custom_pages": ["/checkout", "/cart"]
    },
    "frequency": "hourly",
    "time_config": {
      "minute": 0
    },
    "enabled": true
  }'
```

## Monitoring

### Check Scheduler Status

```bash
# View scheduler logs
tail -f logs/scheduler.log

# Or if using systemd
sudo journalctl -u scheduler -f
```

### Monitor Active Schedules

```bash
# List all enabled schedules
curl http://localhost:8000/api/v1/schedules?enabled=true \
  -H "Authorization: Bearer YOUR_TOKEN"

# List deep scan schedules
curl "http://localhost:8000/api/v1/schedules?scan_type=deep" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Check Schedule Execution

```bash
# Get schedule details (includes last_run, next_run, last_status)
curl http://localhost:8000/api/v1/schedules/{schedule_id} \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Database Queries

```sql
-- View all schedules with status
SELECT schedule_id, domain, scan_type, frequency, enabled,
       last_run, next_run, last_status
FROM schedules
ORDER BY created_at DESC;

-- Count schedules by type
SELECT scan_type, COUNT(*) as count
FROM schedules
WHERE enabled = true
GROUP BY scan_type;

-- Recent execution history
SELECT se.executed_at, s.domain, s.scan_type, se.status, se.duration_seconds
FROM schedule_executions se
JOIN schedules s ON se.schedule_id = s.schedule_id
ORDER BY se.executed_at DESC
LIMIT 10;

-- Failed executions
SELECT s.domain, s.scan_type, se.executed_at, se.error
FROM schedule_executions se
JOIN schedules s ON se.schedule_id = s.schedule_id
WHERE se.status = 'failed'
ORDER BY se.executed_at DESC
LIMIT 10;
```

## Troubleshooting

### Issue: Schedules Not Executing

**Symptoms**: Schedules created but never execute

**Solutions**:
1. Check scheduler service is running:
   ```bash
   ps aux | grep enhanced_scheduler
   # Or: systemctl status scheduler
   ```

2. Check schedule is enabled:
   ```sql
   SELECT schedule_id, enabled FROM schedules WHERE schedule_id = 'YOUR_ID';
   ```

3. Check time configuration is valid:
   ```sql
   SELECT schedule_id, frequency, time_config FROM schedules WHERE schedule_id = 'YOUR_ID';
   ```

4. Check scheduler logs for errors:
   ```bash
   tail -100 logs/scheduler.log | grep ERROR
   ```

### Issue: Database Connection Errors

**Symptoms**: "Database pool not initialized" or connection refused

**Solutions**:
1. Verify DATABASE_URL is correct:
   ```bash
   echo $DATABASE_URL
   ```

2. Test database connection:
   ```bash
   psql $DATABASE_URL -c "SELECT 1"
   ```

3. Check migration was applied:
   ```sql
   SELECT column_name FROM information_schema.columns
   WHERE table_name = 'schedules' AND column_name IN ('scan_type', 'scan_params');
   ```

### Issue: Redis Connection Errors

**Symptoms**: "Failed to acquire distributed lock" or Redis connection refused

**Solutions**:
1. Verify Redis is running:
   ```bash
   redis-cli ping
   # Expected: PONG
   ```

2. Check Redis configuration:
   ```bash
   echo $REDIS_HOST
   echo $REDIS_PORT
   ```

3. Test Redis connection:
   ```bash
   redis-cli -h $REDIS_HOST -p $REDIS_PORT ping
   ```

### Issue: Memory Errors During Deep Scans

**Symptoms**: Out of memory, browser crashes, slow performance

**Solutions**:
1. Reduce browser pool size:
   ```python
   # In scheduled_scan_executor.py
   init_scheduled_scan_executor(
       browser_pool_size=3,  # Reduce from 5
       pages_per_browser=15  # Reduce from 20
   )
   ```

2. Reduce chunk size:
   ```json
   {
     "scan_params": {
       "chunk_size": 500  // Reduce from 1000
     }
   }
   ```

3. Add server memory or use smaller max_pages

### Issue: Duplicate Schedule Executions

**Symptoms**: Same schedule running multiple times simultaneously

**Solutions**:
1. Ensure Redis is properly configured (required for distributed locking)
2. Check only one scheduler instance is running:
   ```bash
   ps aux | grep enhanced_scheduler | wc -l
   # Should be 1 (plus grep itself)
   ```

3. Verify lock timeout settings are appropriate

## Performance Tuning

### For High-Volume Environments

```python
# Increase scheduler workers
scheduler = EnhancedScheduler(
    max_workers=20,  # From default 10
    schedule_check_interval=30  # Check more frequently
)

# Increase API server workers
uvicorn api.main:app --workers 4

# Increase database pool size
asyncpg.create_pool(
    min_size=10,
    max_size=50
)
```

### For Resource-Constrained Environments

```python
# Reduce scheduler workers
scheduler = EnhancedScheduler(
    max_workers=5,
    schedule_check_interval=120  # Check less frequently
)

# Reduce scan concurrency
init_scheduled_scan_executor(
    max_concurrent_quick=3,
    browser_pool_size=2,
    pages_per_browser=10
)
```

## Security Considerations

1. **Authentication**: All schedule endpoints require `schedules:read` or `schedules:write` scopes

2. **Rate Limiting**: Consider adding rate limiting to schedule creation endpoints

3. **Input Validation**: All schedule parameters are validated via Pydantic models

4. **SQL Injection**: All database queries use parameterized queries (asyncpg)

5. **Distributed Locking**: Redis-based locking prevents duplicate executions

## Backup and Recovery

### Backup Schedules

```bash
# Export all schedules
pg_dump -U user -d dbname -t schedules -t schedule_executions > schedules_backup.sql

# Or export as JSON via API
curl http://localhost:8000/api/v1/schedules?page_size=100 \
  -H "Authorization: Bearer TOKEN" > schedules_backup.json
```

### Restore Schedules

```bash
# From SQL dump
psql -U user -d dbname < schedules_backup.sql

# From JSON (requires custom import script)
python scripts/import_schedules.py schedules_backup.json
```

## Scaling

### Horizontal Scaling

The system supports multiple scheduler instances:

1. **Distributed Locking**: Redis ensures only one instance executes each schedule
2. **Database-Backed**: All schedules stored in PostgreSQL
3. **Stateless**: Scheduler instances are stateless and can be added/removed

```bash
# Run multiple scheduler instances
# Instance 1
python -m services.enhanced_scheduler

# Instance 2 (on another server)
python -m services.enhanced_scheduler

# Only one will acquire the lock and execute each schedule
```

### Vertical Scaling

For large deployments:

- **CPU**: More cores for parallel scanning (browser pool)
- **RAM**: More memory for larger browser pools
- **Database**: PostgreSQL connection pooling and replication
- **Redis**: Redis Cluster for distributed locking

## Maintenance

### Regular Tasks

1. **Monitor disk space** (Playwright browser cache, checkpoints)
2. **Clean old executions** (schedule_executions table)
3. **Review failed scans** and update schedules
4. **Update Playwright** browsers periodically

```bash
# Clean old execution history (keep last 30 days)
DELETE FROM schedule_executions
WHERE executed_at < NOW() - INTERVAL '30 days';

# Update Playwright browsers
playwright install
```

## Next Steps

1. ✅ Deploy and test the system
2. ✅ Create initial schedules for your domains
3. ✅ Monitor execution and adjust configuration
4. Configure notifications for failed scans
5. Set up monitoring dashboards (Grafana, etc.)
6. Configure automated backups
7. Review and optimize performance

## Support

For issues or questions:
- Review logs: `logs/scheduler.log`, `logs/api.log`
- Check documentation: [THREE_TIER_SCANNING_SYSTEM.md](THREE_TIER_SCANNING_SYSTEM.md)
- Database queries: Check schedule and execution tables
- Test script: `python scripts/test_three_tier_system.py`

## Summary Checklist

- [ ] Applied database migration (005_schedule_scan_types.sql)
- [ ] Installed required dependencies (playwright, asyncpg, apscheduler)
- [ ] Configured environment variables
- [ ] Restarted API server
- [ ] Started enhanced scheduler service
- [ ] Ran test script successfully
- [ ] Created first test schedule
- [ ] Verified schedule execution
- [ ] Set up monitoring
- [ ] Configured backups

**Your three-tier scanning system is ready! 🚀**
