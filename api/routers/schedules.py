"""
Schedule management endpoints.
"""

import json
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends, Query, Request
from pydantic import BaseModel, Field, UUID4, validator
import asyncpg

from api.auth.dependencies import get_current_user, require_scope
from models.user import TokenData
from models.schedule import Schedule, ScheduleFrequency, ScanType

router = APIRouter()


def get_db_pool(request: Request) -> asyncpg.Pool:
    """Dependency to get database pool from app state."""
    return request.app.state.db_pool


class CreateScheduleRequest(BaseModel):
    """Request model for creating a schedule."""
    domain_config_id: UUID4 = Field(..., description="Domain configuration ID")
    domain: str = Field(..., description="Domain to scan")
    profile_id: Optional[UUID4] = Field(None, description="Scan profile ID")
    scan_type: ScanType = Field(default=ScanType.QUICK, description="Scan type (quick or deep)")
    scan_params: dict = Field(default_factory=dict, description="Scan parameters (max_pages, custom_pages, etc.)")
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
    scan_type: ScanType
    scan_params: dict
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
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    current_user: TokenData = Depends(require_scope("schedules:write"))
):
    """
    Create a new scan schedule.

    Creates a recurring scan schedule with the specified frequency and time configuration.

    **Required scope**: `schedules:write`

    **Scan Types**:
    - **quick**: Scans main page and custom pages only (fast, 1-10 pages)
    - **deep**: Full website crawl up to max_pages (slow, configurable depth)

    **Scan Parameters for Deep Scans**:
    - `max_pages`: Maximum pages to scan (default: 20000, range: 1-20000)
    - `custom_pages`: List of pages to prioritize
    - `chunk_size`: Pages per processing chunk (default: 1000)

    **Time Configuration Examples**:
    - Hourly: `{"minute": 15}` - Run at 15 minutes past each hour
    - Daily: `{"hour": 9, "minute": 0}` - Run at 9:00 AM daily
    - Weekly: `{"day_of_week": "monday", "hour": 9, "minute": 0}` - Run Mondays at 9:00 AM
    - Monthly: `{"day": 1, "hour": 9, "minute": 0}` - Run on 1st of month at 9:00 AM
    """
    schedule_id = uuid4()
    now = datetime.utcnow()

    # Create schedule in database
    query = """
        INSERT INTO schedules (
            schedule_id, domain_config_id, domain, profile_id,
            scan_type, scan_params, frequency, time_config, enabled,
            created_at, updated_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        RETURNING schedule_id, domain_config_id, domain, profile_id,
                  scan_type, scan_params, frequency, time_config, enabled,
                  next_run, last_run, last_status, created_at, updated_at
    """

    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                schedule_id,
                request.domain_config_id,
                request.domain,
                request.profile_id,
                request.scan_type.value,
                json.dumps(request.scan_params),
                request.frequency.value,
                json.dumps(request.time_config),
                request.enabled,
                now,
                now
            )

        return ScheduleResponse(
            schedule_id=row['schedule_id'],
            domain_config_id=row['domain_config_id'],
            domain=row['domain'],
            profile_id=row['profile_id'],
            scan_type=ScanType(row['scan_type']),
            scan_params=json.loads(row['scan_params']) if isinstance(row['scan_params'], str) else row['scan_params'],
            frequency=ScheduleFrequency(row['frequency']),
            time_config=json.loads(row['time_config']) if isinstance(row['time_config'], str) else row['time_config'],
            enabled=row['enabled'],
            next_run=row['next_run'],
            last_run=row['last_run'],
            last_status=row['last_status'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create schedule: {str(e)}"
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
    scan_type: Optional[ScanType] = Query(default=None, description="Filter by scan type"),
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    current_user: TokenData = Depends(require_scope("schedules:read"))
):
    """
    List all schedules with pagination.

    Returns a paginated list of schedules with optional filtering.

    **Required scope**: `schedules:read`
    """
    offset = (page - 1) * page_size

    # Build query with filters
    where_clauses = []
    params = []
    param_idx = 1

    if domain is not None:
        where_clauses.append(f"domain = ${param_idx}")
        params.append(domain)
        param_idx += 1

    if enabled is not None:
        where_clauses.append(f"enabled = ${param_idx}")
        params.append(enabled)
        param_idx += 1

    if scan_type is not None:
        where_clauses.append(f"scan_type = ${param_idx}")
        params.append(scan_type.value)
        param_idx += 1

    where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    # Count total
    count_query = f"SELECT COUNT(*) FROM schedules{where_clause}"

    # Query schedules
    query = f"""
        SELECT schedule_id, domain_config_id, domain, profile_id,
               scan_type, scan_params, frequency, time_config, enabled,
               next_run, last_run, last_status, created_at, updated_at
        FROM schedules
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """
    params.extend([page_size, offset])

    try:
        async with db_pool.acquire() as conn:
            total = await conn.fetchval(count_query, *params[:-2] if where_clauses else [])
            rows = await conn.fetch(query, *params)

        items = [
            ScheduleResponse(
                schedule_id=row['schedule_id'],
                domain_config_id=row['domain_config_id'],
                domain=row['domain'],
                profile_id=row['profile_id'],
                scan_type=ScanType(row['scan_type']),
                scan_params=json.loads(row['scan_params']) if isinstance(row['scan_params'], str) else row['scan_params'],
                frequency=ScheduleFrequency(row['frequency']),
                time_config=json.loads(row['time_config']) if isinstance(row['time_config'], str) else row['time_config'],
                enabled=row['enabled'],
                next_run=row['next_run'],
                last_run=row['last_run'],
                last_status=row['last_status'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            for row in rows
        ]

        return PaginatedSchedulesResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(offset + page_size) < total,
            has_prev=page > 1
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list schedules: {str(e)}"
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
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    current_user: TokenData = Depends(require_scope("schedules:read"))
):
    """
    Get schedule by ID.

    Returns detailed information about a specific schedule.

    **Required scope**: `schedules:read`
    """
    query = """
        SELECT schedule_id, domain_config_id, domain, profile_id,
               scan_type, scan_params, frequency, time_config, enabled,
               next_run, last_run, last_status, created_at, updated_at
        FROM schedules
        WHERE schedule_id = $1
    """

    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(query, schedule_id)

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found"
            )

        return ScheduleResponse(
            schedule_id=row['schedule_id'],
            domain_config_id=row['domain_config_id'],
            domain=row['domain'],
            profile_id=row['profile_id'],
            scan_type=ScanType(row['scan_type']),
            scan_params=json.loads(row['scan_params']) if isinstance(row['scan_params'], str) else row['scan_params'],
            frequency=ScheduleFrequency(row['frequency']),
            time_config=json.loads(row['time_config']) if isinstance(row['time_config'], str) else row['time_config'],
            enabled=row['enabled'],
            next_run=row['next_run'],
            last_run=row['last_run'],
            last_status=row['last_status'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get schedule: {str(e)}"
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
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    current_user: TokenData = Depends(require_scope("schedules:write"))
):
    """
    Update an existing schedule.

    Updates schedule configuration. Only provided fields will be updated.

    **Required scope**: `schedules:write`

    **Note**: After updating, the scheduler will automatically pick up changes
    within the configured check interval (default: 60 seconds).
    """
    # Build dynamic update query
    updates = []
    params = [schedule_id]
    param_idx = 2

    if request.profile_id is not None:
        updates.append(f"profile_id = ${param_idx}")
        params.append(request.profile_id)
        param_idx += 1

    if request.frequency is not None:
        updates.append(f"frequency = ${param_idx}")
        params.append(request.frequency.value)
        param_idx += 1

    if request.time_config is not None:
        updates.append(f"time_config = ${param_idx}")
        params.append(json.dumps(request.time_config))
        param_idx += 1

    if request.enabled is not None:
        updates.append(f"enabled = ${param_idx}")
        params.append(request.enabled)
        param_idx += 1

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )

    updates.append(f"updated_at = ${param_idx}")
    params.append(datetime.utcnow())

    query = f"""
        UPDATE schedules
        SET {', '.join(updates)}
        WHERE schedule_id = $1
        RETURNING schedule_id, domain_config_id, domain, profile_id,
                  scan_type, scan_params, frequency, time_config, enabled,
                  next_run, last_run, last_status, created_at, updated_at
    """

    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found"
            )

        return ScheduleResponse(
            schedule_id=row['schedule_id'],
            domain_config_id=row['domain_config_id'],
            domain=row['domain'],
            profile_id=row['profile_id'],
            scan_type=ScanType(row['scan_type']),
            scan_params=json.loads(row['scan_params']) if isinstance(row['scan_params'], str) else row['scan_params'],
            frequency=ScheduleFrequency(row['frequency']),
            time_config=json.loads(row['time_config']) if isinstance(row['time_config'], str) else row['time_config'],
            enabled=row['enabled'],
            next_run=row['next_run'],
            last_run=row['last_run'],
            last_status=row['last_status'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update schedule: {str(e)}"
        )


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete schedule",
    description="Delete a schedule"
)
async def delete_schedule(
    schedule_id: UUID4,
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    current_user: TokenData = Depends(require_scope("schedules:write"))
):
    """
    Delete a schedule.

    Removes the schedule from the database and unregisters it from the scheduler.

    **Required scope**: `schedules:write`

    **Note**: The scheduler will automatically detect the deletion and remove
    the job within the configured check interval (default: 60 seconds).
    """
    query = "DELETE FROM schedules WHERE schedule_id = $1 RETURNING schedule_id"

    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(query, schedule_id)

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found"
            )

        return None  # 204 No Content
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete schedule: {str(e)}"
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
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    current_user: TokenData = Depends(require_scope("schedules:write"))
):
    """
    Enable a schedule.

    Enables a previously disabled schedule and registers it with the scheduler.

    **Required scope**: `schedules:write`

    **Note**: The scheduler will automatically pick up the enabled schedule
    within the configured check interval (default: 60 seconds).
    """
    query = """
        UPDATE schedules
        SET enabled = TRUE, updated_at = $2
        WHERE schedule_id = $1
        RETURNING schedule_id, domain_config_id, domain, profile_id,
                  scan_type, scan_params, frequency, time_config, enabled,
                  next_run, last_run, last_status, created_at, updated_at
    """

    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(query, schedule_id, datetime.utcnow())

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found"
            )

        return ScheduleResponse(
            schedule_id=row['schedule_id'],
            domain_config_id=row['domain_config_id'],
            domain=row['domain'],
            profile_id=row['profile_id'],
            scan_type=ScanType(row['scan_type']),
            scan_params=json.loads(row['scan_params']) if isinstance(row['scan_params'], str) else row['scan_params'],
            frequency=ScheduleFrequency(row['frequency']),
            time_config=json.loads(row['time_config']) if isinstance(row['time_config'], str) else row['time_config'],
            enabled=row['enabled'],
            next_run=row['next_run'],
            last_run=row['last_run'],
            last_status=row['last_status'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable schedule: {str(e)}"
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
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    current_user: TokenData = Depends(require_scope("schedules:write"))
):
    """
    Disable a schedule.

    Disables an active schedule and unregisters it from the scheduler.

    **Required scope**: `schedules:write`

    **Note**: The scheduler will automatically detect the disabled schedule
    and remove the job within the configured check interval (default: 60 seconds).
    """
    query = """
        UPDATE schedules
        SET enabled = FALSE, updated_at = $2
        WHERE schedule_id = $1
        RETURNING schedule_id, domain_config_id, domain, profile_id,
                  scan_type, scan_params, frequency, time_config, enabled,
                  next_run, last_run, last_status, created_at, updated_at
    """

    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(query, schedule_id, datetime.utcnow())

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found"
            )

        return ScheduleResponse(
            schedule_id=row['schedule_id'],
            domain_config_id=row['domain_config_id'],
            domain=row['domain'],
            profile_id=row['profile_id'],
            scan_type=ScanType(row['scan_type']),
            scan_params=json.loads(row['scan_params']) if isinstance(row['scan_params'], str) else row['scan_params'],
            frequency=ScheduleFrequency(row['frequency']),
            time_config=json.loads(row['time_config']) if isinstance(row['time_config'], str) else row['time_config'],
            enabled=row['enabled'],
            next_run=row['next_run'],
            last_run=row['last_run'],
            last_status=row['last_status'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable schedule: {str(e)}"
        )
