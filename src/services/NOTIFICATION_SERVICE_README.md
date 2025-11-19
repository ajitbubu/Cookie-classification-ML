# Notification Service

The notification service provides multi-channel notification delivery with retry logic, templates, and asynchronous processing via Celery.

## Features

- **Multi-channel delivery**: Email (SMTP), Webhook (HTTP POST), Slack (webhook)
- **Event-driven architecture**: Register listeners for notification events
- **User preferences**: Per-user notification settings with channel and event filtering
- **Retry logic**: Exponential backoff with configurable retry attempts
- **Templates**: Pre-built templates for all event types with variable substitution
- **Async processing**: Celery integration for background notification delivery
- **Statistics tracking**: Monitor delivery success rates and retry metrics

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Notification Service                       │
├─────────────────────────────────────────────────────────────┤
│  Event System  │  Preference Mgmt  │  Template Engine       │
├─────────────────────────────────────────────────────────────┤
│           Retry Logic (Exponential Backoff)                 │
├─────────────────────────────────────────────────────────────┤
│    Email Channel  │  Webhook Channel  │  Slack Channel      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    Celery Task Queue
                            │
                            ▼
                    Redis Broker/Backend
```

## Quick Start

### 1. Initialize the Service

```python
from core.config import get_config, init_config
from services.notification_service import init_notification_service

# Initialize config
config = init_config()

# Initialize notification service
notification_service = init_notification_service(config.notification)
```

### 2. Set User Preferences

```python
from models.notification import NotificationPreferences, NotificationEvent, NotificationChannel
from uuid import uuid4

preferences = NotificationPreferences(
    user_id=uuid4(),
    enabled_events=[
        NotificationEvent.SCAN_COMPLETED,
        NotificationEvent.SCAN_FAILED,
        NotificationEvent.COMPLIANCE_VIOLATION
    ],
    enabled_channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
    email_address="user@example.com",
    slack_webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
)

notification_service.set_user_preferences(str(preferences.user_id), preferences)
```

### 3. Send Notifications

#### Synchronous (immediate)

```python
from models.notification import NotificationEvent

# Send notification
notifications = await notification_service.notify(
    event=NotificationEvent.SCAN_COMPLETED,
    data={
        'domain': 'example.com',
        'scan_id': 'abc-123',
        'duration': 45,
        'total_cookies': 23,
        'pages_scanned': 10,
        'timestamp': '2025-01-15T10:30:00Z',
        'dashboard_url': 'https://dashboard.example.com/scans/abc-123'
    },
    user_id=str(user_id)
)
```

#### Asynchronous (via Celery)

```python
from services.notification_async import trigger_event_notifications_async

# Trigger async notification
task_id = trigger_event_notifications_async(
    event=NotificationEvent.SCAN_COMPLETED,
    data={
        'domain': 'example.com',
        'scan_id': 'abc-123',
        'duration': 45,
        'total_cookies': 23,
        'pages_scanned': 10,
        'timestamp': '2025-01-15T10:30:00Z'
    },
    user_id=user_id
)

# Check task status
from services.notification_async import get_task_status
status = get_task_status(task_id)
```

### 4. Register Event Listeners

```python
async def on_scan_completed(event: NotificationEvent, data: dict):
    print(f"Scan completed: {data['domain']}")

notification_service.register_event_listener(
    NotificationEvent.SCAN_COMPLETED,
    on_scan_completed
)

# Emit event (will trigger listener and send notifications)
await notification_service.emit_event(
    NotificationEvent.SCAN_COMPLETED,
    data={'domain': 'example.com', 'scan_id': 'abc-123'},
    user_id=str(user_id)
)
```

## Configuration

### Environment Variables

```bash
# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@example.com
SMTP_USE_TLS=true

# Slack Configuration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Notification Settings
WEBHOOK_TIMEOUT=10
NOTIFICATION_MAX_RETRIES=3

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0
```

## Notification Events

- `SCAN_STARTED`: Scan has started
- `SCAN_COMPLETED`: Scan completed successfully
- `SCAN_FAILED`: Scan failed with error
- `COMPLIANCE_VIOLATION`: Compliance issue detected
- `ANOMALY_DETECTED`: Anomaly in scan results
- `SCHEDULE_CREATED`: New schedule created
- `SCHEDULE_UPDATED`: Schedule updated
- `SCHEDULE_FAILED`: Scheduled scan failed

## Notification Channels

### Email (SMTP)

Sends HTML and plain text emails using SMTP.

**Required preferences:**
- `email_address`: Recipient email address

**Template variables:**
- All event-specific data fields
- `dashboard_url`: Link to dashboard (optional)

### Webhook (HTTP POST)

Sends JSON payload to webhook URL.

**Required preferences:**
- `webhook_url`: Webhook endpoint URL

**Payload format:**
```json
{
  "event": "scan.completed",
  "data": {
    "domain": "example.com",
    "scan_id": "abc-123",
    ...
  }
}
```

### Slack

Sends formatted messages to Slack via webhook.

**Required preferences:**
- `slack_webhook_url`: Slack webhook URL

**Message format:**
- Rich formatting with color-coded attachments
- Structured fields for key information
- Emoji indicators for event types

## Templates

Templates support variable substitution using `${variable_name}` syntax.

### Customizing Templates

```python
from services.notification_templates import get_template_engine

template_engine = get_template_engine()

# Render custom email
rendered = template_engine.render_email(
    NotificationEvent.SCAN_COMPLETED,
    {
        'domain': 'example.com',
        'scan_id': 'abc-123',
        'duration': 45,
        'total_cookies': 23,
        'pages_scanned': 10,
        'timestamp': '2025-01-15T10:30:00Z'
    }
)

print(rendered['subject'])  # "Scan Completed: example.com"
print(rendered['body'])     # Plain text email body
print(rendered['html_body']) # HTML email body
```

## Retry Logic

Notifications are automatically retried on failure with exponential backoff:

- **Max retries**: 3 (configurable)
- **Base delay**: 2 seconds
- **Max delay**: 60 seconds
- **Backoff multiplier**: 2x

### Retry Statistics

```python
from services.notification_retry import get_retry_stats

stats = get_retry_stats()
print(stats.get_stats())
# {
#   'total_attempts': 100,
#   'successful_first_attempt': 85,
#   'successful_after_retry': 10,
#   'failed_after_all_retries': 5,
#   'success_rate': 95.0,
#   'average_retries': 0.15
# }
```

## Celery Workers

### Starting Workers

```bash
# Start Celery worker
celery -A services.celery_app worker --loglevel=info

# Start with specific queues
celery -A services.celery_app worker --loglevel=info -Q notifications,default

# Start with concurrency
celery -A services.celery_app worker --loglevel=info --concurrency=4
```

### Monitoring

```bash
# Monitor tasks
celery -A services.celery_app events

# Inspect active tasks
celery -A services.celery_app inspect active

# Get statistics
celery -A services.celery_app inspect stats
```

## API Endpoints

### Get Preferences

```http
GET /api/v1/notifications/preferences
Authorization: Bearer <token>
```

### Update Preferences

```http
PUT /api/v1/notifications/preferences
Authorization: Bearer <token>
Content-Type: application/json

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

### Get Supported Events

```http
GET /api/v1/notifications/events
```

### Get Supported Channels

```http
GET /api/v1/notifications/channels
```

## Testing

### Manual Testing

```python
# Test email channel
from services.notification_channels import EmailChannel
from core.config import get_config

config = get_config()
email_channel = EmailChannel(config.notification)

notification = Notification(
    notification_id=uuid4(),
    user_id=uuid4(),
    event=NotificationEvent.SCAN_COMPLETED,
    channel=NotificationChannel.EMAIL,
    data={
        'subject': 'Test Email',
        'body': 'This is a test',
        'html_body': '<p>This is a test</p>'
    }
)

success = await email_channel.send(
    notification,
    {'email_address': 'test@example.com'}
)
```

### Integration Testing

```python
# Test full notification flow
from services.notification_service import get_notification_service

service = get_notification_service()

# Set up test preferences
preferences = NotificationPreferences(
    user_id=test_user_id,
    enabled_events=[NotificationEvent.SCAN_COMPLETED],
    enabled_channels=[NotificationChannel.EMAIL],
    email_address='test@example.com'
)
service.set_user_preferences(str(test_user_id), preferences)

# Send test notification
notifications = await service.notify(
    NotificationEvent.SCAN_COMPLETED,
    {'domain': 'test.com', 'scan_id': 'test-123'},
    str(test_user_id)
)

assert len(notifications) == 1
assert notifications[0].status == NotificationStatus.SENT
```

## Troubleshooting

### Notifications Not Sending

1. Check user preferences are set correctly
2. Verify event is enabled in preferences
3. Verify channel is enabled in preferences
4. Check channel-specific configuration (SMTP, webhook URLs)
5. Review logs for error messages

### SMTP Errors

- Verify SMTP credentials
- Check firewall/network connectivity
- Enable "Less secure app access" for Gmail
- Use app-specific password for Gmail

### Celery Tasks Not Processing

- Verify Redis is running
- Check Celery worker is started
- Review Celery logs for errors
- Verify task serialization (all data must be JSON-serializable)

### High Retry Rates

- Check external service availability (SMTP server, webhook endpoints)
- Review network connectivity
- Increase timeout values if needed
- Check rate limiting on external services

## Best Practices

1. **Use async delivery for non-critical notifications**: Improves API response times
2. **Set appropriate quiet hours**: Respect user preferences for notification timing
3. **Monitor retry statistics**: Identify and fix persistent delivery issues
4. **Use templates consistently**: Maintain professional, consistent messaging
5. **Test with real services**: Verify SMTP, webhooks work in staging environment
6. **Handle failures gracefully**: Log errors but don't block main application flow
7. **Clean up old data**: Implement periodic cleanup of old notification records

## Future Enhancements

- Database persistence for notification history
- Additional channels (SMS, push notifications)
- Custom template management via API
- Notification batching and digest emails
- Advanced filtering and routing rules
- Delivery analytics and reporting dashboard
