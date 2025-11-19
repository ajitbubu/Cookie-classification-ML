"""
Helper functions for triggering asynchronous notification delivery via Celery.
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from src.models.notification import Notification, NotificationEvent, NotificationPreferences
from src.services.notification_tasks import (
    send_notification_async,
    send_event_notifications_async,
    send_bulk_notifications_async
)

logger = logging.getLogger(__name__)


def trigger_notification_async(
    notification: Notification,
    preferences: NotificationPreferences,
    countdown: Optional[int] = None,
    eta: Optional[Any] = None
) -> str:
    """
    Trigger asynchronous notification delivery via Celery.
    
    Args:
        notification: Notification to send
        preferences: User preferences
        countdown: Delay in seconds before executing task
        eta: Specific datetime to execute task
        
    Returns:
        Celery task ID
    """
    try:
        # Convert objects to dictionaries for serialization
        notification_data = notification.model_dump(mode='json')
        preferences_data = preferences.model_dump(mode='json')
        
        # Trigger Celery task
        task = send_notification_async.apply_async(
            args=[notification_data, preferences_data],
            countdown=countdown,
            eta=eta
        )
        
        logger.info(
            f"Triggered async notification task {task.id} for "
            f"notification {notification.notification_id}"
        )
        
        return task.id
        
    except Exception as e:
        logger.error(f"Failed to trigger async notification: {e}", exc_info=True)
        raise


def trigger_event_notifications_async(
    event: NotificationEvent,
    data: Dict[str, Any],
    user_id: UUID,
    countdown: Optional[int] = None,
    eta: Optional[Any] = None
) -> str:
    """
    Trigger asynchronous event notifications via Celery.
    
    Args:
        event: Event type
        data: Event data
        user_id: User ID to notify
        countdown: Delay in seconds before executing task
        eta: Specific datetime to execute task
        
    Returns:
        Celery task ID
    """
    try:
        # Trigger Celery task
        task = send_event_notifications_async.apply_async(
            args=[event.value, data, str(user_id)],
            countdown=countdown,
            eta=eta
        )
        
        logger.info(
            f"Triggered async event notifications task {task.id} for "
            f"event {event.value}, user {user_id}"
        )
        
        return task.id
        
    except Exception as e:
        logger.error(f"Failed to trigger async event notifications: {e}", exc_info=True)
        raise


def trigger_bulk_notifications_async(
    event: NotificationEvent,
    data: Dict[str, Any],
    user_ids: List[UUID],
    countdown: Optional[int] = None,
    eta: Optional[Any] = None
) -> str:
    """
    Trigger asynchronous bulk notifications via Celery.
    
    Args:
        event: Event type
        data: Event data
        user_ids: List of user IDs to notify
        countdown: Delay in seconds before executing task
        eta: Specific datetime to execute task
        
    Returns:
        Celery task ID
    """
    try:
        # Convert UUIDs to strings
        user_id_strs = [str(uid) for uid in user_ids]
        
        # Trigger Celery task
        task = send_bulk_notifications_async.apply_async(
            args=[event.value, data, user_id_strs],
            countdown=countdown,
            eta=eta
        )
        
        logger.info(
            f"Triggered async bulk notifications task {task.id} for "
            f"event {event.value}, {len(user_ids)} users"
        )
        
        return task.id
        
    except Exception as e:
        logger.error(f"Failed to trigger async bulk notifications: {e}", exc_info=True)
        raise


def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get status of a Celery task.
    
    Args:
        task_id: Celery task ID
        
    Returns:
        Task status dictionary
    """
    try:
        from src.services.celery_app import celery_app
        
        result = celery_app.AsyncResult(task_id)
        
        return {
            'task_id': task_id,
            'state': result.state,
            'ready': result.ready(),
            'successful': result.successful() if result.ready() else None,
            'result': result.result if result.ready() else None,
            'traceback': result.traceback if result.failed() else None
        }
        
    except Exception as e:
        logger.error(f"Failed to get task status for {task_id}: {e}", exc_info=True)
        return {
            'task_id': task_id,
            'state': 'UNKNOWN',
            'error': str(e)
        }


def cancel_task(task_id: str) -> bool:
    """
    Cancel a Celery task.
    
    Args:
        task_id: Celery task ID
        
    Returns:
        True if cancelled successfully
    """
    try:
        from src.services.celery_app import celery_app
        
        celery_app.control.revoke(task_id, terminate=True)
        logger.info(f"Cancelled task {task_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}", exc_info=True)
        return False
