"""
Celery Beat configuration for periodic tasks.

This module defines the schedule for periodic tasks that should run automatically.
"""

from celery.schedules import crontab
from src.services.celery_app import celery_app


# Configure periodic tasks
celery_app.conf.beat_schedule = {
    # Monitor Celery health every 5 minutes
    'monitor-celery-health': {
        'task': 'monitor_celery_health',
        'schedule': 300.0,  # 5 minutes in seconds
        'options': {
            'queue': 'default',
            'expires': 60,  # Task expires after 60 seconds if not executed
        }
    },
    
    # Monitor notification health every 10 minutes
    'monitor-notification-health': {
        'task': 'monitor_notification_health',
        'schedule': 600.0,  # 10 minutes
        'options': {
            'queue': 'notifications',
            'expires': 60,
        }
    },
    
    # Get notification statistics every hour
    'get-notification-stats': {
        'task': 'get_notification_stats',
        'schedule': crontab(minute=0),  # Every hour at minute 0
        'options': {
            'queue': 'notifications',
        }
    },
    
    # Cleanup old notifications daily at 2 AM
    'cleanup-old-notifications': {
        'task': 'cleanup_old_notifications',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2:00 AM
        'kwargs': {'days': 30},
        'options': {
            'queue': 'default',
        }
    },
    
    # Cleanup old reports daily at 3 AM
    'cleanup-old-reports': {
        'task': 'cleanup_old_reports',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3:00 AM
        'kwargs': {'days': 30},
        'options': {
            'queue': 'reports',
        }
    },
    
    # Get task statistics every 6 hours
    'get-task-statistics': {
        'task': 'get_task_statistics',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
        'kwargs': {'hours': 24},
        'options': {
            'queue': 'default',
        }
    },
}

# Celery Beat configuration
celery_app.conf.update(
    beat_schedule=celery_app.conf.beat_schedule,
    timezone='UTC',
)
