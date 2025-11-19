"""
Schedule-related data models.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, validator, UUID4


class ScheduleFrequency(str, Enum):
    """Schedule frequency enumeration."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class ScanType(str, Enum):
    """Scan type enumeration for scheduled scans."""
    QUICK = "quick"
    DEEP = "deep"


class Schedule(BaseModel):
    """Schedule data model."""
    schedule_id: Optional[UUID4] = None
    domain_config_id: UUID4 = Field(..., description="Domain configuration ID")
    domain: str = Field(..., description="Domain to scan")
    profile_id: Optional[UUID4] = Field(None, description="Scan profile ID")
    scan_type: ScanType = Field(default=ScanType.QUICK, description="Scan type (quick or deep)")
    scan_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Scan parameters (max_pages, custom_pages, etc.)"
    )
    frequency: ScheduleFrequency = Field(..., description="Schedule frequency")
    time_config: Dict[str, Any] = Field(
        ...,
        description="Time configuration (cron expression, hour, day_of_week, etc.)"
    )
    enabled: bool = Field(default=True, description="Whether schedule is enabled")
    next_run: Optional[datetime] = Field(None, description="Next scheduled run time")
    last_run: Optional[datetime] = Field(None, description="Last run time")
    last_status: Optional[str] = Field(None, description="Status of last run")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    @validator('time_config')
    def validate_time_config(cls, v, values):
        """Validate time configuration based on frequency."""
        if 'frequency' not in values:
            return v
        
        frequency = values['frequency']
        
        if frequency == ScheduleFrequency.HOURLY:
            # Should have 'minute' field
            if 'minute' not in v:
                raise ValueError("Hourly schedule requires 'minute' in time_config")
        elif frequency == ScheduleFrequency.DAILY:
            # Should have 'hour' and 'minute' fields
            if 'hour' not in v or 'minute' not in v:
                raise ValueError("Daily schedule requires 'hour' and 'minute' in time_config")
        elif frequency == ScheduleFrequency.WEEKLY:
            # Should have 'day_of_week', 'hour', and 'minute' fields
            if 'day_of_week' not in v or 'hour' not in v or 'minute' not in v:
                raise ValueError("Weekly schedule requires 'day_of_week', 'hour', and 'minute' in time_config")
        elif frequency == ScheduleFrequency.MONTHLY:
            # Should have 'day', 'hour', and 'minute' fields
            if 'day' not in v or 'hour' not in v or 'minute' not in v:
                raise ValueError("Monthly schedule requires 'day', 'hour', and 'minute' in time_config")
        elif frequency == ScheduleFrequency.CUSTOM:
            # Should have 'cron' field
            if 'cron' not in v:
                raise ValueError("Custom schedule requires 'cron' expression in time_config")
        
        return v


class ScheduleExecution(BaseModel):
    """Schedule execution history model."""
    execution_id: Optional[UUID4] = None
    schedule_id: UUID4 = Field(..., description="Schedule ID")
    scan_id: Optional[UUID4] = Field(None, description="Resulting scan ID")
    executed_at: datetime = Field(default_factory=datetime.utcnow, description="Execution time")
    status: str = Field(..., description="Execution status (success, failed)")
    duration_seconds: Optional[float] = Field(None, description="Execution duration")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
