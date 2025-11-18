"""
Schedule management endpoints.
"""

from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field, UUID4, validator

from api.auth.dependencies import get_current_user, require_scope
from models.user import TokenData
from models.schedule import Schedule, ScheduleFrequency

router = APIRouter()


class CreateScheduleRequest(BaseModel):
    """Request model for creating a schedule."""
    domain_config_id: UUID4 = Field(..., description="Domain configuration ID")
    domain: str = Field(..., description="Domain to scan")
    profile_id: Optional[UUID4] = Field(None, description="Scan profile ID")
    frequency: ScheduleFrequency = Field(..., description="Schedule frequency")
    time_config: dict = Field(..., description="Time configuration")
    enabled: bool = Field(default=True, description="Whether schedule is enabled")
    
    @validator('time_config')
    def validate_time_config(cls, v, values):
        """Validate time configuration based on frequency."""
        if 'frequency' not in values:
            return v
        
        frequency = values['frequency']
        
        if frequency == ScheduleFrequency.HOURLY:
            if 'minute' not in v:
                raise ValueError("Hourly schedule requires 'minute' in time_config")
        elif frequency == ScheduleFrequency.DAILY:
            if 'hour' not in v or 'minute' not in v:
                raise ValueError("Daily schedule requires 'hour' and 'minute' in time_config")
        elif frequency == ScheduleFrequency.WEEKLY:
            if 'day_of_week' not in v or 'hour' not in v or 'minute' not in v:
                raise ValueError("Weekly schedule requires 'day_of_week', 'hour', and 'minute' in time_config")
        elif frequency == ScheduleFrequency.MONTHLY:
            if 'day' not in v or 'hour' not in v or 'minute' not in v:
                raise ValueError("Monthly schedule requires 'day', 'hour', and 'minute' in time_config")
        
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "domain_config_id": "123e4567-e89b-12d3-a456-426614174000",
                "domain": "https://example.com",
                "frequency": "daily",
                "time_config": {
                    "hour": 9,
                    "minute": 0
                },
                "enabled": True
            }
        }


class UpdateScheduleRequest(BaseModel):
    """Request model for updating a schedule."""
    profile_id: Optional[UUID4] = None
    frequency: Optional[ScheduleFrequency] = None
    time_config: Optional[dict] = None
    enabled: Optional[bool] = None


class ScheduleResponse(BaseModel):
    """Response model for schedule operations."""
    schedule_id: UUID4
    domain_config_id: UUID4
    domain: str
    profile_id: Optional[UUID4]
    frequency: ScheduleFrequency
    time_config: dict
    enabled: bool
    next_run: Optional[datetime]
    last_run: Optional[datetime]
    last_status: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        use_enum_values = True


class PaginatedSchedulesResponse(BaseModel):
    """Paginated list of schedules."""
    items: List[ScheduleResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


@router.post(
    "",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create schedule",
    description="Create a new scan schedule"
)
async def create_schedule(
    request: CreateScheduleRequest,
    current_user: TokenData = Depends(require_scope("schedules:write"))
):
    """
    Create a new scan schedule.
    
    Creates a recurring scan schedule with the specified frequency and time configuration.
    
    **Required scope**: `schedules:write`
    
    **Time Configuration Examples**:
    - Hourly: `{"minute": 15}` - Run at 15 minutes past each hour
    - Daily: `{"hour": 9, "minute": 0}` - Run at 9:00 AM daily
    - Weekly: `{"day_of_week": "monday", "hour": 9, "minute": 0}` - Run Mondays at 9:00 AM
    - Monthly: `{"day": 1, "hour": 9, "minute": 0}` - Run on 1st of month at 9:00 AM
    
    **Note**: This is a placeholder implementation. In production, this should:
    - Validate schedule configuration
    - Store schedule in database
    - Register with scheduler service
    - Calculate next run time
    """
    # TODO: Implement actual schedule creation
    # - Validate time configuration
    # - Store in database
    # - Register with APScheduler
    # - Calculate next_run timestamp
    
    schedule_id = uuid4()
    now = datetime.utcnow()
    
    return ScheduleResponse(
        schedule_id=schedule_id,
        domain_config_id=request.domain_config_id,
        domain=request.domain,
        profile_id=request.profile_id,
        frequency=request.frequency,
        time_config=request.time_config,
        enabled=request.enabled,
        next_run=None,  # TODO: Calculate based on time_config
        last_run=None,
        last_status=None,
        created_at=now,
        updated_at=now
    )


@router.get(
    "",
    response_model=PaginatedSchedulesResponse,
    status_code=status.HTTP_200_OK,
    summary="List schedules",
    description="List all schedules with pagination"
)
async def list_schedules(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    domain: Optional[str] = Query(default=None, description="Filter by domain"),
    enabled: Optional[bool] = Query(default=None, description="Filter by enabled status"),
    current_user: TokenData = Depends(require_scope("schedules:read"))
):
    """
    List all schedules with pagination.
    
    Returns a paginated list of schedules with optional filtering.
    
    **Required scope**: `schedules:read`
    
    **Note**: This is a placeholder implementation. In production, this should:
    - Query database with filters
    - Apply pagination
    - Return results with metadata
    """
    # TODO: Implement actual schedule listing
    # - Query database with filters
    # - Apply pagination
    # - Return results
    
    return PaginatedSchedulesResponse(
        items=[],
        total=0,
        page=page,
        page_size=page_size,
        has_next=False,
        has_prev=page > 1
    )


@router.get(
    "/{schedule_id}",
    response_model=ScheduleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get schedule",
    description="Get schedule by ID"
)
async def get_schedule(
    schedule_id: UUID4,
    current_user: TokenData = Depends(require_scope("schedules:read"))
):
    """
    Get schedule by ID.
    
    Returns detailed information about a specific schedule.
    
    **Required scope**: `schedules:read`
    
    **Note**: This is a placeholder implementation. In production, this should:
    - Query database for schedule
    - Check user permissions
    - Return schedule or 404
    """
    # TODO: Implement actual schedule retrieval
    # - Query database
    # - Check permissions
    # - Return schedule
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Schedule with ID {schedule_id} not found"
    )


@router.put(
    "/{schedule_id}",
    response_model=ScheduleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update schedule",
    description="Update an existing schedule"
)
async def update_schedule(
    schedule_id: UUID4,
    request: UpdateScheduleRequest,
    current_user: TokenData = Depends(require_scope("schedules:write"))
):
    """
    Update an existing schedule.
    
    Updates schedule configuration. Only provided fields will be updated.
    
    **Required scope**: `schedules:write`
    
    **Note**: This is a placeholder implementation. In production, this should:
    - Validate schedule exists
    - Update database record
    - Update scheduler registration
    - Recalculate next run time
    """
    # TODO: Implement actual schedule update
    # - Check schedule exists
    # - Update database
    # - Update APScheduler job
    # - Recalculate next_run
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Schedule with ID {schedule_id} not found"
    )


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete schedule",
    description="Delete a schedule"
)
async def delete_schedule(
    schedule_id: UUID4,
    current_user: TokenData = Depends(require_scope("schedules:write"))
):
    """
    Delete a schedule.
    
    Removes the schedule from the database and unregisters it from the scheduler.
    
    **Required scope**: `schedules:write`
    
    **Note**: This is a placeholder implementation. In production, this should:
    - Validate schedule exists
    - Remove from scheduler
    - Delete from database
    """
    # TODO: Implement actual schedule deletion
    # - Check schedule exists
    # - Remove from APScheduler
    # - Delete from database
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Schedule with ID {schedule_id} not found"
    )


@router.post(
    "/{schedule_id}/enable",
    response_model=ScheduleResponse,
    status_code=status.HTTP_200_OK,
    summary="Enable schedule",
    description="Enable a disabled schedule"
)
async def enable_schedule(
    schedule_id: UUID4,
    current_user: TokenData = Depends(require_scope("schedules:write"))
):
    """
    Enable a schedule.
    
    Enables a previously disabled schedule and registers it with the scheduler.
    
    **Required scope**: `schedules:write`
    """
    # TODO: Implement schedule enabling
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Schedule with ID {schedule_id} not found"
    )


@router.post(
    "/{schedule_id}/disable",
    response_model=ScheduleResponse,
    status_code=status.HTTP_200_OK,
    summary="Disable schedule",
    description="Disable an active schedule"
)
async def disable_schedule(
    schedule_id: UUID4,
    current_user: TokenData = Depends(require_scope("schedules:write"))
):
    """
    Disable a schedule.
    
    Disables an active schedule and unregisters it from the scheduler.
    
    **Required scope**: `schedules:write`
    """
    # TODO: Implement schedule disabling
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Schedule with ID {schedule_id} not found"
    )
