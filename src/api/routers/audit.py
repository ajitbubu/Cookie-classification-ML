"""
Audit log API endpoints.

Provides endpoints for viewing audit logs and user activity.
"""

from typing import Optional, List
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, EmailStr

from src.api.auth.dependencies import get_current_user, require_admin
from src.api.auth.audit import (
    get_audit_logger,
    AuditAction,
    ResourceType,
    AuditStatus
)
from src.api.auth.lockout import get_lockout_manager
from src.models.user import User

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


class AuditLogResponse(BaseModel):
    """Audit log response model."""
    
    audit_id: UUID
    user_id: Optional[UUID]
    action: str
    resource_type: str
    resource_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    status: str
    details: dict
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuditLogsListResponse(BaseModel):
    """Paginated audit logs response."""
    
    logs: List[AuditLogResponse]
    total: int
    limit: int
    offset: int


@router.get("/logs", response_model=AuditLogsListResponse)
async def get_audit_logs(
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    current_user: User = Depends(require_admin)
):
    """
    Get audit logs with filtering (admin only).
    
    Retrieve audit logs with optional filtering by user, action, resource type,
    and date range. Only accessible to admin users.
    """
    audit_logger = get_audit_logger()
    
    # Convert string enums if provided
    action_enum = None
    if action:
        try:
            action_enum = AuditAction(action)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid action: {action}")
    
    resource_type_enum = None
    if resource_type:
        try:
            resource_type_enum = ResourceType(resource_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid resource type: {resource_type}")
    
    # Get logs
    logs = audit_logger.get_audit_logs(
        user_id=user_id,
        action=action_enum,
        resource_type=resource_type_enum,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    
    # Get total count (for pagination)
    # Note: In production, you'd want a separate count query
    total = len(logs)
    
    return AuditLogsListResponse(
        logs=[AuditLogResponse(**log) for log in logs],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/activity", response_model=List[AuditLogResponse])
async def get_user_activity(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's activity history.
    
    Retrieve the authenticated user's recent activity including logins,
    configuration changes, and data access operations.
    """
    audit_logger = get_audit_logger()
    
    logs = audit_logger.get_user_activity(
        user_id=current_user.user_id,
        days=days,
        limit=limit
    )
    
    return [AuditLogResponse(**log) for log in logs]


@router.get("/actions", response_model=List[str])
async def get_audit_actions(
    current_user: User = Depends(require_admin)
):
    """
    Get list of available audit actions (admin only).
    
    Returns all possible audit action types for filtering.
    """
    return [action.value for action in AuditAction]


@router.get("/resource-types", response_model=List[str])
async def get_resource_types(
    current_user: User = Depends(require_admin)
):
    """
    Get list of available resource types (admin only).
    
    Returns all possible resource types for filtering.
    """
    return [resource.value for resource in ResourceType]



class LockoutInfoResponse(BaseModel):
    """Account lockout information response."""
    
    email: str
    is_locked: bool
    unlock_time: Optional[str]
    failed_attempts: int
    max_attempts: int
    remaining_attempts: int
    locked_for_seconds: Optional[int] = None


class UnlockAccountRequest(BaseModel):
    """Request to unlock an account."""
    
    email: EmailStr = Field(..., description="Email address of account to unlock")


@router.get("/lockout/{email}", response_model=LockoutInfoResponse)
async def get_lockout_status(
    email: EmailStr,
    current_user: User = Depends(require_admin)
):
    """
    Get account lockout status (admin only).
    
    Retrieve detailed information about an account's lockout status,
    including failed attempts and unlock time.
    """
    lockout_manager = get_lockout_manager()
    info = lockout_manager.get_lockout_info(email)
    
    return LockoutInfoResponse(**info)


@router.post("/unlock", status_code=200)
async def unlock_account(
    request: UnlockAccountRequest,
    current_user: User = Depends(require_admin)
):
    """
    Manually unlock an account (admin only).
    
    Remove lockout and reset failed login attempts for an account.
    This action is logged to the audit trail.
    """
    lockout_manager = get_lockout_manager()
    
    # Check if account is actually locked
    is_locked, _ = lockout_manager.is_locked(request.email)
    if not is_locked:
        raise HTTPException(
            status_code=400,
            detail=f"Account {request.email} is not locked"
        )
    
    # Unlock the account
    lockout_manager.unlock_account(request.email, current_user.user_id)
    
    return {
        "message": f"Account {request.email} has been unlocked",
        "unlocked_by": str(current_user.user_id)
    }


@router.post("/reset-attempts", status_code=200)
async def reset_login_attempts(
    email: EmailStr = Query(..., description="Email address"),
    current_user: User = Depends(require_admin)
):
    """
    Reset failed login attempts for an account (admin only).
    
    Clear the failed login attempt counter without unlocking the account.
    """
    lockout_manager = get_lockout_manager()
    lockout_manager.reset_attempts(email)
    
    return {
        "message": f"Login attempts reset for {email}",
        "reset_by": str(current_user.user_id)
    }
