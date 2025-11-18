"""
Repository for managing notification preferences in database and cache.
"""

import logging
import json
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from models.notification import NotificationPreferences, NotificationEvent, NotificationChannel
from cache.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class NotificationPreferencesRepository:
    """
    Repository for notification preferences with Redis caching.
    
    Note: This implementation uses Redis as the primary storage.
    For production, consider adding PostgreSQL persistence.
    """
    
    def __init__(self):
        """Initialize the repository."""
        self.redis_client = get_redis_client()
        self.cache_prefix = "notification_preferences"
        self.cache_ttl = 1800  # 30 minutes
    
    def _get_cache_key(self, user_id: UUID) -> str:
        """
        Get cache key for user preferences.
        
        Args:
            user_id: User ID
            
        Returns:
            Cache key string
        """
        return f"{self.cache_prefix}:{str(user_id)}"
    
    def get_preferences(self, user_id: UUID) -> Optional[NotificationPreferences]:
        """
        Get notification preferences for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            NotificationPreferences or None if not found
        """
        try:
            cache_key = self._get_cache_key(user_id)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                preferences = NotificationPreferences(**data)
                logger.debug(f"Retrieved preferences from cache for user {user_id}")
                return preferences
            
            logger.debug(f"No preferences found for user {user_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving preferences for user {user_id}: {e}", exc_info=True)
            return None
    
    def save_preferences(self, preferences: NotificationPreferences) -> bool:
        """
        Save notification preferences for a user.
        
        Args:
            preferences: NotificationPreferences to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            cache_key = self._get_cache_key(preferences.user_id)
            
            # Update timestamp
            preferences.updated_at = datetime.utcnow()
            
            # Serialize to JSON
            data = preferences.model_dump(mode='json')
            json_data = json.dumps(data)
            
            # Save to Redis
            self.redis_client.set(
                cache_key,
                json_data,
                ttl=self.cache_ttl
            )
            
            logger.info(f"Saved preferences for user {preferences.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving preferences for user {preferences.user_id}: {e}", exc_info=True)
            return False
    
    def update_preferences(
        self,
        user_id: UUID,
        updates: dict
    ) -> Optional[NotificationPreferences]:
        """
        Update notification preferences for a user.
        
        Args:
            user_id: User ID
            updates: Dictionary of fields to update
            
        Returns:
            Updated NotificationPreferences or None if failed
        """
        try:
            # Get existing preferences
            preferences = self.get_preferences(user_id)
            
            if not preferences:
                # Create new preferences if none exist
                preferences = NotificationPreferences(
                    user_id=user_id,
                    enabled_events=[],
                    enabled_channels=[]
                )
            
            # Update fields
            for key, value in updates.items():
                if hasattr(preferences, key):
                    setattr(preferences, key, value)
            
            # Save updated preferences
            success = self.save_preferences(preferences)
            
            if success:
                return preferences
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error updating preferences for user {user_id}: {e}", exc_info=True)
            return None
    
    def delete_preferences(self, user_id: UUID) -> bool:
        """
        Delete notification preferences for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            cache_key = self._get_cache_key(user_id)
            self.redis_client.delete(cache_key)
            logger.info(f"Deleted preferences for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting preferences for user {user_id}: {e}", exc_info=True)
            return False
    
    def get_all_users_with_event_enabled(
        self,
        event: NotificationEvent
    ) -> List[NotificationPreferences]:
        """
        Get all users who have a specific event enabled.
        
        Note: This is a simplified implementation that scans Redis keys.
        For production with many users, consider using PostgreSQL with indexes.
        
        Args:
            event: Event to check
            
        Returns:
            List of NotificationPreferences with the event enabled
        """
        try:
            # Get all preference keys using SCAN
            pattern = f"{self.cache_prefix}:*"
            keys = []
            
            # Use Redis SCAN command (synchronous)
            cursor = '0'
            while cursor != 0:
                cursor, batch = self.redis_client.client.scan(
                    cursor=int(cursor) if isinstance(cursor, str) else cursor,
                    match=pattern,
                    count=100
                )
                keys.extend(batch)
            
            # Get preferences for each key
            preferences_list = []
            for key in keys:
                cached_data = self.redis_client.get(key)
                if cached_data:
                    data = json.loads(cached_data)
                    preferences = NotificationPreferences(**data)
                    
                    # Check if event is enabled
                    if event in preferences.enabled_events:
                        preferences_list.append(preferences)
            
            logger.debug(f"Found {len(preferences_list)} users with event {event} enabled")
            return preferences_list
            
        except Exception as e:
            logger.error(f"Error getting users with event {event} enabled: {e}", exc_info=True)
            return []
    
    def create_default_preferences(self, user_id: UUID) -> NotificationPreferences:
        """
        Create default notification preferences for a new user.
        
        Args:
            user_id: User ID
            
        Returns:
            Created NotificationPreferences
        """
        preferences = NotificationPreferences(
            user_id=user_id,
            enabled_events=[
                NotificationEvent.SCAN_COMPLETED,
                NotificationEvent.SCAN_FAILED,
                NotificationEvent.COMPLIANCE_VIOLATION,
                NotificationEvent.ANOMALY_DETECTED
            ],
            enabled_channels=[NotificationChannel.EMAIL],
            email_address=None,  # To be set by user
            webhook_url=None,
            slack_webhook_url=None,
            quiet_hours=None
        )
        
        self.save_preferences(preferences)
        logger.info(f"Created default preferences for user {user_id}")
        return preferences


# Global repository instance
_preferences_repository: Optional[NotificationPreferencesRepository] = None


def get_preferences_repository() -> NotificationPreferencesRepository:
    """Get the global preferences repository instance."""
    global _preferences_repository
    if _preferences_repository is None:
        _preferences_repository = NotificationPreferencesRepository()
    return _preferences_repository
