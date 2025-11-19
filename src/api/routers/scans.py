"""
Scan management endpoints.
"""

import asyncio
import json
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, UUID4

from src.api.auth.dependencies import get_current_user, require_scope
from src.models.user import TokenData
from src.models.scan import ScanResult, ScanParams, ScanMode, ScanStatus, ScanProgress, Cookie
from src.services.scan_service import ScanService
from src.services.parallel_scan_manager import ParallelScanManager

router = APIRouter()
logger = logging.getLogger(__name__)


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
    req: CreateScanRequest,
    request: Request,
    current_user: TokenData = Depends(require_scope("scans:write")),
    scan_service: ScanService = Depends(get_scan_service)
):
    """
    Create a new scan.
    
    Initiates a cookie scan for the specified domain with the given parameters.
    The scan will be queued and executed asynchronously.
    
    **Required scope**: `scans:write`
    
    **Scan Modes**:
    - **quick**: Scans main page and custom pages only (fast, 1-10 pages)
    - **deep**: Full website crawl up to max_pages (slow, configurable depth)
    - **realtime**: Same as quick but with real-time progress streaming
    
    **Response**: Returns immediately with scan ID. Use `/scans/{scan_id}` to check status
    and `/scans/{scan_id}/progress` or `/scans/{scan_id}/stream` for real-time updates.
    """
    from src.services.scan_tasks import execute_scan_async
    
    # Validate domain format
    if not req.domain.startswith(('http://', 'https://')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Domain must include protocol (http:// or https://)"
        )
    
    # Generate domain_config_id if not provided
    domain_config_id = req.domain_config_id or uuid4()
    
    # Create scan record in database
    scan_id = await scan_service.create_scan(
        domain=req.domain,
        domain_config_id=domain_config_id,
        scan_mode=req.scan_mode,
        params=req.params or ScanParams(),
        profile=None  # TODO: Load profile if needed
    )
    
    # Queue scan for async execution
    try:
        execute_scan_async.delay(
            scan_id=str(scan_id),
            domain=req.domain,
            domain_config_id=str(domain_config_id),
            scan_mode=req.scan_mode.value,
            params=(req.params or ScanParams()).dict(),
            profile_id=None
        )
        logger.info(f"Scan {scan_id} queued for execution")
    except Exception as e:
        logger.error(f"Failed to queue scan {scan_id}: {e}")
        # Update scan status to failed
        await scan_service._update_scan_status(scan_id, ScanStatus.FAILED, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue scan: {str(e)}"
        )
    
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
    request: Request,
    current_user: TokenData = Depends(require_scope("scans:read"))
):
    """
    Get scan result by ID.
    
    Returns the complete scan result including all cookies found,
    storage data, and scan metadata.
    
    **Required scope**: `scans:read`
    """
    db_pool = request.app.state.db_pool
    
    async with db_pool.acquire() as conn:
        # Get scan result
        row = await conn.fetchrow(
            """
            SELECT 
                scan_id, domain_config_id, domain, scan_mode, timestamp_utc,
                status, error, total_cookies, duration_seconds, page_count,
                created_at, updated_at, params
            FROM scan_results
            WHERE scan_id = $1
            """,
            scan_id
        )
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scan with ID {scan_id} not found"
            )
        
        # Get cookies for this scan
        cookie_rows = await conn.fetch(
            """
            SELECT 
                cookie_id, scan_id, name, domain, path, hashed_value,
                http_only, secure, same_site, category, cookie_type,
                created_at
            FROM cookies
            WHERE scan_id = $1
            ORDER BY created_at
            """,
            scan_id
        )
        
        # Get cookie counts by type
        cookie_counts = await conn.fetchrow(
            """
            SELECT 
                COUNT(*) FILTER (WHERE cookie_type = 'First Party') as first_party,
                COUNT(*) FILTER (WHERE cookie_type = 'Third Party') as third_party
            FROM cookies
            WHERE scan_id = $1
            """,
            scan_id
        )
        
        cookies = [
            Cookie(
                cookie_id=c['cookie_id'],
                scan_id=c['scan_id'],
                name=c['name'],
                value=c['hashed_value'] or '',
                domain=c['domain'],
                path=c['path'] or '/',
                expires=None,
                http_only=c['http_only'],
                secure=c['secure'],
                same_site=c['same_site'],
                category=c['category'],
                is_first_party=(c['cookie_type'] == 'First Party'),
                created_at=c['created_at']
            )
            for c in cookie_rows
        ]
        
        return ScanResult(
            scan_id=row['scan_id'],
            domain_config_id=row['domain_config_id'],
            domain=row['domain'],
            scan_mode=row['scan_mode'],
            timestamp_utc=row['timestamp_utc'],
            status=row['status'],
            error_message=row['error'],
            total_cookies=row['total_cookies'] or 0,
            first_party_cookies=cookie_counts['first_party'] or 0,
            third_party_cookies=cookie_counts['third_party'] or 0,
            scan_duration_seconds=row['duration_seconds'] or 0,
            pages_scanned=row['page_count'] or 0,
            cookies=cookies,
            storage_data={},
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )


@router.get(
    "",
    response_model=PaginatedScansResponse,
    status_code=status.HTTP_200_OK,
    summary="List scans",
    description="List scans with pagination and filtering"
)
async def list_scans(
    request: Request,
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
    """
    db_pool = request.app.state.db_pool
    offset = (page - 1) * page_size
    
    # Build query with filters
    where_clauses = []
    params = []
    param_count = 1
    
    if domain:
        where_clauses.append(f"domain ILIKE ${param_count}")
        params.append(f"%{domain}%")
        param_count += 1
    
    if status_filter:
        where_clauses.append(f"status = ${param_count}")
        params.append(status_filter)
        param_count += 1
    
    if scan_mode:
        where_clauses.append(f"scan_mode = ${param_count}")
        params.append(scan_mode)
        param_count += 1
    
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    
    async with db_pool.acquire() as conn:
        # Get total count
        count_query = f"SELECT COUNT(*) FROM scan_results {where_sql}"
        total = await conn.fetchval(count_query, *params)
        
        # Get paginated results
        query = f"""
            SELECT 
                scan_id, domain_config_id, domain, scan_mode, timestamp_utc,
                status, error, total_cookies, duration_seconds, page_count,
                created_at, updated_at, params
            FROM scan_results
            {where_sql}
            ORDER BY created_at DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """
        params.extend([page_size, offset])
        
        rows = await conn.fetch(query, *params)
        
        # Convert rows to ScanResult objects
        items = []
        for row in rows:
            # Get cookie counts by type
            cookie_counts = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) FILTER (WHERE cookie_type = 'First Party') as first_party,
                    COUNT(*) FILTER (WHERE cookie_type = 'Third Party') as third_party
                FROM cookies
                WHERE scan_id = $1
                """,
                row['scan_id']
            )
            
            items.append(ScanResult(
                scan_id=row['scan_id'],
                domain_config_id=row['domain_config_id'],
                domain=row['domain'],
                scan_mode=row['scan_mode'],
                timestamp_utc=row['timestamp_utc'],
                status=row['status'],
                error_message=row['error'],
                total_cookies=row['total_cookies'] or 0,
                first_party_cookies=cookie_counts['first_party'] or 0,
                third_party_cookies=cookie_counts['third_party'] or 0,
                scan_duration_seconds=row['duration_seconds'] or 0,
                pages_scanned=row['page_count'] or 0,
                cookies=[],  # Don't load full cookie data in list view
                storage_data={},
                created_at=row['created_at'],
                updated_at=row['updated_at']
            ))
    
    return PaginatedScansResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + page_size) < total,
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
    request: Request,
    current_user: TokenData = Depends(require_scope("scans:write"))
):
    """
    Cancel or delete a scan.
    
    If the scan is running, it will be cancelled. If it's completed,
    the scan result will be deleted from the database.
    
    **Required scope**: `scans:write`
    
    **Behavior**:
    - For pending/running scans: Cancels the scan and marks as cancelled
    - For completed scans: Deletes the scan and all associated data (cookies, etc.)
    """
    from src.services.scan_tasks import cancel_scan_async
    
    db_pool = request.app.state.db_pool
    
    async with db_pool.acquire() as conn:
        # Check if scan exists and get status
        row = await conn.fetchrow(
            "SELECT scan_id, status FROM scan_results WHERE scan_id = $1",
            scan_id
        )
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scan with ID {scan_id} not found"
            )
        
        scan_status = row['status']
        
        # If scan is running or pending, cancel it
        if scan_status in [ScanStatus.PENDING, ScanStatus.RUNNING]:
            try:
                cancel_scan_async.delay(str(scan_id))
                logger.info(f"Scan {scan_id} cancellation queued")
            except Exception as e:
                logger.error(f"Failed to queue scan cancellation: {e}")
                # Still try to update status directly
                await conn.execute(
                    """
                    UPDATE scan_results
                    SET status = 'cancelled', updated_at = NOW()
                    WHERE scan_id = $1
                    """,
                    scan_id
                )
        else:
            # For completed scans, delete from database
            # Delete cookies first (foreign key constraint)
            await conn.execute(
                "DELETE FROM cookies WHERE scan_id = $1",
                scan_id
            )
            
            # Delete scan result
            await conn.execute(
                "DELETE FROM scan_results WHERE scan_id = $1",
                scan_id
            )
            
            logger.info(f"Scan {scan_id} deleted from database")
    
    return None  # 204 No Content


@router.delete(
    "/by-domain",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete scan by domain",
    description="Delete the most recent scan for a domain"
)
async def delete_scan_by_domain(
    domain: str = Query(..., description="Domain name to delete scan for"),
    request: Request = None,
    current_user: TokenData = Depends(require_scope("scans:write"))
):
    """
    Delete the most recent scan for a specific domain.

    This endpoint is useful when you only have the domain name
    and not the scan_id. It will delete the most recently created
    scan for the specified domain.

    **Required scope**: `scans:write`

    **Example**:
    ```
    DELETE /api/v1/scans/by-domain?domain=https://example.com
    ```
    """
    db_pool = request.app.state.db_pool

    async with db_pool.acquire() as conn:
        # Get most recent scan for this domain
        row = await conn.fetchrow(
            """
            SELECT scan_id FROM scan_results
            WHERE domain = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            domain
        )

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No scan found for domain: {domain}"
            )

        scan_id = row['scan_id']

        # Delete cookies first (foreign key constraint)
        await conn.execute(
            "DELETE FROM cookies WHERE scan_id = $1",
            scan_id
        )

        # Delete scan result
        await conn.execute(
            "DELETE FROM scan_results WHERE scan_id = $1",
            scan_id
        )

        logger.info(f"Deleted most recent scan for domain {domain} (scan_id: {scan_id})")

    return None  # 204 No Content


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
