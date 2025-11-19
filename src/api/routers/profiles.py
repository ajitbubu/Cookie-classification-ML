"""
Scan profile management endpoints.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Depends, Query, Request
from pydantic import BaseModel, UUID4

from src.api.auth.dependencies import get_current_user, require_scope
from src.models.user import TokenData
from src.models.profile import ScanProfile, ScanProfileCreate, ScanProfileUpdate
from src.services.profile_service import ProfileService

router = APIRouter()


def get_profile_service(request: Request) -> ProfileService:
    """Dependency to get profile service from app state."""
    return ProfileService(request.app.state.db_pool)


@router.post(
    "",
    response_model=ScanProfile,
    status_code=status.HTTP_201_CREATED,
    summary="Create scan profile",
    description="Create a new scan profile with custom configuration"
)
async def create_profile(
    profile_data: ScanProfileCreate,
    current_user: TokenData = Depends(require_scope("profiles:write")),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """
    Create a new scan profile.
    
    Scan profiles allow you to define reusable scan configurations with
    custom parameters like depth, retries, custom pages, and more.
    
    **Required scope**: `profiles:write`
    """
    try:
        profile = await profile_service.create_profile(
            profile_data=profile_data,
            created_by=current_user.user_id
        )
        return profile
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create profile: {str(e)}"
        )


@router.get(
    "/{profile_id}",
    response_model=ScanProfile,
    status_code=status.HTTP_200_OK,
    summary="Get scan profile",
    description="Retrieve a scan profile by ID"
)
async def get_profile(
    profile_id: UUID4,
    current_user: TokenData = Depends(require_scope("profiles:read")),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """
    Get a scan profile by ID.
    
    Returns the complete profile configuration including all parameters.
    
    **Required scope**: `profiles:read`
    """
    profile = await profile_service.get_profile(profile_id)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile with ID {profile_id} not found"
        )
    
    return profile


@router.get(
    "",
    response_model=List[ScanProfile],
    status_code=status.HTTP_200_OK,
    summary="List scan profiles",
    description="List all scan profiles with optional filtering"
)
async def list_profiles(
    scan_mode: Optional[str] = Query(default=None, description="Filter by scan mode"),
    limit: int = Query(default=100, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    current_user: TokenData = Depends(require_scope("profiles:read")),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """
    List scan profiles.
    
    Returns a list of scan profiles with optional filtering by scan mode.
    Supports pagination via limit and offset parameters.
    
    **Required scope**: `profiles:read`
    """
    try:
        profiles = await profile_service.list_profiles(
            scan_mode=scan_mode,
            limit=limit,
            offset=offset
        )
        return profiles
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list profiles: {str(e)}"
        )


@router.put(
    "/{profile_id}",
    response_model=ScanProfile,
    status_code=status.HTTP_200_OK,
    summary="Update scan profile",
    description="Update an existing scan profile"
)
async def update_profile(
    profile_id: UUID4,
    profile_data: ScanProfileUpdate,
    current_user: TokenData = Depends(require_scope("profiles:write")),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """
    Update a scan profile.
    
    Updates the specified profile with new configuration. Only provided
    fields will be updated; omitted fields will retain their current values.
    
    **Required scope**: `profiles:write`
    """
    try:
        profile = await profile_service.update_profile(
            profile_id=profile_id,
            profile_data=profile_data
        )
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile with ID {profile_id} not found"
            )
        
        return profile
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )


@router.delete(
    "/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete scan profile",
    description="Delete a scan profile"
)
async def delete_profile(
    profile_id: UUID4,
    current_user: TokenData = Depends(require_scope("profiles:write")),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """
    Delete a scan profile.
    
    Permanently deletes the specified profile. This action cannot be undone.
    Note: Schedules using this profile will have their profile_id set to NULL.
    
    **Required scope**: `profiles:write`
    """
    try:
        deleted = await profile_service.delete_profile(profile_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile with ID {profile_id} not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete profile: {str(e)}"
        )
