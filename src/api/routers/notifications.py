"""
Notification endpoints for managing user preferences and notification history.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from src.models.notification import (
    NotificationPreferences,
    NotificationEvent,
    NotificationChannel,
    Notification
)
from src.services.notification_preferences_repository import get_preferences_repository
from src.api.auth.dependencies import get_current_user
from src.models.user import User

router = APIRouter()


# Request/Response models
class UpdatePreferencesRequest(BaseModel):
    """Request model for updating notification preferences."""
    enabled_events: Optional[List[NotificationEvent]] = None
    enabled_channels: Optional[List[NotificationChannel]] = None
    email_address: Optional[str] = None
    webhook_url: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    quiet_hours: Optional[dict] = None


class PreferencesResponse(BaseModel):
    """Response model for notification preferences."""
    user_id: UUID
    enabled_events: List[NotificationEvent]
    enabled_channels: List[NotificationChannel]
    email_address: Optional[str]
    webhook_url: Optional[str]
    slack_webhook_url: Optional[str]
    quiet_hours: Optional[dict]
    updated_at: Optional[str]


@router.get(
    "/preferences",
    response_model=PreferencesResponse,
    summary="Get notification preferences",
    description="Get notification preferences for the authenticated user"
)
async def get_preferences(
    current_user: User = Depends(get_current_user)
) -> PreferencesResponse:
    """
    Get notification preferences for the authenticated user.
    
    Returns:
        User's notification preferences
    """
    repository = get_preferences_repository()
    preferences = await repository.get_preferences(current_user.user_id)
    
    if not preferences:
        # Create default preferences if none exist
        preferences = await repository.create_default_preferences(current_user.user_id)
    
    return PreferencesResponse(
        user_id=preferences.user_id,
        enabled_events=preferences.enabled_events,
        enabled_channels=preferences.enabled_channels,
        email_address=preferences.email_address,
        webhook_url=preferences.webhook_url,
        slack_webhook_url=preferences.slack_webhook_url,
        quiet_hours=preferences.quiet_hours,
        updated_at=preferences.updated_at.isoformat() if preferences.updated_at else None
    )


@router.put(
    "/preferences",
    response_model=PreferencesResponse,
    summary="Update notification preferences",
    description="Update notification preferences for the authenticated user"
)
async def update_preferences(
    request: UpdatePreferencesRequest,
    current_user: User = Depends(get_current_user)
) -> PreferencesResponse:
    """
    Update notification preferences for the authenticated user.
    
    Args:
        request: Preference updates
        
    Returns:
        Updated notification preferences
    """
    repository = get_preferences_repository()
    
    # Build updates dictionary (only include non-None values)
    updates = {}
    if request.enabled_events is not None:
        updates['enabled_events'] = request.enabled_events
    if request.enabled_channels is not None:
        updates['enabled_channels'] = request.enabled_channels
    if request.email_address is not None:
        updates['email_address'] = request.email_address
    if request.webhook_url is not None:
        updates['webhook_url'] = request.webhook_url
    if request.slack_webhook_url is not None:
        updates['slack_webhook_url'] = request.slack_webhook_url
    if request.quiet_hours is not None:
        updates['quiet_hours'] = request.quiet_hours
    
    # Update preferences
    preferences = await repository.update_preferences(current_user.user_id, updates)
    
    if not preferences:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update notification preferences"
        )
    
    return PreferencesResponse(
        user_id=preferences.user_id,
        enabled_events=preferences.enabled_events,
        enabled_channels=preferences.enabled_channels,
        email_address=preferences.email_address,
        webhook_url=preferences.webhook_url,
        slack_webhook_url=preferences.slack_webhook_url,
        quiet_hours=preferences.quiet_hours,
        updated_at=preferences.updated_at.isoformat() if preferences.updated_at else None
    )


@router.delete(
    "/preferences",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete notification preferences",
    description="Delete notification preferences for the authenticated user (resets to defaults)"
)
async def delete_preferences(
    current_user: User = Depends(get_current_user)
):
    """
    Delete notification preferences for the authenticated user.
    This will reset preferences to defaults on next access.
    """
    repository = get_preferences_repository()
    success = await repository.delete_preferences(current_user.user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete notification preferences"
        )
    
    return None


@router.get(
    "/events",
    response_model=List[str],
    summary="Get supported notification events",
    description="Get list of all supported notification event types"
)
async def get_supported_events() -> List[str]:
    """
    Get list of all supported notification event types.
    
    Returns:
        List of event type strings
    """
    return [event.value for event in NotificationEvent]


@router.get(
    "/channels",
    response_model=List[str],
    summary="Get supported notification channels",
    description="Get list of all supported notification channel types"
)
async def get_supported_channels() -> List[str]:
    """
    Get list of all supported notification channel types.
    
    Returns:
        List of channel type strings
    """
    return [channel.value for channel in NotificationChannel]


class NotificationHistoryResponse(BaseModel):
    """Response model for notification history."""
    notification_id: UUID
    event: NotificationEvent
    channel: NotificationChannel
    status: str
    created_at: str
    sent_at: Optional[str]
    retry_count: int
    data: dict
    error: Optional[str]


@router.get(
    "/history",
    response_model=List[NotificationHistoryResponse],
    summary="Get notification history",
    description="Get notification history for the authenticated user"
)
async def get_notification_history(
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=500, description="Maximum number of notifications"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    event: Optional[NotificationEvent] = Query(default=None, description="Filter by event type"),
    status: Optional[str] = Query(default=None, description="Filter by status")
) -> List[NotificationHistoryResponse]:
    """
    Get notification history for the authenticated user.
    
    Returns a paginated list of notifications sent to the user, with optional
    filtering by event type and status.
    
    Args:
        limit: Maximum number of notifications to return
        offset: Number of notifications to skip
        event: Optional event type filter
        status: Optional status filter (pending, sent, failed)
        
    Returns:
        List of notifications
    """
    # Import here to avoid circular dependency
    from src.api.main import get_db_pool
    
    try:
        db_pool = get_db_pool()
        
        # Build query
        query = """
            SELECT notification_id, user_id, event, channel, status,
                   created_at, sent_at, retry_count, data, error
            FROM notifications
            WHERE user_id = $1
        """
        params = [current_user.user_id]
        param_count = 2
        
        if event:
            query += f" AND event = ${param_count}"
            params.append(event.value)
            param_count += 1
        
        if status:
            query += f" AND status = ${param_count}"
            params.append(status)
            param_count += 1
        
        query += f" ORDER BY created_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
        params.extend([limit, offset])
        
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            
            notifications = []
            for row in rows:
                notifications.append(NotificationHistoryResponse(
                    notification_id=row['notification_id'],
                    event=NotificationEvent(row['event']),
                    channel=NotificationChannel(row['channel']),
                    status=row['status'],
                    created_at=row['created_at'].isoformat(),
                    sent_at=row['sent_at'].isoformat() if row['sent_at'] else None,
                    retry_count=row['retry_count'],
                    data=row['data'] or {},
                    error=row['error']
                ))
            
            return notifications
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve notification history: {str(e)}"
        )
