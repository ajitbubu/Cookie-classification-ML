"""
Notification-related data models.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, UUID4, validator


class NotificationEvent(str, Enum):
    """Notification event enumeration."""
    SCAN_STARTED = "scan.started"
    SCAN_COMPLETED = "scan.completed"
    SCAN_FAILED = "scan.failed"
    COMPLIANCE_VIOLATION = "compliance.violation"
    ANOMALY_DETECTED = "anomaly.detected"
    SCHEDULE_CREATED = "schedule.created"
    SCHEDULE_UPDATED = "schedule.updated"
    SCHEDULE_FAILED = "schedule.failed"


class NotificationChannel(str, Enum):
    """Notification channel enumeration."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"


class NotificationStatus(str, Enum):
    """Notification status enumeration."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


class Notification(BaseModel):
    """Notification data model."""
    notification_id: Optional[UUID4] = None
    user_id: UUID4 = Field(..., description="User ID to notify")
    event: NotificationEvent = Field(..., description="Event that triggered notification")
    channel: NotificationChannel = Field(..., description="Notification channel")
    status: NotificationStatus = Field(default=NotificationStatus.PENDING, description="Notification status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    sent_at: Optional[datetime] = Field(None, description="Sent timestamp")
    retry_count: int = Field(default=0, ge=0, description="Number of retry attempts")
    data: Dict[str, Any] = Field(default_factory=dict, description="Notification data/payload")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    @validator('retry_count')
    def validate_retry_count(cls, v):
        """Validate retry count doesn't exceed maximum."""
        if v > 3:
            raise ValueError("Maximum 3 retry attempts allowed")
        return v


class NotificationPreferences(BaseModel):
    """User notification preferences model."""
    user_id: UUID4 = Field(..., description="User ID")
    enabled_events: list[NotificationEvent] = Field(
        default_factory=list,
        description="List of events to receive notifications for"
    )
    enabled_channels: list[NotificationChannel] = Field(
        default_factory=list,
        description="List of channels to use for notifications"
    )
    email_address: Optional[str] = Field(None, description="Email address for email notifications")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for webhook notifications")
    slack_webhook_url: Optional[str] = Field(None, description="Slack webhook URL")
    quiet_hours: Optional[Dict[str, Any]] = Field(
        None,
        description="Quiet hours configuration (start_hour, end_hour)"
    )
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    @validator('email_address')
    def validate_email(cls, v, values):
        """Validate email if email channel is enabled."""
        if v is None and 'enabled_channels' in values:
            if NotificationChannel.EMAIL in values['enabled_channels']:
                raise ValueError("Email address required when email channel is enabled")
        return v
    
    @validator('webhook_url')
    def validate_webhook(cls, v, values):
        """Validate webhook URL if webhook channel is enabled."""
        if v is None and 'enabled_channels' in values:
            if NotificationChannel.WEBHOOK in values['enabled_channels']:
                raise ValueError("Webhook URL required when webhook channel is enabled")
        return v
    
    @validator('slack_webhook_url')
    def validate_slack(cls, v, values):
        """Validate Slack webhook URL if Slack channel is enabled."""
        if v is None and 'enabled_channels' in values:
            if NotificationChannel.SLACK in values['enabled_channels']:
                raise ValueError("Slack webhook URL required when Slack channel is enabled")
        return v


class NotificationTemplate(BaseModel):
    """Notification template model."""
    template_id: Optional[UUID4] = None
    event: NotificationEvent = Field(..., description="Event this template is for")
    channel: NotificationChannel = Field(..., description="Channel this template is for")
    subject: Optional[str] = Field(None, description="Subject line (for email)")
    body: str = Field(..., description="Template body with variable placeholders")
    variables: list[str] = Field(default_factory=list, description="List of available variables")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
