"""
Scheduled scan executor that integrates with parallel and enterprise scanners.

This service executes scheduled scans using the appropriate scanner based on
the scan type (quick or deep).
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import uuid4

from parallel_scanner import ParallelCookieScanner
from enterprise_scanner import EnterpriseCookieScanner, EnterpriseMetrics

logger = logging.getLogger(__name__)


class ScanType:
    """Scan type enumeration."""
    QUICK = "quick"
    DEEP = "deep"


class ScheduledScanExecutor:
    """
    Executor for scheduled scans that uses parallel or enterprise scanners
    based on the scan type.
    """

    def __init__(
        self,
        max_concurrent_quick: int = 5,
        browser_pool_size: int = 5,
        pages_per_browser: int = 20
    ):
        """
        Initialize scheduled scan executor.

        Args:
            max_concurrent_quick: Max concurrent pages for quick scans
            browser_pool_size: Number of browser instances for deep scans
            pages_per_browser: Concurrent pages per browser for deep scans
        """
        self.max_concurrent_quick = max_concurrent_quick
        self.browser_pool_size = browser_pool_size
        self.pages_per_browser = pages_per_browser

        logger.info(
            f"ScheduledScanExecutor initialized: "
            f"quick_concurrent={max_concurrent_quick}, "
            f"browser_pool={browser_pool_size}, "
            f"pages_per_browser={pages_per_browser}"
        )

    async def execute_quick_scan(
        self,
        domain: str,
        custom_pages: Optional[list] = None,
        accept_button_selector: str = 'button:has-text("Accept")',
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a quick scan using ParallelCookieScanner.

        Quick scans only scan the main page and any custom pages provided.

        Args:
            domain: Domain to scan (must include protocol)
            custom_pages: Optional list of custom pages to scan
            accept_button_selector: Selector for accept button
            user_agent: Optional custom user agent

        Returns:
            Scan results dictionary
        """
        logger.info(f"Executing quick scan for {domain}")

        try:
            scanner = ParallelCookieScanner(
                max_concurrent=self.max_concurrent_quick,
                accept_button_selector=accept_button_selector,
                user_agent=user_agent
            )

            result = await scanner.quick_scan(
                domain=domain,
                custom_pages=custom_pages or []
            )

            logger.info(
                f"Quick scan completed for {domain}: "
                f"{result['cookies_found']} cookies found"
            )

            return {
                'scan_id': str(uuid4()),
                'scan_type': ScanType.QUICK,
                'domain': domain,
                'status': 'success',
                'cookies_found': result['cookies_found'],
                'pages_scanned': result['pages_scanned'],
                'duration_seconds': result['scan_duration'],
                'completed_at': datetime.utcnow().isoformat(),
                'cookies': result['cookies'],
                'errors': result.get('errors', [])
            }

        except Exception as e:
            logger.error(f"Quick scan failed for {domain}: {e}", exc_info=True)
            return {
                'scan_id': str(uuid4()),
                'scan_type': ScanType.QUICK,
                'domain': domain,
                'status': 'failed',
                'error': str(e),
                'completed_at': datetime.utcnow().isoformat()
            }

    async def execute_deep_scan(
        self,
        domain: str,
        max_pages: int = 20000,
        custom_pages: Optional[list] = None,
        accept_button_selector: str = 'button:has-text("Accept")',
        user_agent: Optional[str] = None,
        chunk_size: int = 1000
    ) -> Dict[str, Any]:
        """
        Execute a deep scan using EnterpriseCookieScanner.

        Deep scans crawl the website and scan up to max_pages.

        Args:
            domain: Domain to scan (must include protocol)
            max_pages: Maximum pages to scan (1-20000)
            custom_pages: Optional list of custom pages to prioritize
            accept_button_selector: Selector for accept button
            user_agent: Optional custom user agent
            chunk_size: Pages per processing chunk

        Returns:
            Scan results dictionary
        """
        logger.info(f"Executing deep scan for {domain} (max_pages={max_pages})")

        try:
            scanner = EnterpriseCookieScanner(
                browser_pool_size=self.browser_pool_size,
                pages_per_browser=self.pages_per_browser,
                accept_button_selector=accept_button_selector,
                user_agent=user_agent
            )

            result = await scanner.enterprise_deep_scan(
                domain=domain,
                max_pages=max_pages,
                custom_pages=custom_pages,
                chunk_size=chunk_size
            )

            logger.info(
                f"Deep scan completed for {domain}: "
                f"{result['cookies_found']} cookies from {result['pages_scanned']} pages"
            )

            return {
                'scan_id': result.get('scan_id', str(uuid4())),
                'scan_type': ScanType.DEEP,
                'domain': domain,
                'status': 'success',
                'cookies_found': result['cookies_found'],
                'pages_scanned': result['pages_scanned'],
                'pages_failed': result.get('pages_failed', 0),
                'duration_seconds': result.get('duration_seconds', 0),
                'completed_at': datetime.utcnow().isoformat(),
                'cookies': result.get('cookies', []),
                'errors': result.get('errors', []),
                'metrics': result.get('metrics', {})
            }

        except Exception as e:
            logger.error(f"Deep scan failed for {domain}: {e}", exc_info=True)
            return {
                'scan_id': str(uuid4()),
                'scan_type': ScanType.DEEP,
                'domain': domain,
                'status': 'failed',
                'error': str(e),
                'completed_at': datetime.utcnow().isoformat()
            }

    async def execute_scheduled_scan(
        self,
        schedule: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a scheduled scan based on schedule configuration.

        This is the main entry point for executing scheduled scans.
        It determines the scan type and calls the appropriate scanner.

        Args:
            schedule: Schedule dictionary from database

        Returns:
            Scan results dictionary
        """
        domain = schedule['domain']
        scan_type = schedule.get('scan_type', ScanType.QUICK)

        # Extract scan parameters from schedule
        scan_params = schedule.get('scan_params', {})
        max_pages = scan_params.get('max_pages', 20000)
        custom_pages = scan_params.get('custom_pages', [])
        accept_button_selector = scan_params.get(
            'accept_selector',
            'button:has-text("Accept")'
        )
        user_agent = scan_params.get('user_agent')
        chunk_size = scan_params.get('chunk_size', 1000)

        logger.info(
            f"Executing scheduled {scan_type} scan for {domain} "
            f"(schedule_id={schedule['schedule_id']})"
        )

        # Execute appropriate scan type
        if scan_type == ScanType.DEEP:
            result = await self.execute_deep_scan(
                domain=domain,
                max_pages=max_pages,
                custom_pages=custom_pages,
                accept_button_selector=accept_button_selector,
                user_agent=user_agent,
                chunk_size=chunk_size
            )
        else:  # ScanType.QUICK
            result = await self.execute_quick_scan(
                domain=domain,
                custom_pages=custom_pages,
                accept_button_selector=accept_button_selector,
                user_agent=user_agent
            )

        # Add schedule metadata to result
        result['schedule_id'] = schedule['schedule_id']
        result['domain_config_id'] = schedule['domain_config_id']

        return result

    def execute_scheduled_scan_sync(
        self,
        schedule: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Synchronous wrapper for execute_scheduled_scan.

        This is used by the enhanced scheduler which runs in a thread pool.

        Args:
            schedule: Schedule dictionary from database

        Returns:
            Scan results dictionary
        """
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                self.execute_scheduled_scan(schedule)
            )
            return result
        finally:
            loop.close()


# Singleton instance
_scheduled_scan_executor: Optional[ScheduledScanExecutor] = None


def get_scheduled_scan_executor() -> ScheduledScanExecutor:
    """Get the global scheduled scan executor instance."""
    global _scheduled_scan_executor
    if _scheduled_scan_executor is None:
        raise RuntimeError(
            "Scheduled scan executor not initialized. "
            "Call init_scheduled_scan_executor() first."
        )
    return _scheduled_scan_executor


def init_scheduled_scan_executor(
    max_concurrent_quick: int = 5,
    browser_pool_size: int = 5,
    pages_per_browser: int = 20
) -> ScheduledScanExecutor:
    """Initialize the global scheduled scan executor instance."""
    global _scheduled_scan_executor
    _scheduled_scan_executor = ScheduledScanExecutor(
        max_concurrent_quick=max_concurrent_quick,
        browser_pool_size=browser_pool_size,
        pages_per_browser=pages_per_browser
    )
    return _scheduled_scan_executor
