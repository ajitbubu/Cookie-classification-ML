"""
Scan management endpoints.
"""

import asyncio
import json
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, UUID4

from api.auth.dependencies import get_current_user, require_scope
from models.user import TokenData
from models.scan import ScanResult, ScanParams, ScanMode, ScanStatus, ScanProgress
from services.scan_service import ScanService
from services.parallel_scan_manager import ParallelScanManager

router = APIRouter()


def get_scan_service(request: Request) -> ScanService:
    """Dependency to get scan service from app state."""
    return ScanService(request.app.state.db_pool, request.app.state.redis_client)


def get_parallel_scan_manager(request: Request) -> ParallelScanManager:
    """Dependency to get parallel scan manager from app state."""
    scan_service = get_scan_service(request)
    # Get max concurrency from config or use default
    max_concurrency = getattr(request.app.state, 'max_scan_concurrency', 10)
    return ParallelScanManager(scan_service, max_concurrency)


class CreateScanRequest(BaseModel):
    """Request model for creating a new scan."""
    domain: str = Field(..., description="Domain to scan (must include protocol)")
    domain_config_id: Optional[UUID4] = Field(None, description="Domain configuration ID (optional)")
    scan_mode: ScanMode = Field(default=ScanMode.QUICK, description="Scan mode")
    params: Optional[ScanParams] = Field(default_factory=ScanParams, description="Scan parameters")
    
    class Config:
        schema_extra = {
            "example": {
                "domain": "https://example.com",
                "domain_config_id": "123e4567-e89b-12d3-a456-426614174000",
                "scan_mode": "quick",
                "params": {
                    "custom_pages": ["/about", "/contact"],
                    "max_retries": 3
                }
            }
        }


class CreateScanResponse(BaseModel):
    """Response model for scan creation."""
    scan_id: UUID4
    status: ScanStatus
    message: str
    created_at: datetime


class PaginatedScansResponse(BaseModel):
    """Paginated list of scans."""
    items: List[ScanResult]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class BatchScanDomain(BaseModel):
    """Domain configuration for batch scanning."""
    domain: str = Field(..., description="Domain to scan")
    domain_config_id: UUID4 = Field(..., description="Domain configuration ID")
    params: Optional[ScanParams] = Field(default_factory=ScanParams, description="Scan parameters")


class BatchScanRequest(BaseModel):
    """Request model for batch scanning multiple domains."""
    domains: List[BatchScanDomain] = Field(..., min_items=1, max_items=10, description="List of domains to scan")
    scan_mode: ScanMode = Field(default=ScanMode.QUICK, description="Scan mode for all domains")
    profile_id: Optional[UUID4] = Field(None, description="Optional scan profile ID to apply")
    
    class Config:
        schema_extra = {
            "example": {
                "domains": [
                    {
                        "domain": "https://example.com",
                        "domain_config_id": "123e4567-e89b-12d3-a456-426614174000",
                        "params": {"custom_pages": ["/about"]}
                    },
                    {
                        "domain": "https://example.org",
                        "domain_config_id": "123e4567-e89b-12d3-a456-426614174001"
                    }
                ],
                "scan_mode": "quick"
            }
        }


class BatchScanResponse(BaseModel):
    """Response model for batch scan."""
    total_domains: int
    successful: int
    failed: int
    results: List[Dict[str, Any]]


@router.post(
    "",
    response_model=CreateScanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new scan",
    description="Initiate a new cookie scan for a domain"
)
async def create_scan(
    request: CreateScanRequest,
    current_user: TokenData = Depends(require_scope("scans:write"))
):
    """
    Create a new scan.
    
    Initiates a cookie scan for the specified domain with the given parameters.
    The scan will be queued and executed asynchronously.
    
    **Required scope**: `scans:write`
    
    **Note**: This is a placeholder implementation. In production, this should:
    - Validate the domain
    - Queue the scan job
    - Store scan metadata in database
    - Return the scan ID for tracking
    """
    # TODO: Implement actual scan creation logic
    # - Validate domain format and accessibility
    # - Create scan record in database
    # - Queue scan job for async processing
    # - Return scan ID
    
    scan_id = uuid4()
    
    return CreateScanResponse(
        scan_id=scan_id,
        status=ScanStatus.PENDING,
        message="Scan created successfully and queued for processing",
        created_at=datetime.utcnow()
    )


@router.get(
    "/{scan_id}",
    response_model=ScanResult,
    status_code=status.HTTP_200_OK,
    summary="Get scan result",
    description="Retrieve scan result by ID"
)
async def get_scan(
    scan_id: UUID4,
    current_user: TokenData = Depends(require_scope("scans:read"))
):
    """
    Get scan result by ID.
    
    Returns the complete scan result including all cookies found,
    storage data, and scan metadata.
    
    **Required scope**: `scans:read`
    
    **Note**: This is a placeholder implementation. In production, this should:
    - Query database for scan result
    - Check user permissions
    - Return cached result if available
    """
    # TODO: Implement actual scan retrieval
    # - Query database for scan by ID
    # - Check if user has permission to view this scan
    # - Return scan result or 404 if not found
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Scan with ID {scan_id} not found"
    )


@router.get(
    "",
    response_model=PaginatedScansResponse,
    status_code=status.HTTP_200_OK,
    summary="List scans",
    description="List scans with pagination and filtering"
)
async def list_scans(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    domain: Optional[str] = Query(default=None, description="Filter by domain"),
    status_filter: Optional[ScanStatus] = Query(default=None, alias="status", description="Filter by status"),
    scan_mode: Optional[ScanMode] = Query(default=None, description="Filter by scan mode"),
    current_user: TokenData = Depends(require_scope("scans:read"))
):
    """
    List scans with pagination.
    
    Returns a paginated list of scans with optional filtering by domain,
    status, and scan mode.
    
    **Required scope**: `scans:read`
    
    **Note**: This is a placeholder implementation. In production, this should:
    - Query database with filters
    - Apply pagination
    - Return results with pagination metadata
    """
    # TODO: Implement actual scan listing
    # - Query database with filters and pagination
    # - Filter by user permissions
    # - Return paginated results
    
    return PaginatedScansResponse(
        items=[],
        total=0,
        page=page,
        page_size=page_size,
        has_next=False,
        has_prev=page > 1
    )


@router.delete(
    "/{scan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel/delete scan",
    description="Cancel a running scan or delete a completed scan"
)
async def delete_scan(
    scan_id: UUID4,
    current_user: TokenData = Depends(require_scope("scans:write"))
):
    """
    Cancel or delete a scan.
    
    If the scan is running, it will be cancelled. If it's completed,
    the scan result will be deleted from the database.
    
    **Required scope**: `scans:write`
    
    **Note**: This is a placeholder implementation. In production, this should:
    - Check if scan exists
    - Cancel if running
    - Delete from database
    - Clean up associated resources
    """
    # TODO: Implement actual scan deletion
    # - Check if scan exists
    # - If running, cancel the scan job
    # - Delete scan record from database
    # - Clean up cached data
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Scan with ID {scan_id} not found"
    )


@router.get(
    "/{scan_id}/progress",
    response_model=ScanProgress,
    status_code=status.HTTP_200_OK,
    summary="Get scan progress",
    description="Get real-time progress of a running scan"
)
async def get_scan_progress(
    scan_id: UUID4,
    current_user: TokenData = Depends(require_scope("scans:read")),
    scan_service: ScanService = Depends(get_scan_service)
):
    """
    Get real-time scan progress.
    
    Returns current progress information for a running scan,
    including pages visited, cookies found, and progress percentage.
    
    **Required scope**: `scans:read`
    """
    progress = await scan_service.get_scan_progress(scan_id)
    
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID {scan_id} not found or not running"
        )
    
    return progress


@router.get(
    "/{scan_id}/stream",
    summary="Stream scan progress (SSE)",
    description="Server-Sent Events endpoint for real-time scan progress updates"
)
async def stream_scan_progress(
    scan_id: UUID4,
    current_user: TokenData = Depends(require_scope("scans:read")),
    scan_service: ScanService = Depends(get_scan_service)
):
    """
    Stream real-time scan progress via Server-Sent Events (SSE).
    
    This endpoint provides a continuous stream of progress updates for a running scan.
    The connection will remain open until the scan completes or fails.
    
    **Required scope**: `scans:read`
    
    **Response format**: Server-Sent Events (text/event-stream)
    
    Each event contains a JSON payload with progress information:
    ```json
    {
      "scan_id": "uuid",
      "status": "running",
      "current_page": "https://example.com/page",
      "pages_visited": 5,
      "cookies_found": 23,
      "progress_percentage": 45.5,
      "message": null,
      "timestamp": "2025-11-04T10:30:00Z"
    }
    ```
    """
    async def event_generator():
        """Generate SSE events for scan progress."""
        last_progress = None
        
        # Keep streaming until scan completes or fails
        while True:
            progress = await scan_service.get_scan_progress(scan_id)
            
            if not progress:
                # Scan not found or completed
                if last_progress and last_progress.status in [ScanStatus.SUCCESS, ScanStatus.FAILED, ScanStatus.CANCELLED]:
                    # Send final event and close
                    yield f"data: {json.dumps(last_progress.dict())}\n\n"
                    yield "event: close\ndata: Scan completed\n\n"
                else:
                    # Scan not found
                    yield f"event: error\ndata: Scan not found\n\n"
                break
            
            # Send progress update
            progress_json = progress.dict()
            progress_json['timestamp'] = progress_json['timestamp'].isoformat()
            yield f"data: {json.dumps(progress_json)}\n\n"
            
            last_progress = progress
            
            # Check if scan is complete
            if progress.status in [ScanStatus.SUCCESS, ScanStatus.FAILED, ScanStatus.CANCELLED]:
                yield "event: close\ndata: Scan completed\n\n"
                break
            
            # Wait before next update (2 seconds as per requirements)
            await asyncio.sleep(2)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.post(
    "/batch",
    response_model=BatchScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Batch scan multiple domains",
    description="Scan multiple domains in parallel with concurrency control"
)
async def batch_scan_domains(
    request: BatchScanRequest,
    current_user: TokenData = Depends(require_scope("scans:write")),
    parallel_manager: ParallelScanManager = Depends(get_parallel_scan_manager)
):
    """
    Scan multiple domains in parallel.
    
    This endpoint allows you to scan up to 10 domains concurrently with
    automatic concurrency control to prevent resource exhaustion.
    
    **Required scope**: `scans:write`
    
    **Features**:
    - Parallel execution with semaphore-based concurrency control
    - Automatic error handling for individual scan failures
    - Support for custom scan parameters per domain
    - Optional scan profile application
    
    **Limits**:
    - Maximum 10 domains per batch
    - System-wide concurrency limit applies
    
    **Note**: This endpoint returns immediately with 202 Accepted.
    The scans are executed asynchronously. Use the returned scan IDs
    to track progress via the `/scans/{scan_id}/progress` endpoint.
    """
    # Convert request domains to internal format
    domains = [
        {
            "domain": d.domain,
            "domain_config_id": d.domain_config_id,
            "params": d.params
        }
        for d in request.domains
    ]
    
    # Execute parallel scans
    results = await parallel_manager.scan_multiple_domains(
        domains=domains,
        scan_mode=request.scan_mode,
        profile=None  # TODO: Load profile if profile_id provided
    )
    
    # Count successes and failures
    successful = sum(1 for r in results if r.get("status") == "success")
    failed = len(results) - successful
    
    return BatchScanResponse(
        total_domains=len(domains),
        successful=successful,
        failed=failed,
        results=results
    )
