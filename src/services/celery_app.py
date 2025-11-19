"""
Celery application configuration for async task processing.
"""

import logging
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
from src.core.config import get_config

logger = logging.getLogger(__name__)


def create_celery_app() -> Celery:
    """
    Create and configure Celery application.
    
    Returns:
        Configured Celery instance
    """
    import os
    
    try:
        config = get_config()
        redis_url = config.redis.url
    except RuntimeError:
        # Fallback to environment variable or default
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        logger.warning(f"Config not initialized, using Redis URL from env: {redis_url}")
    
    # Create Celery app
    app = Celery(
        'dcs_tasks',
        broker=redis_url,
        backend=redis_url
    )
    
    # Configure Celery
    app.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=300,  # 5 minutes
        task_soft_time_limit=270,  # 4.5 minutes
        worker_prefetch_multiplier=4,
        worker_max_tasks_per_child=1000,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        result_expires=3600,  # 1 hour
        broker_connection_retry_on_startup=True,
        # Task routing
        task_routes={
            'execute_scan_async': {'queue': 'scans'},
            'cancel_scan_async': {'queue': 'scans'},
            'generate_report_async': {'queue': 'reports'},
            'generate_multiple_reports_async': {'queue': 'reports'},
            'export_scan_to_csv_async': {'queue': 'reports'},
            'send_notification_async': {'queue': 'notifications'},
            'send_event_notifications_async': {'queue': 'notifications'},
            'send_bulk_notifications_async': {'queue': 'notifications'},
        },
        # Default queue
        task_default_queue='default',
        task_default_exchange='default',
        task_default_routing_key='default',
    )
    
    logger.info("Celery app created and configured")
    return app


# Global Celery app instance - will be created lazily
_celery_app = None


def get_celery_app() -> Celery:
    """Get or create the Celery app instance."""
    global _celery_app
    if _celery_app is None:
        _celery_app = create_celery_app()
    return _celery_app


# For backward compatibility
celery_app = create_celery_app()


# Task signal handlers for monitoring and logging
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **extra_kwargs):
    """Log when a task starts."""
    logger.info(f"Task started: {task.name} (ID: {task_id})")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, **extra_kwargs):
    """Log when a task completes."""
    logger.info(f"Task completed: {task.name} (ID: {task_id})")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **extra_kwargs):
    """Log when a task fails."""
    logger.error(f"Task failed: {sender.name} (ID: {task_id}), Error: {exception}", exc_info=einfo)


# Auto-discover tasks from modules
def autodiscover_tasks():
    """Auto-discover and register all Celery tasks."""
    try:
        # Import task modules to register tasks
        from services import notification_tasks
        from services import report_tasks
        from services import celery_monitoring
        from services import scan_tasks
        
        logger.info("Celery tasks auto-discovered and registered")
    except Exception as e:
        logger.error(f"Error auto-discovering tasks: {e}", exc_info=True)


# Call autodiscover on module load
autodiscover_tasks()
