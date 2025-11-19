"""
Celery tasks for asynchronous notification delivery.
"""

import logging
import asyncio
from typing import Dict, Any
from uuid import UUID
from celery import Task
from src.services.celery_app import celery_app
from src.models.notification import (
    Notification,
    NotificationEvent,
    NotificationChannel,
    NotificationPreferences
)
from src.services.notification_service import get_notification_service
from src.core.config import get_config, init_config

logger = logging.getLogger(__name__)


class NotificationTask(Task):
    """Base task class for notification tasks with error handling."""
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True
    retry_backoff_max = 60
    retry_jitter = True


@celery_app.task(
    bind=True,
    base=NotificationTask,
    name='send_notification_async'
)
def send_notification_async(
    self,
    notification_data: Dict[str, Any],
    preferences_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Send notification asynchronously via Celery.
    
    Args:
        notification_data: Notification data dictionary
        preferences_data: User preferences data dictionary
        
    Returns:
        Result dictionary with status and details
    """
    try:
        # Initialize config if not already done
        try:
            get_config()
        except RuntimeError:
            init_config()
        
        # Reconstruct notification and preferences objects
        notification = Notification(**notification_data)
        preferences = NotificationPreferences(**preferences_data)
        
        # Get notification service
        notification_service = get_notification_service()
        
        # Send notification with retry logic
        # Run async function in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success = loop.run_until_complete(
                notification_service.send_notification_with_retry(
                    notification,
                    preferences
                )
            )
        finally:
            loop.close()
        
        result = {
            'notification_id': str(notification.notification_id),
            'status': notification.status.value,
            'success': success,
            'retry_count': notification.retry_count,
            'error': notification.error
        }
        
        logger.info(
            f"Async notification task completed: {notification.notification_id}, "
            f"success={success}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in send_notification_async task: {e}", exc_info=True)
        # Re-raise to trigger Celery retry
        raise


@celery_app.task(
    bind=True,
    base=NotificationTask,
    name='send_event_notifications_async'
)
def send_event_notifications_async(
    self,
    event: str,
    data: Dict[str, Any],
    user_id: str
) -> Dict[str, Any]:
    """
    Send notifications for an event asynchronously.
    
    Args:
        event: Event type string
        data: Event data
        user_id: User ID to notify
        
    Returns:
        Result dictionary with notification statuses
    """
    try:
        # Initialize config if not already done
        try:
            get_config()
        except RuntimeError:
            init_config()
        
        # Convert event string to enum
        event_enum = NotificationEvent(event)
        
        # Get notification service
        notification_service = get_notification_service()
        
        # Send notifications
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            notifications = loop.run_until_complete(
                notification_service.notify(event_enum, data, user_id)
            )
        finally:
            loop.close()
        
        result = {
            'event': event,
            'user_id': user_id,
            'notifications_sent': len(notifications),
            'notifications': [
                {
                    'notification_id': str(n.notification_id),
                    'channel': n.channel.value,
                    'status': n.status.value
                }
                for n in notifications
            ]
        }
        
        logger.info(
            f"Async event notifications task completed: {event}, "
            f"sent {len(notifications)} notifications"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in send_event_notifications_async task: {e}", exc_info=True)
        # Re-raise to trigger Celery retry
        raise


@celery_app.task(
    bind=True,
    name='send_bulk_notifications_async'
)
def send_bulk_notifications_async(
    self,
    event: str,
    data: Dict[str, Any],
    user_ids: list[str]
) -> Dict[str, Any]:
    """
    Send notifications to multiple users asynchronously.
    
    Args:
        event: Event type string
        data: Event data
        user_ids: List of user IDs to notify
        
    Returns:
        Result dictionary with summary
    """
    try:
        # Initialize config if not already done
        try:
            get_config()
        except RuntimeError:
            init_config()
        
        # Convert event string to enum
        event_enum = NotificationEvent(event)
        
        # Get notification service
        notification_service = get_notification_service()
        
        # Send notifications to all users
        total_notifications = 0
        successful_users = 0
        failed_users = 0
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            for user_id in user_ids:
                try:
                    notifications = loop.run_until_complete(
                        notification_service.notify(event_enum, data, user_id)
                    )
                    total_notifications += len(notifications)
                    successful_users += 1
                except Exception as e:
                    logger.error(f"Failed to notify user {user_id}: {e}")
                    failed_users += 1
        finally:
            loop.close()
        
        result = {
            'event': event,
            'total_users': len(user_ids),
            'successful_users': successful_users,
            'failed_users': failed_users,
            'total_notifications': total_notifications
        }
        
        logger.info(
            f"Bulk notifications task completed: {event}, "
            f"{successful_users}/{len(user_ids)} users notified"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in send_bulk_notifications_async task: {e}", exc_info=True)
        # Re-raise to trigger Celery retry
        raise


@celery_app.task(name='cleanup_old_notifications')
def cleanup_old_notifications(days: int = 30) -> Dict[str, Any]:
    """
    Clean up old notification records (placeholder for future implementation).
    
    Args:
        days: Number of days to keep notifications
        
    Returns:
        Result dictionary with cleanup summary
    """
    try:
        # TODO: Implement cleanup logic when notification persistence is added
        logger.info(f"Cleanup task executed for notifications older than {days} days")
        
        return {
            'status': 'completed',
            'days': days,
            'deleted_count': 0  # Placeholder
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_notifications task: {e}", exc_info=True)
        raise


# Task monitoring helpers
@celery_app.task(name='get_notification_stats')
def get_notification_stats() -> Dict[str, Any]:
    """
    Get notification delivery statistics.
    
    Returns:
        Statistics dictionary
    """
    try:
        from src.services.notification_retry import get_retry_stats
        
        retry_stats = get_retry_stats()
        stats = retry_stats.get_stats()
        
        logger.info("Retrieved notification statistics")
        return stats
        
    except Exception as e:
        logger.error(f"Error getting notification stats: {e}", exc_info=True)
        return {}


# Periodic task for monitoring (can be configured with Celery Beat)
@celery_app.task(name='monitor_notification_health')
def monitor_notification_health() -> Dict[str, Any]:
    """
    Monitor notification service health.
    
    Returns:
        Health status dictionary
    """
    try:
        # Initialize config if not already done
        try:
            get_config()
        except RuntimeError:
            init_config()
        
        # Get notification service
        notification_service = get_notification_service()
        
        # Check service health
        health = {
            'status': 'healthy',
            'supported_channels': [c.value for c in notification_service.get_supported_channels()],
            'supported_events': [e.value for e in notification_service.get_supported_events()],
            'active_preferences': len(notification_service.preferences)
        }
        
        logger.info("Notification health check completed")
        return health
        
    except Exception as e:
        logger.error(f"Error in notification health check: {e}", exc_info=True)
        return {
            'status': 'unhealthy',
            'error': str(e)
        }
