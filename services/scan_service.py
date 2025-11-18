"""
Scan service with real-time progress streaming.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable, List
from uuid import UUID, uuid4
from datetime import datetime
from urllib.parse import urljoin, urlparse

import asyncpg
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

from models.scan import ScanResult, ScanParams, ScanMode, ScanStatus, ScanProgress, Cookie
from models.profile import ScanProfile
from services.wait_strategies import DynamicContentWaiter, create_waiter_from_params
from services.browser_pool import BrowserPool, get_browser_pool

logger = logging.getLogger(__name__)
stealth = Stealth()


class ScanService:
    """Service for managing scans with real-time progress streaming."""
    
    def __init__(
        self,
        db_pool: asyncpg.Pool,
        redis_client=None,
        browser_pool: Optional[BrowserPool] = None
    ):
        """Initialize scan service."""
        self.db_pool = db_pool
        self.redis_client = redis_client
        self.browser_pool = browser_pool
        self.active_scans: Dict[UUID, Dict[str, Any]] = {}
    
    async def create_scan(
        self,
        domain: str,
        domain_config_id: UUID,
        scan_mode: ScanMode,
        params: ScanParams,
        profile: Optional[ScanProfile] = None
    ) -> UUID:
        """
        Create a new scan record in database.
        
        Args:
            domain: Domain to scan
            domain_config_id: Domain configuration ID
            scan_mode: Scan mode
            params: Scan parameters
            profile: Optional scan profile
            
        Returns:
            Scan ID
        """
        scan_id = uuid4()
        now = datetime.utcnow()
        
        # Merge profile config if provided
        if profile:
            params = self._merge_profile_params(params, profile)
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO scan_results (
                    scan_id, domain_config_id, domain, scan_mode,
                    timestamp_utc, status, params, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                scan_id,
                domain_config_id,
                domain,
                scan_mode,
                now,
                ScanStatus.PENDING,
                params.dict(),
                now,
                now
            )
        
        return scan_id
    
    async def execute_scan_with_progress(
        self,
        scan_id: UUID,
        domain: str,
        params: ScanParams,
        scan_mode: ScanMode,
        progress_callback: Optional[Callable[[ScanProgress], None]] = None
    ) -> ScanResult:
        """
        Execute a scan with real-time progress updates.
        
        Args:
            scan_id: Scan ID
            domain: Domain to scan
            params: Scan parameters
            scan_mode: Scan mode
            progress_callback: Optional callback for progress updates
            
        Returns:
            ScanResult
        """
        start_time = time.time()
        
        # Initialize progress tracking
        progress_data = {
            'scan_id': scan_id,
            'status': ScanStatus.RUNNING,
            'pages_visited': 0,
            'cookies_found': 0,
            'current_page': None,
            'progress_percentage': 0.0
        }
        self.active_scans[scan_id] = progress_data
        
        # Update scan status to running
        await self._update_scan_status(scan_id, ScanStatus.RUNNING)
        
        # Send initial progress
        if progress_callback:
            await progress_callback(self._create_progress(progress_data))
        
        try:
            # Execute scan based on mode
            if scan_mode == ScanMode.REALTIME:
                result = await self._execute_realtime_scan(
                    scan_id, domain, params, progress_callback
                )
            elif scan_mode == ScanMode.QUICK:
                result = await self._execute_quick_scan(
                    scan_id, domain, params, progress_callback
                )
            elif scan_mode == ScanMode.DEEP:
                result = await self._execute_deep_scan(
                    scan_id, domain, params, progress_callback
                )
            else:
                raise ValueError(f"Unsupported scan mode: {scan_mode}")
            
            duration = time.time() - start_time
            
            # Update scan with results
            await self._save_scan_result(scan_id, result, duration, ScanStatus.SUCCESS)
            
            # Final progress update
            progress_data['status'] = ScanStatus.SUCCESS
            progress_data['progress_percentage'] = 100.0
            if progress_callback:
                await progress_callback(self._create_progress(progress_data))
            
            return result
            
        except Exception as e:
            logger.exception(f"Scan {scan_id} failed: {e}")
            duration = time.time() - start_time
            
            # Update scan with error
            await self._update_scan_status(
                scan_id, ScanStatus.FAILED, error=str(e), duration=duration
            )
            
            # Error progress update
            progress_data['status'] = ScanStatus.FAILED
            if progress_callback:
                await progress_callback(self._create_progress(progress_data, message=str(e)))
            
            raise
        finally:
            # Clean up active scan tracking
            self.active_scans.pop(scan_id, None)
    
    async def _execute_realtime_scan(
        self,
        scan_id: UUID,
        domain: str,
        params: ScanParams,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Execute real-time scan with page-by-page streaming."""
        visited = set()
        cookie_map = {}
        storages_agg = {"localStorage": {}, "sessionStorage": {}}
        
        # Use browser pool if available, otherwise create new browser
        if self.browser_pool:
            browser_instance = await self.browser_pool.acquire()
            try:
                context = await browser_instance.create_context(
                    user_agent=params.user_agent,
                    viewport=params.viewport
                )
                
                page = await context.new_page()
                
                # Scan main page
                await self._scan_page_with_progress(
                    page, domain, domain, visited, cookie_map, storages_agg,
                    params, scan_id, progress_callback, follow_links=False
                )
                
                # Scan custom pages
                for custom_page in params.custom_pages:
                    url = custom_page if custom_page.startswith("http") else urljoin(domain, custom_page)
                    await self._scan_page_with_progress(
                        page, domain, url, visited, cookie_map, storages_agg,
                        params, scan_id, progress_callback, follow_links=False
                    )
                
                await browser_instance.close_context(context)
            finally:
                await self.browser_pool.release(browser_instance)
        else:
            # Fallback to creating new browser
            async with stealth.use_async(async_playwright()) as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--disable-http2"]
                )
                
                context = await browser.new_context(
                    user_agent=params.user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    viewport=params.viewport
                )
                await stealth.apply_stealth_async(context)
                
                page = await context.new_page()
                
                # Scan main page
                await self._scan_page_with_progress(
                    page, domain, domain, visited, cookie_map, storages_agg,
                    params, scan_id, progress_callback, follow_links=False
                )
                
                # Scan custom pages
                for custom_page in params.custom_pages:
                    url = custom_page if custom_page.startswith("http") else urljoin(domain, custom_page)
                    await self._scan_page_with_progress(
                        page, domain, url, visited, cookie_map, storages_agg,
                        params, scan_id, progress_callback, follow_links=False
                    )
                
                await browser.close()
        
        return {
            "cookies": list(cookie_map.values()),
            "storages": storages_agg,
            "pages_visited": list(visited)
        }
    
    async def _execute_quick_scan(
        self,
        scan_id: UUID,
        domain: str,
        params: ScanParams,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Execute quick scan (main page + custom pages, no deep crawl)."""
        return await self._execute_realtime_scan(scan_id, domain, params, progress_callback)
    
    async def _execute_deep_scan(
        self,
        scan_id: UUID,
        domain: str,
        params: ScanParams,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Execute deep scan with link following."""
        visited = set()
        cookie_map = {}
        storages_agg = {"localStorage": {}, "sessionStorage": {}}
        
        # Use browser pool if available
        if self.browser_pool:
            browser_instance = await self.browser_pool.acquire()
            try:
                context = await browser_instance.create_context(
                    user_agent=params.user_agent,
                    viewport=params.viewport
                )
                
                page = await context.new_page()
                
                # Deep crawl from main page
                await self._crawl_recursive(
                    page, domain, domain, visited, cookie_map, storages_agg,
                    params, scan_id, progress_callback, depth=0
                )
                
                await browser_instance.close_context(context)
            finally:
                await self.browser_pool.release(browser_instance)
        else:
            # Fallback to creating new browser
            async with stealth.use_async(async_playwright()) as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--disable-http2"]
                )
                
                context = await browser.new_context(
                    user_agent=params.user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    viewport=params.viewport
                )
                await stealth.apply_stealth_async(context)
                
                page = await context.new_page()
                
                # Deep crawl from main page
                await self._crawl_recursive(
                    page, domain, domain, visited, cookie_map, storages_agg,
                    params, scan_id, progress_callback, depth=0
                )
                
                await browser.close()
        
        return {
            "cookies": list(cookie_map.values()),
            "storages": storages_agg,
            "pages_visited": list(visited)
        }
    
    async def _scan_page_with_progress(
        self,
        page,
        base_domain: str,
        url: str,
        visited: set,
        cookie_map: dict,
        storages_agg: dict,
        params: ScanParams,
        scan_id: UUID,
        progress_callback: Optional[Callable],
        follow_links: bool = False
    ):
        """Scan a single page and report progress."""
        if url in visited:
            return
        
        # Update progress
        progress_data = self.active_scans.get(scan_id, {})
        progress_data['current_page'] = url
        if progress_callback:
            await progress_callback(self._create_progress(progress_data))
        
        # Navigate to page
        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            # Wait for dynamic content using configured strategy
            if params.wait_for_dynamic_content > 0:
                waiter = create_waiter_from_params(
                    wait_seconds=params.wait_for_dynamic_content,
                    strategy=params.wait_strategy
                )
                await waiter.wait_for_content(page, url)
            
            visited.add(url)
            
            # Collect cookies
            await self._collect_cookies(page.context, base_domain, cookie_map, before_accept=True)
            
            # Try to accept cookie banner
            try:
                btn = page.locator(params.accept_selector)
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(2000)
                    await self._collect_cookies(page.context, base_domain, cookie_map, before_accept=False)
            except Exception:
                pass
            
            # Collect storage
            storages = await self._collect_storages(page)
            storages_agg["localStorage"].update(storages.get("localStorage", {}))
            storages_agg["sessionStorage"].update(storages.get("sessionStorage", {}))
            
            # Update progress
            progress_data['pages_visited'] = len(visited)
            progress_data['cookies_found'] = len(cookie_map)
            if progress_callback:
                await progress_callback(self._create_progress(progress_data))
            
        except Exception as e:
            logger.warning(f"Failed to scan page {url}: {e}")
    
    async def _crawl_recursive(
        self,
        page,
        base_domain: str,
        url: str,
        visited: set,
        cookie_map: dict,
        storages_agg: dict,
        params: ScanParams,
        scan_id: UUID,
        progress_callback: Optional[Callable],
        depth: int = 0
    ):
        """Recursively crawl pages up to max depth."""
        if url in visited or depth > params.scan_depth:
            return
        
        if params.max_pages and len(visited) >= params.max_pages:
            return
        
        # Scan current page
        await self._scan_page_with_progress(
            page, base_domain, url, visited, cookie_map, storages_agg,
            params, scan_id, progress_callback, follow_links=True
        )
        
        # Follow links if not at max depth
        if depth < params.scan_depth:
            try:
                anchors = await page.eval_on_selector_all("a", "els => els.map(el => el.href)")
                base_parsed = urlparse(base_domain)
                
                for link in anchors:
                    if not link or link in visited:
                        continue
                    
                    parsed_link = urlparse(link)
                    
                    # Only follow internal links
                    if not parsed_link.netloc or parsed_link.netloc == base_parsed.netloc:
                        next_url = urljoin(base_domain, link)
                        await self._crawl_recursive(
                            page, base_domain, next_url, visited, cookie_map, storages_agg,
                            params, scan_id, progress_callback, depth + 1
                        )
            except Exception as e:
                logger.warning(f"Failed to extract links from {url}: {e}")
    
    async def _collect_cookies(self, context, base_domain: str, cookie_map: dict, before_accept: bool):
        """Collect cookies from browser context."""
        cookies = await context.cookies()
        
        for c in cookies:
            cookie_id = f"{c.get('name')}|{c.get('domain')}|{c.get('path')}"
            if cookie_id not in cookie_map:
                cookie_map[cookie_id] = {
                    "name": c.get("name"),
                    "domain": c.get("domain"),
                    "path": c.get("path", "/"),
                    "size": len(c.get("value", "")),
                    "http_only": c.get("httpOnly", False),
                    "secure": c.get("secure", False),
                    "same_site": c.get("sameSite"),
                    "set_after_accept": not before_accept
                }
    
    async def _collect_storages(self, page) -> Dict[str, Dict]:
        """Collect localStorage and sessionStorage."""
        try:
            local = await page.evaluate("""() => {
                const out = {};
                for(let i=0; i<localStorage.length; i++){
                    const k=localStorage.key(i);
                    out[k] = localStorage.getItem(k);
                }
                return out;
            }""")
        except Exception:
            local = {}
        
        try:
            session = await page.evaluate("""() => {
                const out = {};
                for(let i=0; i<sessionStorage.length; i++){
                    const k=sessionStorage.key(i);
                    out[k] = sessionStorage.getItem(k);
                }
                return out;
            }""")
        except Exception:
            session = {}
        
        return {"localStorage": local, "sessionStorage": session}
    
    async def _save_scan_result(
        self,
        scan_id: UUID,
        result: Dict[str, Any],
        duration: float,
        status: ScanStatus
    ):
        """Save scan result to database."""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE scan_results
                SET status = $1, duration_seconds = $2, total_cookies = $3,
                    page_count = $4, updated_at = $5
                WHERE scan_id = $6
                """,
                status,
                duration,
                len(result.get("cookies", [])),
                len(result.get("pages_visited", [])),
                datetime.utcnow(),
                scan_id
            )
    
    async def _update_scan_status(
        self,
        scan_id: UUID,
        status: ScanStatus,
        error: Optional[str] = None,
        duration: Optional[float] = None
    ):
        """Update scan status in database."""
        async with self.db_pool.acquire() as conn:
            if error:
                await conn.execute(
                    """
                    UPDATE scan_results
                    SET status = $1, error = $2, duration_seconds = $3, updated_at = $4
                    WHERE scan_id = $5
                    """,
                    status, error, duration, datetime.utcnow(), scan_id
                )
            else:
                await conn.execute(
                    """
                    UPDATE scan_results
                    SET status = $1, updated_at = $2
                    WHERE scan_id = $3
                    """,
                    status, datetime.utcnow(), scan_id
                )
    
    def _create_progress(
        self,
        progress_data: Dict[str, Any],
        message: Optional[str] = None
    ) -> ScanProgress:
        """Create ScanProgress object from progress data."""
        return ScanProgress(
            scan_id=progress_data['scan_id'],
            status=progress_data['status'],
            current_page=progress_data.get('current_page'),
            pages_visited=progress_data.get('pages_visited', 0),
            cookies_found=progress_data.get('cookies_found', 0),
            progress_percentage=progress_data.get('progress_percentage', 0.0),
            message=message
        )
    
    def _merge_profile_params(self, params: ScanParams, profile: ScanProfile) -> ScanParams:
        """Merge profile configuration into scan parameters."""
        return ScanParams(
            max_pages=params.max_pages or profile.max_pages,
            scan_depth=params.scan_depth or profile.max_depth,
            max_retries=params.max_retries or profile.max_retries,
            custom_pages=params.custom_pages or profile.custom_pages,
            accept_selector=params.accept_selector or profile.accept_button_selector,
            wait_for_dynamic_content=params.wait_for_dynamic_content or profile.wait_for_dynamic_content,
            follow_external_links=params.follow_external_links or profile.follow_external_links,
            collect_screenshots=params.collect_screenshots or profile.collect_screenshots,
            user_agent=params.user_agent or profile.user_agent,
            viewport=params.viewport or profile.viewport
        )
    
    async def get_scan_progress(self, scan_id: UUID) -> Optional[ScanProgress]:
        """Get current progress of an active scan."""
        progress_data = self.active_scans.get(scan_id)
        if progress_data:
            return self._create_progress(progress_data)
        return None
