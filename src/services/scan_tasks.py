"""
Celery tasks for async scan execution.
"""

import logging
import asyncio
from uuid import UUID
from typing import Optional

from src.services.celery_app import celery_app
from src.models.scan import ScanMode, ScanParams
from src.models.profile import ScanProfile

logger = logging.getLogger(__name__)


@celery_app.task(name='execute_scan_async', bind=True, max_retries=3)
def execute_scan_async(
    self,
    scan_id: str,
    domain: str,
    domain_config_id: str,
    scan_mode: str,
    params: dict,
    profile_id: Optional[str] = None
):
    """
    Execute a scan asynchronously.
    
    Args:
        self: Celery task instance
        scan_id: Scan ID
        domain: Domain to scan
        domain_config_id: Domain configuration ID
        scan_mode: Scan mode (quick, deep, realtime)
        params: Scan parameters dict
        profile_id: Optional scan profile ID
        
    Returns:
        Scan result dict
    """
    try:
        # Import here to avoid circular dependencies
        from src.database.connection import get_db_pool
        from src.cache.redis_client import get_redis_client
        from src.services.scan_service import ScanService
        from src.services.profile_service import ProfileService
        
        # Get database pool and Redis client
        db_pool = get_db_pool()
        redis_client = get_redis_client()
        
        # Create scan service
        scan_service = ScanService(db_pool, redis_client)
        
        # Load profile if provided
        profile = None
        if profile_id:
            profile_service = ProfileService(db_pool)
            profile = asyncio.run(profile_service.get_profile(UUID(profile_id)))
        
        # Convert params dict to ScanParams
        scan_params = ScanParams(**params)
        
        # Execute scan with progress tracking
        result = asyncio.run(
            scan_service.execute_scan_with_progress(
                scan_id=UUID(scan_id),
                domain=domain,
                domain_config_id=UUID(domain_config_id),
                params=scan_params,
                scan_mode=ScanMode(scan_mode),
                progress_callback=None  # No callback for async execution
            )
        )
        
        logger.info(f"Scan {scan_id} completed successfully")
        return {
            "scan_id": scan_id,
            "status": "success",
            "total_cookies": len(result.get("cookies", [])),
            "pages_visited": len(result.get("pages_visited", []))
        }
        
    except Exception as e:
        logger.exception(f"Scan {scan_id} failed: {e}")
        
        # Retry on transient errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        
        # Update scan status to failed
        try:
            from src.database.connection import get_db_pool
            db_pool = get_db_pool()
            
            async def update_failed():
                async with db_pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE scan_results
                        SET status = 'failed', error = $1, updated_at = NOW()
                        WHERE scan_id = $2
                        """,
                        str(e),
                        UUID(scan_id)
                    )
            
            asyncio.run(update_failed())
        except Exception as update_error:
            logger.error(f"Failed to update scan status: {update_error}")
        
        raise


@celery_app.task(name='cancel_scan_async')
def cancel_scan_async(scan_id: str):
    """
    Cancel a running scan.
    
    Args:
        scan_id: Scan ID to cancel
        
    Returns:
        Success status
    """
    try:
        from src.database.connection import get_db_pool
        
        db_pool = get_db_pool()
        
        async def cancel():
            async with db_pool.acquire() as conn:
                # Update scan status to cancelled
                await conn.execute(
                    """
                    UPDATE scan_results
                    SET status = 'cancelled', updated_at = NOW()
                    WHERE scan_id = $1 AND status IN ('pending', 'running')
                    """,
                    UUID(scan_id)
                )
        
        asyncio.run(cancel())
        logger.info(f"Scan {scan_id} cancelled")
        
        return {"scan_id": scan_id, "status": "cancelled"}
        
    except Exception as e:
        logger.exception(f"Failed to cancel scan {scan_id}: {e}")
        raise
