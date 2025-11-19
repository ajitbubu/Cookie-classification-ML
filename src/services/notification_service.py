"""
Event-driven notification service for multi-channel notification delivery.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime
from uuid import uuid4
from src.models.notification import (
    Notification,
    NotificationEvent,
    NotificationChannel as ChannelEnum,
    NotificationStatus,
    NotificationPreferences
)
from src.services.notification_channels import NotificationChannel, ChannelFactory
from src.services.notification_retry import RetryableNotificationDelivery, get_retry_stats
from src.services.notification_templates import get_template_engine
from src.core.config import NotificationConfig

logger = logging.getLogger(__name__)


EventListener = Callable[[NotificationEvent, Dict[str, Any]], Awaitable[None]]


class NotificationService:
    """
    Event-driven notification service that manages notification delivery
    across multiple channels based on user preferences.
    """
    
    def __init__(self, config: NotificationConfig):
        """
        Initialize notification service.
        
        Args:
            config: Notification configuration
        """
        self.config = config
        self.channels: Dict[ChannelEnum, NotificationChannel] = ChannelFactory.create_all_channels(config)
        self.preferences: Dict[str, NotificationPreferences] = {}
        self.event_listeners: Dict[NotificationEvent, List[EventListener]] = {}
        self.event_to_notification_mapping: Dict[NotificationEvent, List[ChannelEnum]] = {}
        self.retry_delivery = RetryableNotificationDelivery(
            max_retries=config.notification_max_retries,
            base_delay=2.0,
            max_delay=60.0
        )
        self.template_engine = get_template_engine()
        
        # Initialize default event-to-notification mappings
        self._initialize_default_mappings()
        
        logger.info("Notification service initialized")
    
    def _initialize_default_mappings(self):
        """Initialize default event-to-notification channel mappings."""
        # All events can use all channels by default
        for event in NotificationEvent:
            self.event_to_notification_mapping[event] = [
                ChannelEnum.EMAIL,
                ChannelEnum.WEBHOOK,
                ChannelEnum.SLACK
            ]
    
    def register_event_listener(
        self,
        event: NotificationEvent,
        listener: EventListener
    ):
        """
        Register an event listener for a specific event type.
        
        Args:
            event: Event type to listen for
            listener: Async callback function to invoke when event occurs
        """
        if event not in self.event_listeners:
            self.event_listeners[event] = []
        
        self.event_listeners[event].append(listener)
        logger.info(f"Registered event listener for {event}")
    
    def unregister_event_listener(
        self,
        event: NotificationEvent,
        listener: EventListener
    ):
        """
        Unregister an event listener.
        
        Args:
            event: Event type
            listener: Listener to remove
        """
        if event in self.event_listeners:
            try:
                self.event_listeners[event].remove(listener)
                logger.info(f"Unregistered event listener for {event}")
            except ValueError:
                logger.warning(f"Listener not found for event {event}")
    
    async def emit_event(
        self,
        event: NotificationEvent,
        data: Dict[str, Any],
        user_id: Optional[str] = None
    ):
        """
        Emit an event and trigger all registered listeners.
        
        Args:
            event: Event type
            data: Event data
            user_id: Optional user ID to notify
        """
        logger.info(f"Event emitted: {event} with data: {data}")
        
        # Trigger event listeners
        if event in self.event_listeners:
            tasks = []
            for listener in self.event_listeners[event]:
                tasks.append(listener(event, data))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        
        # Send notifications if user_id is provided
        if user_id:
            await self.notify(event, data, user_id)
    
    def set_user_preferences(self, user_id: str, preferences: NotificationPreferences):
        """
        Set notification preferences for a user.
        
        Args:
            user_id: User ID
            preferences: User's notification preferences
        """
        self.preferences[user_id] = preferences
        logger.info(f"Updated notification preferences for user {user_id}")
    
    def get_user_preferences(self, user_id: str) -> Optional[NotificationPreferences]:
        """
        Get notification preferences for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            User's notification preferences or None if not set
        """
        return self.preferences.get(user_id)
    
    def remove_user_preferences(self, user_id: str):
        """
        Remove notification preferences for a user.
        
        Args:
            user_id: User ID
        """
        if user_id in self.preferences:
            del self.preferences[user_id]
            logger.info(f"Removed notification preferences for user {user_id}")
    
    def _should_send_notification(
        self,
        event: NotificationEvent,
        channel: ChannelEnum,
        preferences: NotificationPreferences
    ) -> bool:
        """
        Check if notification should be sent based on user preferences.
        
        Args:
            event: Event type
            channel: Notification channel
            preferences: User preferences
            
        Returns:
            True if notification should be sent, False otherwise
        """
        # Check if event is enabled
        if event not in preferences.enabled_events:
            return False
        
        # Check if channel is enabled
        if channel not in preferences.enabled_channels:
            return False
        
        # Check quiet hours if configured
        if preferences.quiet_hours:
            current_hour = datetime.utcnow().hour
            start_hour = preferences.quiet_hours.get('start_hour', 0)
            end_hour = preferences.quiet_hours.get('end_hour', 0)
            
            if start_hour <= current_hour < end_hour:
                logger.info(f"Skipping notification during quiet hours for user {preferences.user_id}")
                return False
        
        return True
    
    def _get_recipient_config(
        self,
        channel: ChannelEnum,
        preferences: NotificationPreferences
    ) -> Dict[str, Any]:
        """
        Get recipient configuration for a specific channel.
        
        Args:
            channel: Notification channel
            preferences: User preferences
            
        Returns:
            Recipient configuration dictionary
        """
        if channel == ChannelEnum.EMAIL:
            return {'email_address': preferences.email_address}
        elif channel == ChannelEnum.WEBHOOK:
            return {'webhook_url': preferences.webhook_url}
        elif channel == ChannelEnum.SLACK:
            return {'slack_webhook_url': preferences.slack_webhook_url}
        else:
            return {}
    
    def _prepare_notification_data(
        self,
        event: NotificationEvent,
        channel: ChannelEnum,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare notification data using templates.
        
        Args:
            event: Event type
            channel: Notification channel
            data: Raw event data
            
        Returns:
            Prepared notification data with rendered templates
        """
        if channel == ChannelEnum.EMAIL:
            rendered = self.template_engine.render_email(event, data)
            return {
                'subject': rendered['subject'],
                'body': rendered['body'],
                'html_body': rendered['html_body'],
                **data
            }
        elif channel == ChannelEnum.SLACK:
            rendered = self.template_engine.render_slack(event, data)
            return rendered
        elif channel == ChannelEnum.WEBHOOK:
            rendered = self.template_engine.render_webhook(event, data)
            return rendered
        else:
            return data
    
    async def notify(
        self,
        event: NotificationEvent,
        data: Dict[str, Any],
        user_id: str
    ) -> List[Notification]:
        """
        Send notification to user based on their preferences.
        
        Args:
            event: Event that triggered notification
            data: Notification data/payload
            user_id: User ID to notify
            
        Returns:
            List of created notifications
        """
        # Get user preferences
        preferences = self.get_user_preferences(user_id)
        if not preferences:
            logger.warning(f"No notification preferences found for user {user_id}")
            return []
        
        # Get available channels for this event
        available_channels = self.event_to_notification_mapping.get(event, [])
        
        # Create notifications for each enabled channel
        notifications = []
        for channel in available_channels:
            if self._should_send_notification(event, channel, preferences):
                # Prepare notification data with templates
                notification_data = self._prepare_notification_data(event, channel, data)
                
                notification = Notification(
                    notification_id=uuid4(),
                    user_id=preferences.user_id,
                    event=event,
                    channel=channel,
                    status=NotificationStatus.PENDING,
                    data=notification_data,
                    created_at=datetime.utcnow()
                )
                notifications.append(notification)
        
        # Send notifications
        if notifications:
            await self._send_notifications(notifications, preferences)
        
        return notifications
    
    async def _send_notifications(
        self,
        notifications: List[Notification],
        preferences: NotificationPreferences
    ):
        """
        Send multiple notifications concurrently.
        
        Args:
            notifications: List of notifications to send
            preferences: User preferences for recipient configuration
        """
        tasks = []
        for notification in notifications:
            task = self._send_single_notification(notification, preferences)
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_single_notification(
        self,
        notification: Notification,
        preferences: NotificationPreferences
    ):
        """
        Send a single notification through its channel.
        
        Args:
            notification: Notification to send
            preferences: User preferences for recipient configuration
        """
        try:
            # Increment retry count
            if notification.status == NotificationStatus.RETRYING:
                notification.retry_count += 1
            
            # Get channel instance
            channel = self.channels.get(notification.channel)
            if not channel:
                logger.error(f"Channel not found: {notification.channel}")
                notification.status = NotificationStatus.FAILED
                notification.error = f"Channel not available: {notification.channel}"
                return
            
            # Get recipient configuration
            recipient_config = self._get_recipient_config(notification.channel, preferences)
            
            # Send notification
            success = await channel.send(notification, recipient_config)
            
            if success:
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.utcnow()
                logger.info(
                    f"Notification {notification.notification_id} sent successfully "
                    f"via {notification.channel} for event {notification.event}"
                )
            else:
                notification.status = NotificationStatus.FAILED
                notification.error = "Channel send failed"
                logger.error(
                    f"Failed to send notification {notification.notification_id} "
                    f"via {notification.channel}"
                )
                
        except Exception as e:
            notification.status = NotificationStatus.FAILED
            notification.error = str(e)
            logger.error(
                f"Error sending notification {notification.notification_id}: {e}",
                exc_info=True
            )
    
    async def send_notification_with_retry(
        self,
        notification: Notification,
        preferences: NotificationPreferences
    ) -> bool:
        """
        Send notification with retry logic and exponential backoff.
        
        Args:
            notification: Notification to send
            preferences: User preferences
            
        Returns:
            True if sent successfully, False otherwise
        """
        notification.status = NotificationStatus.RETRYING
        retry_stats = get_retry_stats()
        
        # Create delivery function
        async def delivery_func():
            await self._send_single_notification(notification, preferences)
            return notification.status == NotificationStatus.SENT
        
        # Attempt delivery with retry
        success, error = await self.retry_delivery.deliver_with_retry(delivery_func)
        
        if success:
            retry_stats.record_success(notification.retry_count)
            logger.info(
                f"Notification {notification.notification_id} sent successfully "
                f"after {notification.retry_count + 1} attempt(s)"
            )
            return True
        else:
            retry_stats.record_failure(notification.retry_count + 1)
            notification.status = NotificationStatus.FAILED
            notification.error = error or "Failed after all retry attempts"
            logger.error(
                f"Notification {notification.notification_id} failed after "
                f"{notification.retry_count + 1} attempts: {error}"
            )
            return False
    
    def get_supported_channels(self) -> List[ChannelEnum]:
        """
        Get list of supported notification channels.
        
        Returns:
            List of supported channel types
        """
        return list(self.channels.keys())
    
    def get_supported_events(self) -> List[NotificationEvent]:
        """
        Get list of supported notification events.
        
        Returns:
            List of supported event types
        """
        return list(NotificationEvent)


# Global notification service instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get the global notification service instance."""
    global _notification_service
    if _notification_service is None:
        raise RuntimeError("Notification service not initialized. Call init_notification_service() first.")
    return _notification_service


def init_notification_service(config: NotificationConfig) -> NotificationService:
    """
    Initialize the global notification service instance.
    
    Args:
        config: Notification configuration
        
    Returns:
        Initialized NotificationService instance
    """
    global _notification_service
    _notification_service = NotificationService(config)
    logger.info("Global notification service initialized")
    return _notification_service
