# Celery Async Task Processing

This document describes the Celery-based asynchronous task processing system for the Cookie Scanner Platform.

## Overview

The platform uses Celery for handling long-running tasks asynchronously:

- **Report Generation**: Generate PDF, HTML, and JSON compliance reports
- **Notification Delivery**: Send notifications via email, webhook, and Slack
- **Periodic Tasks**: Automated cleanup and monitoring tasks
- **Task Monitoring**: Health checks and statistics collection

## Architecture

### Components

1. **Celery App** (`services/celery_app.py`)
   - Core Celery application configuration
   - Task routing and queue management
   - Signal handlers for logging

2. **Report Tasks** (`services/report_tasks.py`)
   - `generate_report_async`: Generate single report
   - `generate_multiple_reports_async`: Generate multiple formats
   - `export_scan_to_csv_async`: Export scan data to CSV
   - `cleanup_old_reports`: Periodic cleanup task

3. **Notification Tasks** (`services/notification_tasks.py`)
   - `send_notification_async`: Send single notification
   - `send_event_notifications_async`: Send notifications for events
   - `send_bulk_notifications_async`: Send to multiple users
   - `cleanup_old_notifications`: Periodic cleanup task

4. **Monitoring** (`services/celery_monitoring.py`)
   - Worker statistics and health monitoring
   - Queue statistics
   - Task status tracking
   - Task revocation and queue management

5. **Beat Scheduler** (`services/celery_beat_config.py`)
   - Periodic task scheduling
   - Automated health checks
   - Cleanup tasks

### Task Queues

The system uses three queues for task organization:

- **default**: General tasks and monitoring
- **reports**: Report generation tasks
- **notifications**: Notification delivery tasks

## Installation

### Prerequisites

```bash
# Redis must be running
docker run -d -p 6379:6379 redis:7

# Or use existing Redis from docker-compose
docker-compose up -d redis
```

### Python Dependencies

All required dependencies are in `requirements.txt`:

```
celery>=5.3.0
redis>=5.0.0
```

## Usage

### Starting Workers

#### Basic Worker (All Queues)

```bash
python run_celery_worker.py
```

#### Specific Queue

```bash
# Reports queue only
python run_celery_worker.py --queue reports

# Notifications queue only
python run_celery_worker.py --queue notifications
```

#### With Custom Concurrency

```bash
# 8 worker processes
python run_celery_worker.py --concurrency 8
```

#### With Autoscaling

```bash
# Autoscale between 3 and 10 workers
python run_celery_worker.py --autoscale 10,3
```

#### Advanced Options

```bash
python run_celery_worker.py \
  --queue reports \
  --concurrency 4 \
  --loglevel DEBUG \
  --pool prefork
```

### Starting Beat Scheduler

For periodic tasks:

```bash
python run_celery_beat.py
```

### Using Celery CLI Directly

```bash
# Start worker
celery -A services.celery_app worker --loglevel=info

# Start beat scheduler
celery -A services.celery_app beat --loglevel=info

# Monitor with Flower (if installed)
celery -A services.celery_app flower
```

## Task Examples

### Generate Report Asynchronously

```python
from services.report_tasks import generate_report_async

# Submit task
result = generate_report_async.delay(
    scan_id='123e4567-e89b-12d3-a456-426614174000',
    format='pdf'
)

# Check status
print(f"Task ID: {result.id}")
print(f"Status: {result.state}")

# Wait for result (blocking)
report_info = result.get(timeout=60)
print(f"Report generated: {report_info['file_path']}")
```

### Generate Multiple Formats

```python
from services.report_tasks import generate_multiple_reports_async

# Generate PDF, HTML, and JSON
result = generate_multiple_reports_async.delay(
    scan_id='123e4567-e89b-12d3-a456-426614174000',
    formats=['pdf', 'html', 'json']
)

# Get results
reports = result.get(timeout=120)
print(f"Generated {reports['total_generated']} reports")
```

### Send Notification Asynchronously

```python
from services.notification_tasks import send_notification_async
from models.notification import Notification, NotificationEvent, NotificationChannel

# Prepare notification data
notification_data = {
    'notification_id': str(uuid4()),
    'user_id': 'user123',
    'event': NotificationEvent.SCAN_COMPLETED.value,
    'channel': NotificationChannel.EMAIL.value,
    'status': 'pending',
    'data': {
        'scan_id': '123e4567-e89b-12d3-a456-426614174000',
        'domain': 'example.com',
        'total_cookies': 42
    }
}

preferences_data = {
    'user_id': 'user123',
    'email_address': 'user@example.com',
    'enabled_channels': ['email'],
    'enabled_events': ['scan.completed']
}

# Submit task
result = send_notification_async.delay(
    notification_data,
    preferences_data
)

# Check result
notification_result = result.get(timeout=30)
print(f"Notification sent: {notification_result['success']}")
```

### Export to CSV

```python
from services.report_tasks import export_scan_to_csv_async

result = export_scan_to_csv_async.delay(
    scan_id='123e4567-e89b-12d3-a456-426614174000'
)

csv_info = result.get(timeout=60)
print(f"CSV exported: {csv_info['file_path']}")
```

## Monitoring

### Using Python API

```python
from services.celery_monitoring import get_celery_monitor

monitor = get_celery_monitor()

# Get worker statistics
worker_stats = monitor.get_worker_stats()
print(f"Active workers: {worker_stats['worker_count']}")
print(f"Active tasks: {worker_stats['total_active_tasks']}")

# Get task status
task_status = monitor.get_task_status('task-id-here')
print(f"Task state: {task_status['state']}")

# Get comprehensive status
status = monitor.get_comprehensive_status()
print(f"System status: {status['status']}")
```

### Using Celery CLI

```bash
# Inspect active tasks
celery -A services.celery_app inspect active

# Inspect registered tasks
celery -A services.celery_app inspect registered

# Inspect worker stats
celery -A services.celery_app inspect stats

# Inspect scheduled tasks
celery -A services.celery_app inspect scheduled
```

### Monitoring Tasks

The system includes built-in monitoring tasks:

```python
from services.celery_monitoring import monitor_celery_health

# Run health check
health = monitor_celery_health.delay()
result = health.get()
print(f"Health status: {result['status']}")
```

## Task Management

### Revoke (Cancel) a Task

```python
from services.celery_monitoring import get_celery_monitor

monitor = get_celery_monitor()

# Revoke task (soft)
monitor.revoke_task('task-id-here')

# Revoke and terminate (hard)
monitor.revoke_task('task-id-here', terminate=True)
```

### Purge Queue

```python
from services.celery_monitoring import get_celery_monitor

monitor = get_celery_monitor()

# Purge all tasks from default queue
result = monitor.purge_queue()
print(f"Purged {result['purged_count']} tasks")
```

## Configuration

### Environment Variables

```bash
# Redis connection
REDIS_URL=redis://localhost:6379/0

# Celery settings (optional, defaults are set)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Task Routing

Tasks are automatically routed to appropriate queues:

- `generate_report_async` → `reports` queue
- `generate_multiple_reports_async` → `reports` queue
- `export_scan_to_csv_async` → `reports` queue
- `send_notification_async` → `notifications` queue
- `send_event_notifications_async` → `notifications` queue
- `send_bulk_notifications_async` → `notifications` queue

### Task Time Limits

- **Hard time limit**: 5 minutes (300 seconds)
- **Soft time limit**: 4.5 minutes (270 seconds)
- Tasks exceeding these limits will be terminated

### Retry Configuration

Tasks automatically retry on failure:

- **Max retries**: 3
- **Backoff**: Exponential with jitter
- **Max backoff**: 60 seconds

## Periodic Tasks

Configured in `services/celery_beat_config.py`:

| Task | Schedule | Description |
|------|----------|-------------|
| `monitor-celery-health` | Every 5 minutes | Check Celery system health |
| `monitor-notification-health` | Every 10 minutes | Check notification service health |
| `get-notification-stats` | Every hour | Collect notification statistics |
| `cleanup-old-notifications` | Daily at 2 AM | Remove old notification records |
| `cleanup-old-reports` | Daily at 3 AM | Remove old report files |
| `get-task-statistics` | Every 6 hours | Collect task execution statistics |

## Production Deployment

### Docker Compose

```yaml
services:
  celery-worker:
    build: .
    command: python run_celery_worker.py --concurrency 4
    environment:
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_URL=postgresql://user:pass@postgres/dcs
    depends_on:
      - redis
      - postgres
    restart: unless-stopped
  
  celery-beat:
    build: .
    command: python run_celery_beat.py
    environment:
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_URL=postgresql://user:pass@postgres/dcs
    depends_on:
      - redis
      - postgres
    restart: unless-stopped
```

### Systemd Service

```ini
[Unit]
Description=Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=dcs
Group=dcs
WorkingDirectory=/opt/dcs
ExecStart=/opt/dcs/venv/bin/python run_celery_worker.py --concurrency 4
Restart=always

[Install]
WantedBy=multi-user.target
```

### Monitoring with Flower

```bash
# Install Flower
pip install flower

# Start Flower
celery -A services.celery_app flower --port=5555

# Access at http://localhost:5555
```

## Troubleshooting

### Workers Not Starting

1. Check Redis connection:
   ```bash
   redis-cli ping
   ```

2. Check configuration:
   ```python
   from core.config import get_config
   config = get_config()
   print(config.redis.url)
   ```

3. Check logs:
   ```bash
   python run_celery_worker.py --loglevel DEBUG
   ```

### Tasks Not Executing

1. Verify workers are running:
   ```bash
   celery -A services.celery_app inspect active_queues
   ```

2. Check task registration:
   ```bash
   celery -A services.celery_app inspect registered
   ```

3. Monitor task status:
   ```python
   from celery.result import AsyncResult
   result = AsyncResult('task-id')
   print(result.state, result.info)
   ```

### High Memory Usage

1. Reduce worker concurrency:
   ```bash
   python run_celery_worker.py --concurrency 2
   ```

2. Enable worker restarts:
   ```bash
   python run_celery_worker.py --max-tasks-per-child 100
   ```

3. Use autoscaling:
   ```bash
   python run_celery_worker.py --autoscale 10,2
   ```

## Best Practices

1. **Use appropriate queues**: Route tasks to specific queues for better resource management
2. **Set timeouts**: Always use timeouts when waiting for results
3. **Handle failures**: Implement proper error handling in task consumers
4. **Monitor workers**: Use monitoring tasks or Flower for production
5. **Scale appropriately**: Start with low concurrency and scale based on load
6. **Use task IDs**: Store task IDs for status tracking and cancellation
7. **Clean up results**: Set appropriate `result_expires` to avoid memory bloat

## References

- [Celery Documentation](https://docs.celeryproject.org/)
- [Redis Documentation](https://redis.io/documentation)
- [Flower Documentation](https://flower.readthedocs.io/)
