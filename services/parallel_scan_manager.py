"""
Parallel scan manager for concurrent domain scanning.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from models.scan import ScanParams, ScanMode, ScanResult, ScanStatus
from models.profile import ScanProfile
from services.scan_service import ScanService

logger = logging.getLogger(__name__)


class ParallelScanManager:
    """
    Manager for parallel domain scanning with concurrency control.
    
    Uses semaphore-based concurrency control to limit the number of
    simultaneous scans and prevent resource exhaustion.
    """
    
    def __init__(
        self,
        scan_service: ScanService,
        max_concurrency: int = 10
    ):
        """
        Initialize parallel scan manager.
        
        Args:
            scan_service: ScanService instance for executing scans
            max_concurrency: Maximum number of concurrent scans (1-10)
        """
        if max_concurrency < 1 or max_concurrency > 10:
            raise ValueError("max_concurrency must be between 1 and 10")
        
        self.scan_service = scan_service
        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.active_scans: Dict[UUID, Dict[str, Any]] = {}
        
        logger.info(f"ParallelScanManager initialized with max_concurrency={max_concurrency}")
    
    async def scan_multiple_domains(
        self,
        domains: List[Dict[str, Any]],
        scan_mode: ScanMode = ScanMode.QUICK,
        profile: Optional[ScanProfile] = None
    ) -> List[Dict[str, Any]]:
        """
        Scan multiple domains in parallel with concurrency control.
        
        Args:
            domains: List of domain configurations, each containing:
                - domain: str (required)
                - domain_config_id: UUID (required)
                - params: ScanParams (optional)
            scan_mode: Scan mode to use for all domains
            profile: Optional scan profile to apply
            
        Returns:
            List of scan results (successful or error dicts)
            
        Example:
            domains = [
                {
                    "domain": "https://example.com",
                    "domain_config_id": uuid4(),
                    "params": ScanParams(custom_pages=["/about"])
                },
                {
                    "domain": "https://example.org",
                    "domain_config_id": uuid4()
                }
            ]
            results = await manager.scan_multiple_domains(domains)
        """
        if not domains:
            return []
        
        logger.info(f"Starting parallel scan of {len(domains)} domains")
        
        # Create tasks for all domains
        tasks = [
            self._scan_with_semaphore(
                domain_config=domain,
                scan_mode=scan_mode,
                profile=profile
            )
            for domain in domains
        ]
        
        # Execute all tasks concurrently with error handling
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and convert exceptions to error dicts
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Scan failed for domain {domains[i].get('domain')}: {result}")
                processed_results.append({
                    "domain": domains[i].get("domain"),
                    "domain_config_id": domains[i].get("domain_config_id"),
                    "status": "failed",
                    "error": str(result),
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                processed_results.append(result)
        
        logger.info(f"Completed parallel scan of {len(domains)} domains")
        return processed_results
    
    async def _scan_with_semaphore(
        self,
        domain_config: Dict[str, Any],
        scan_mode: ScanMode,
        profile: Optional[ScanProfile]
    ) -> Dict[str, Any]:
        """
        Execute a single scan with semaphore-based concurrency control.
        
        Args:
            domain_config: Domain configuration dict
            scan_mode: Scan mode
            profile: Optional scan profile
            
        Returns:
            Scan result dict
        """
        domain = domain_config.get("domain")
        domain_config_id = domain_config.get("domain_config_id")
        params = domain_config.get("params", ScanParams())
        
        if not domain or not domain_config_id:
            raise ValueError("domain and domain_config_id are required")
        
        # Acquire semaphore (blocks if max concurrency reached)
        async with self.semaphore:
            logger.info(f"Starting scan for {domain} (active: {self.max_concurrency - self.semaphore._value})")
            
            try:
                # Create scan record
                scan_id = await self.scan_service.create_scan(
                    domain=domain,
                    domain_config_id=domain_config_id,
                    scan_mode=scan_mode,
                    params=params,
                    profile=profile
                )
                
                # Track active scan
                self.active_scans[scan_id] = {
                    "domain": domain,
                    "started_at": datetime.utcnow(),
                    "status": "running"
                }
                
                # Execute scan
                result = await self.scan_service.execute_scan_with_progress(
                    scan_id=scan_id,
                    domain=domain,
                    params=params,
                    scan_mode=scan_mode,
                    progress_callback=None  # No progress callback for parallel scans
                )
                
                # Remove from active scans
                self.active_scans.pop(scan_id, None)
                
                logger.info(f"Completed scan for {domain} (scan_id: {scan_id})")
                
                return {
                    "scan_id": str(scan_id),
                    "domain": domain,
                    "domain_config_id": str(domain_config_id),
                    "status": "success",
                    "total_cookies": len(result.get("cookies", [])),
                    "pages_visited": len(result.get("pages_visited", [])),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.exception(f"Scan failed for {domain}: {e}")
                
                # Remove from active scans
                if 'scan_id' in locals():
                    self.active_scans.pop(scan_id, None)
                
                raise
    
    def get_active_scan_count(self) -> int:
        """
        Get the number of currently active scans.
        
        Returns:
            Number of active scans
        """
        return len(self.active_scans)
    
    def get_available_slots(self) -> int:
        """
        Get the number of available scan slots.
        
        Returns:
            Number of available slots (0 if at max concurrency)
        """
        return self.semaphore._value
    
    def get_active_scans(self) -> Dict[UUID, Dict[str, Any]]:
        """
        Get information about currently active scans.
        
        Returns:
            Dict mapping scan_id to scan info
        """
        return self.active_scans.copy()
    
    async def wait_for_slot(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for an available scan slot.
        
        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)
            
        Returns:
            True if slot became available, False if timeout
        """
        try:
            await asyncio.wait_for(
                self.semaphore.acquire(),
                timeout=timeout
            )
            self.semaphore.release()
            return True
        except asyncio.TimeoutError:
            return False


class BatchScanRequest:
    """Helper class for building batch scan requests."""
    
    def __init__(self):
        """Initialize batch scan request."""
        self.domains: List[Dict[str, Any]] = []
    
    def add_domain(
        self,
        domain: str,
        domain_config_id: UUID,
        params: Optional[ScanParams] = None
    ) -> 'BatchScanRequest':
        """
        Add a domain to the batch scan request.
        
        Args:
            domain: Domain URL
            domain_config_id: Domain configuration ID
            params: Optional scan parameters
            
        Returns:
            Self for method chaining
        """
        self.domains.append({
            "domain": domain,
            "domain_config_id": domain_config_id,
            "params": params or ScanParams()
        })
        return self
    
    def get_domains(self) -> List[Dict[str, Any]]:
        """
        Get the list of domains to scan.
        
        Returns:
            List of domain configurations
        """
        return self.domains
    
    def count(self) -> int:
        """
        Get the number of domains in the batch.
        
        Returns:
            Number of domains
        """
        return len(self.domains)
