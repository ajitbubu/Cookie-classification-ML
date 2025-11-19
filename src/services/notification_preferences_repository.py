"""
Repository for managing notification preferences in database and cache.
"""

import logging
import json
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime
import asyncpg

from src.models.notification import NotificationPreferences, NotificationEvent, NotificationChannel
from src.cache.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class NotificationPreferencesRepository:
    """
    Repository for notification preferences with database persistence and Redis caching.
    
    Uses PostgreSQL as primary storage with Redis for caching.
    """
    
    def __init__(self, db_pool: Optional[asyncpg.Pool] = None):
        """
        Initialize the repository.
        
        Args:
            db_pool: Database connection pool (optional, will use global if not provided)
        """
        self.db_pool = db_pool
        try:
            self.redis_client = get_redis_client()
        except Exception as e:
            logger.warning(f"Redis client not available: {e}")
            self.redis_client = None
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
    
    async def get_preferences(self, user_id: UUID) -> Optional[NotificationPreferences]:
        """
        Get notification preferences for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            NotificationPreferences or None if not found
        """
        try:
            # Try cache first
            if self.redis_client:
                cache_key = self._get_cache_key(user_id)
                cached_data = self.redis_client.get(cache_key)
                
                if cached_data:
                    data = json.loads(cached_data)
                    preferences = NotificationPreferences(**data)
                    logger.debug(f"Retrieved preferences from cache for user {user_id}")
                    return preferences
            
            # Get from database
            if not self.db_pool:
                from src.api.main import get_db_pool
                self.db_pool = get_db_pool()
            
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT preference_id, user_id, enabled_events, enabled_channels,
                           email_address, webhook_url, slack_webhook_url, quiet_hours,
                           created_at, updated_at
                    FROM notification_preferences
                    WHERE user_id = $1
                    """,
                    user_id
                )
                
                if not row:
                    logger.debug(f"No preferences found for user {user_id}")
                    return None
                
                # Parse JSON fields
                enabled_events = [NotificationEvent(e) for e in row['enabled_events']]
                enabled_channels = [NotificationChannel(c) for c in row['enabled_channels']]
                
                preferences = NotificationPreferences(
                    user_id=row['user_id'],
                    enabled_events=enabled_events,
                    enabled_channels=enabled_channels,
                    email_address=row['email_address'],
                    webhook_url=row['webhook_url'],
                    slack_webhook_url=row['slack_webhook_url'],
                    quiet_hours=row['quiet_hours'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                
                # Cache the result
                if self.redis_client:
                    await self._cache_preferences(preferences)
                
                logger.debug(f"Retrieved preferences from database for user {user_id}")
                return preferences
            
        except Exception as e:
            logger.error(f"Error retrieving preferences for user {user_id}: {e}", exc_info=True)
            return None
    
    async def save_preferences(self, preferences: NotificationPreferences) -> bool:
        """
        Save notification preferences for a user.
        
        Args:
            preferences: NotificationPreferences to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Update timestamp
            preferences.updated_at = datetime.utcnow()
            
            # Save to database
            if not self.db_pool:
                from src.api.main import get_db_pool
                self.db_pool = get_db_pool()
            
            async with self.db_pool.acquire() as conn:
                # Convert enums to strings for JSON storage
                enabled_events_json = json.dumps([e.value for e in preferences.enabled_events])
                enabled_channels_json = json.dumps([c.value for c in preferences.enabled_channels])
                quiet_hours_json = json.dumps(preferences.quiet_hours) if preferences.quiet_hours else None
                
                # Upsert preferences
                await conn.execute(
                    """
                    INSERT INTO notification_preferences (
                        user_id, enabled_events, enabled_channels,
                        email_address, webhook_url, slack_webhook_url,
                        quiet_hours, created_at, updated_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (user_id) DO UPDATE SET
                        enabled_events = EXCLUDED.enabled_events,
                        enabled_channels = EXCLUDED.enabled_channels,
                        email_address = EXCLUDED.email_address,
                        webhook_url = EXCLUDED.webhook_url,
                        slack_webhook_url = EXCLUDED.slack_webhook_url,
                        quiet_hours = EXCLUDED.quiet_hours,
                        updated_at = EXCLUDED.updated_at
                    """,
                    preferences.user_id,
                    enabled_events_json,
                    enabled_channels_json,
                    preferences.email_address,
                    preferences.webhook_url,
                    preferences.slack_webhook_url,
                    quiet_hours_json,
                    preferences.created_at or datetime.utcnow(),
                    preferences.updated_at
                )
            
            # Cache the result
            if self.redis_client:
                await self._cache_preferences(preferences)
            
            logger.info(f"Saved preferences for user {preferences.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving preferences for user {preferences.user_id}: {e}", exc_info=True)
            return False
    
    async def _cache_preferences(self, preferences: NotificationPreferences):
        """Cache preferences in Redis."""
        try:
            if not self.redis_client:
                return
            
            cache_key = self._get_cache_key(preferences.user_id)
            data = preferences.model_dump(mode='json')
            json_data = json.dumps(data)
            
            self.redis_client.set(
                cache_key,
                json_data,
                ttl=self.cache_ttl
            )
        except Exception as e:
            logger.warning(f"Failed to cache preferences: {e}")
    
    async def update_preferences(
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
            preferences = await self.get_preferences(user_id)
            
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
            success = await self.save_preferences(preferences)
            
            if success:
                return preferences
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error updating preferences for user {user_id}: {e}", exc_info=True)
            return None
    
    async def delete_preferences(self, user_id: UUID) -> bool:
        """
        Delete notification preferences for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Delete from database
            if not self.db_pool:
                from src.api.main import get_db_pool
                self.db_pool = get_db_pool()
            
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM notification_preferences WHERE user_id = $1",
                    user_id
                )
            
            # Delete from cache
            if self.redis_client:
                cache_key = self._get_cache_key(user_id)
                self.redis_client.delete(cache_key)
            
            logger.info(f"Deleted preferences for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting preferences for user {user_id}: {e}", exc_info=True)
            return False
    
    async def get_all_users_with_event_enabled(
        self,
        event: NotificationEvent
    ) -> List[NotificationPreferences]:
        """
        Get all users who have a specific event enabled.
        
        Uses PostgreSQL with GIN index for efficient querying.
        
        Args:
            event: Event to check
            
        Returns:
            List of NotificationPreferences with the event enabled
        """
        try:
            if not self.db_pool:
                from src.api.main import get_db_pool
                self.db_pool = get_db_pool()
            
            async with self.db_pool.acquire() as conn:
                # Use JSONB containment operator for efficient querying
                rows = await conn.fetch(
                    """
                    SELECT preference_id, user_id, enabled_events, enabled_channels,
                           email_address, webhook_url, slack_webhook_url, quiet_hours,
                           created_at, updated_at
                    FROM notification_preferences
                    WHERE enabled_events @> $1::jsonb
                    """,
                    json.dumps([event.value])
                )
                
                preferences_list = []
                for row in rows:
                    enabled_events = [NotificationEvent(e) for e in row['enabled_events']]
                    enabled_channels = [NotificationChannel(c) for c in row['enabled_channels']]
                    
                    preferences = NotificationPreferences(
                        user_id=row['user_id'],
                        enabled_events=enabled_events,
                        enabled_channels=enabled_channels,
                        email_address=row['email_address'],
                        webhook_url=row['webhook_url'],
                        slack_webhook_url=row['slack_webhook_url'],
                        quiet_hours=row['quiet_hours'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    )
                    preferences_list.append(preferences)
                
                logger.debug(f"Found {len(preferences_list)} users with event {event} enabled")
                return preferences_list
            
        except Exception as e:
            logger.error(f"Error getting users with event {event} enabled: {e}", exc_info=True)
            return []
    
    async def create_default_preferences(self, user_id: UUID) -> NotificationPreferences:
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
        
        await self.save_preferences(preferences)
        logger.info(f"Created default preferences for user {user_id}")
        return preferences


# Global repository instance
_preferences_repository: Optional[NotificationPreferencesRepository] = None


def get_preferences_repository(db_pool: Optional[asyncpg.Pool] = None) -> NotificationPreferencesRepository:
    """
    Get the global preferences repository instance.
    
    Args:
        db_pool: Optional database pool to use
        
    Returns:
        NotificationPreferencesRepository instance
    """
    global _preferences_repository
    if _preferences_repository is None:
        _preferences_repository = NotificationPreferencesRepository(db_pool)
    elif db_pool and not _preferences_repository.db_pool:
        _preferences_repository.db_pool = db_pool
    return _preferences_repository
