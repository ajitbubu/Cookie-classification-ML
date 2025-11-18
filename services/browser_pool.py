"""
Browser pool for managing and reusing Playwright browser instances.
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import Stealth

logger = logging.getLogger(__name__)
stealth = Stealth()


class BrowserInstance:
    """Wrapper for a browser instance with health tracking."""
    
    def __init__(self, browser: Browser, instance_id: int):
        """
        Initialize browser instance.
        
        Args:
            browser: Playwright browser object
            instance_id: Unique instance ID
        """
        self.browser = browser
        self.instance_id = instance_id
        self.created_at = datetime.utcnow()
        self.last_used = datetime.utcnow()
        self.use_count = 0
        self.is_healthy = True
        self.contexts: Dict[str, BrowserContext] = {}
    
    async def create_context(
        self,
        user_agent: Optional[str] = None,
        viewport: Optional[Dict[str, int]] = None
    ) -> BrowserContext:
        """
        Create a new browser context.
        
        Args:
            user_agent: Optional custom user agent
            viewport: Optional viewport dimensions
            
        Returns:
            BrowserContext
        """
        context = await self.browser.new_context(
            user_agent=user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport=viewport or {"width": 1366, "height": 768}
        )
        
        # Apply stealth
        await stealth.apply_stealth_async(context)
        
        # Add anti-detection script
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        """)
        
        context_id = f"ctx_{len(self.contexts)}"
        self.contexts[context_id] = context
        
        return context
    
    async def close_context(self, context: BrowserContext):
        """Close a browser context."""
        try:
            await context.close()
            # Remove from tracking
            self.contexts = {k: v for k, v in self.contexts.items() if v != context}
        except Exception as e:
            logger.warning(f"Failed to close context: {e}")
    
    async def close_all_contexts(self):
        """Close all browser contexts."""
        for context in list(self.contexts.values()):
            await self.close_context(context)
    
    def mark_used(self):
        """Mark browser as used."""
        self.last_used = datetime.utcnow()
        self.use_count += 1
    
    def age_seconds(self) -> float:
        """Get age of browser instance in seconds."""
        return (datetime.utcnow() - self.created_at).total_seconds()
    
    def idle_seconds(self) -> float:
        """Get idle time in seconds."""
        return (datetime.utcnow() - self.last_used).total_seconds()
    
    async def health_check(self) -> bool:
        """
        Perform health check on browser instance.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to create and close a test context
            test_context = await self.browser.new_context()
            test_page = await test_context.new_page()
            await test_page.goto("about:blank", timeout=5000)
            await test_page.close()
            await test_context.close()
            
            self.is_healthy = True
            return True
        except Exception as e:
            logger.warning(f"Browser {self.instance_id} health check failed: {e}")
            self.is_healthy = False
            return False
    
    async def close(self):
        """Close the browser instance."""
        try:
            await self.close_all_contexts()
            await self.browser.close()
            logger.info(f"Browser {self.instance_id} closed (used {self.use_count} times)")
        except Exception as e:
            logger.error(f"Failed to close browser {self.instance_id}: {e}")


class BrowserPool:
    """
    Pool of browser instances for reuse across scans.
    
    Features:
    - Lazy initialization of browser instances
    - Automatic health checks
    - Instance recycling based on age and usage
    - Graceful shutdown
    """
    
    def __init__(
        self,
        pool_size: int = 5,
        max_age_seconds: int = 3600,
        max_idle_seconds: int = 300,
        max_uses_per_instance: int = 100
    ):
        """
        Initialize browser pool.
        
        Args:
            pool_size: Maximum number of browser instances (1-10)
            max_age_seconds: Maximum age before recycling (default 1 hour)
            max_idle_seconds: Maximum idle time before recycling (default 5 minutes)
            max_uses_per_instance: Maximum uses before recycling (default 100)
        """
        if pool_size < 1 or pool_size > 10:
            raise ValueError("pool_size must be between 1 and 10")
        
        self.pool_size = pool_size
        self.max_age_seconds = max_age_seconds
        self.max_idle_seconds = max_idle_seconds
        self.max_uses_per_instance = max_uses_per_instance
        
        self.pool: asyncio.Queue = asyncio.Queue(maxsize=pool_size)
        self.instances: Dict[int, BrowserInstance] = {}
        self.next_instance_id = 0
        self.playwright = None
        self.is_initialized = False
        self.is_closed = False
        
        self._lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None
        
        logger.info(f"BrowserPool initialized: size={pool_size}, max_age={max_age_seconds}s")
    
    async def initialize(self):
        """Initialize the browser pool."""
        async with self._lock:
            if self.is_initialized:
                return
            
            logger.info("Initializing browser pool...")
            self.playwright = await async_playwright().start()
            
            # Pre-create initial browsers
            for _ in range(min(2, self.pool_size)):  # Start with 2 browsers
                await self._create_browser()
            
            # Start health check task
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            self.is_initialized = True
            logger.info("Browser pool initialized")
    
    async def _create_browser(self) -> BrowserInstance:
        """Create a new browser instance."""
        browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-http2",
                "--disable-dev-shm-usage",
                "--no-sandbox"
            ]
        )
        
        instance = BrowserInstance(browser, self.next_instance_id)
        self.next_instance_id += 1
        self.instances[instance.instance_id] = instance
        
        logger.info(f"Created browser instance {instance.instance_id}")
        return instance
    
    async def acquire(self) -> BrowserInstance:
        """
        Acquire a browser instance from the pool.
        
        Returns:
            BrowserInstance
        """
        if not self.is_initialized:
            await self.initialize()
        
        if self.is_closed:
            raise RuntimeError("Browser pool is closed")
        
        # Try to get from pool
        try:
            instance = await asyncio.wait_for(self.pool.get(), timeout=1.0)
            
            # Check if instance needs recycling
            if self._should_recycle(instance):
                logger.info(f"Recycling browser {instance.instance_id}")
                await instance.close()
                del self.instances[instance.instance_id]
                instance = await self._create_browser()
            
            instance.mark_used()
            return instance
            
        except asyncio.TimeoutError:
            # Pool is empty, create new if under limit
            if len(self.instances) < self.pool_size:
                instance = await self._create_browser()
                instance.mark_used()
                return instance
            else:
                # Wait for an instance to become available
                instance = await self.pool.get()
                
                if self._should_recycle(instance):
                    await instance.close()
                    del self.instances[instance.instance_id]
                    instance = await self._create_browser()
                
                instance.mark_used()
                return instance
    
    async def release(self, instance: BrowserInstance):
        """
        Release a browser instance back to the pool.
        
        Args:
            instance: BrowserInstance to release
        """
        if self.is_closed:
            await instance.close()
            return
        
        # Close all contexts before returning to pool
        await instance.close_all_contexts()
        
        # Check if should recycle
        if self._should_recycle(instance):
            logger.info(f"Recycling browser {instance.instance_id} on release")
            await instance.close()
            del self.instances[instance.instance_id]
            
            # Create replacement if pool not full
            if len(self.instances) < self.pool_size:
                new_instance = await self._create_browser()
                await self.pool.put(new_instance)
        else:
            # Return to pool
            await self.pool.put(instance)
    
    def _should_recycle(self, instance: BrowserInstance) -> bool:
        """
        Check if browser instance should be recycled.
        
        Args:
            instance: BrowserInstance to check
            
        Returns:
            True if should recycle, False otherwise
        """
        # Check age
        if instance.age_seconds() > self.max_age_seconds:
            logger.debug(f"Browser {instance.instance_id} exceeded max age")
            return True
        
        # Check usage count
        if instance.use_count >= self.max_uses_per_instance:
            logger.debug(f"Browser {instance.instance_id} exceeded max uses")
            return True
        
        # Check health
        if not instance.is_healthy:
            logger.debug(f"Browser {instance.instance_id} is unhealthy")
            return True
        
        return False
    
    async def _health_check_loop(self):
        """Background task to perform periodic health checks."""
        while not self.is_closed:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Check all instances
                for instance in list(self.instances.values()):
                    # Skip recently used instances
                    if instance.idle_seconds() < 30:
                        continue
                    
                    # Perform health check
                    is_healthy = await instance.health_check()
                    
                    if not is_healthy:
                        logger.warning(f"Browser {instance.instance_id} failed health check")
                        # Will be recycled on next acquire/release
                
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
    
    async def close(self):
        """Close the browser pool and all instances."""
        if self.is_closed:
            return
        
        logger.info("Closing browser pool...")
        self.is_closed = True
        
        # Cancel health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Close all instances
        for instance in list(self.instances.values()):
            await instance.close()
        
        self.instances.clear()
        
        # Stop playwright
        if self.playwright:
            await self.playwright.stop()
        
        logger.info("Browser pool closed")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get pool statistics.
        
        Returns:
            Dict with pool statistics
        """
        return {
            "pool_size": self.pool_size,
            "active_instances": len(self.instances),
            "available_instances": self.pool.qsize(),
            "total_uses": sum(i.use_count for i in self.instances.values()),
            "instances": [
                {
                    "id": i.instance_id,
                    "age_seconds": i.age_seconds(),
                    "idle_seconds": i.idle_seconds(),
                    "use_count": i.use_count,
                    "is_healthy": i.is_healthy,
                    "active_contexts": len(i.contexts)
                }
                for i in self.instances.values()
            ]
        }


# Global browser pool instance (singleton)
_global_pool: Optional[BrowserPool] = None


async def get_browser_pool(
    pool_size: int = 5,
    **kwargs
) -> BrowserPool:
    """
    Get or create the global browser pool.
    
    Args:
        pool_size: Pool size (only used on first call)
        **kwargs: Additional BrowserPool arguments
        
    Returns:
        BrowserPool instance
    """
    global _global_pool
    
    if _global_pool is None:
        _global_pool = BrowserPool(pool_size=pool_size, **kwargs)
        await _global_pool.initialize()
    
    return _global_pool


async def close_browser_pool():
    """Close the global browser pool."""
    global _global_pool
    
    if _global_pool:
        await _global_pool.close()
        _global_pool = None
