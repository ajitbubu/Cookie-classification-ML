"""
Wait strategies for handling dynamic content in web pages.
"""

import asyncio
import logging
from enum import Enum
from typing import Optional

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


class WaitStrategy(str, Enum):
    """Wait strategy enumeration."""
    TIMEOUT = "timeout"  # Simple timeout wait
    NETWORK_IDLE = "networkidle"  # Wait for network to be idle
    DOM_CONTENT_LOADED = "domcontentloaded"  # Wait for DOM content loaded
    LOAD = "load"  # Wait for full page load
    COMBINED = "combined"  # Combination of strategies


class DynamicContentWaiter:
    """
    Handler for waiting for dynamic content to load on web pages.
    
    Supports multiple wait strategies for JavaScript-heavy pages:
    - Simple timeout
    - Network idle (no network activity for 500ms)
    - DOM content loaded event
    - Full page load event
    - Combined strategy (multiple conditions)
    """
    
    def __init__(
        self,
        timeout_seconds: int = 5,
        strategy: WaitStrategy = WaitStrategy.TIMEOUT
    ):
        """
        Initialize dynamic content waiter.
        
        Args:
            timeout_seconds: Maximum time to wait (5-60 seconds)
            strategy: Wait strategy to use
        """
        if timeout_seconds < 5 or timeout_seconds > 60:
            raise ValueError("timeout_seconds must be between 5 and 60")
        
        self.timeout_seconds = timeout_seconds
        self.strategy = strategy
        self.timeout_ms = timeout_seconds * 1000
        
        logger.debug(f"DynamicContentWaiter initialized: timeout={timeout_seconds}s, strategy={strategy}")
    
    async def wait_for_content(self, page: Page, url: Optional[str] = None) -> bool:
        """
        Wait for dynamic content to load based on configured strategy.
        
        Args:
            page: Playwright page object
            url: Optional URL being loaded (for logging)
            
        Returns:
            True if content loaded successfully, False if timeout
        """
        try:
            if self.strategy == WaitStrategy.TIMEOUT:
                return await self._wait_timeout(page)
            elif self.strategy == WaitStrategy.NETWORK_IDLE:
                return await self._wait_network_idle(page, url)
            elif self.strategy == WaitStrategy.DOM_CONTENT_LOADED:
                return await self._wait_dom_content_loaded(page, url)
            elif self.strategy == WaitStrategy.LOAD:
                return await self._wait_load(page, url)
            elif self.strategy == WaitStrategy.COMBINED:
                return await self._wait_combined(page, url)
            else:
                logger.warning(f"Unknown wait strategy: {self.strategy}, using timeout")
                return await self._wait_timeout(page)
        except Exception as e:
            logger.warning(f"Wait strategy failed: {e}")
            return False
    
    async def _wait_timeout(self, page: Page) -> bool:
        """Simple timeout wait."""
        try:
            await page.wait_for_timeout(self.timeout_ms)
            return True
        except Exception as e:
            logger.warning(f"Timeout wait failed: {e}")
            return False
    
    async def _wait_network_idle(self, page: Page, url: Optional[str]) -> bool:
        """
        Wait for network to be idle.
        
        Network is considered idle when there are no more than 0 network
        connections for at least 500ms.
        """
        try:
            await page.wait_for_load_state("networkidle", timeout=self.timeout_ms)
            logger.debug(f"Network idle reached for {url}")
            return True
        except PlaywrightTimeoutError:
            logger.warning(f"Network idle timeout for {url}")
            return False
        except Exception as e:
            logger.warning(f"Network idle wait failed: {e}")
            return False
    
    async def _wait_dom_content_loaded(self, page: Page, url: Optional[str]) -> bool:
        """
        Wait for DOM content loaded event.
        
        This event fires when the initial HTML document has been completely
        loaded and parsed, without waiting for stylesheets, images, and subframes.
        """
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=self.timeout_ms)
            logger.debug(f"DOM content loaded for {url}")
            return True
        except PlaywrightTimeoutError:
            logger.warning(f"DOM content loaded timeout for {url}")
            return False
        except Exception as e:
            logger.warning(f"DOM content loaded wait failed: {e}")
            return False
    
    async def _wait_load(self, page: Page, url: Optional[str]) -> bool:
        """
        Wait for full page load event.
        
        This event fires when the whole page has loaded, including all dependent
        resources such as stylesheets and images.
        """
        try:
            await page.wait_for_load_state("load", timeout=self.timeout_ms)
            logger.debug(f"Full page load completed for {url}")
            return True
        except PlaywrightTimeoutError:
            logger.warning(f"Full page load timeout for {url}")
            return False
        except Exception as e:
            logger.warning(f"Full page load wait failed: {e}")
            return False
    
    async def _wait_combined(self, page: Page, url: Optional[str]) -> bool:
        """
        Combined wait strategy.
        
        Waits for DOM content loaded, then network idle, with fallback to timeout.
        This provides the most comprehensive wait for dynamic content.
        """
        try:
            # First wait for DOM content loaded
            await page.wait_for_load_state("domcontentloaded", timeout=self.timeout_ms // 2)
            logger.debug(f"DOM content loaded for {url}")
            
            # Then wait for network idle
            await page.wait_for_load_state("networkidle", timeout=self.timeout_ms // 2)
            logger.debug(f"Network idle reached for {url}")
            
            return True
        except PlaywrightTimeoutError:
            logger.warning(f"Combined wait timeout for {url}, falling back to simple timeout")
            # Fallback to simple timeout for remaining time
            remaining_time = self.timeout_ms // 4
            if remaining_time > 0:
                await page.wait_for_timeout(remaining_time)
            return True
        except Exception as e:
            logger.warning(f"Combined wait failed: {e}")
            return False
    
    async def wait_for_selector(
        self,
        page: Page,
        selector: str,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Wait for a specific selector to appear on the page.
        
        Args:
            page: Playwright page object
            selector: CSS selector to wait for
            timeout: Optional timeout in milliseconds (uses default if not provided)
            
        Returns:
            True if selector appeared, False if timeout
        """
        try:
            await page.wait_for_selector(
                selector,
                timeout=timeout or self.timeout_ms,
                state="visible"
            )
            logger.debug(f"Selector '{selector}' appeared")
            return True
        except PlaywrightTimeoutError:
            logger.debug(f"Selector '{selector}' did not appear within timeout")
            return False
        except Exception as e:
            logger.warning(f"Wait for selector failed: {e}")
            return False
    
    async def wait_for_function(
        self,
        page: Page,
        expression: str,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Wait for a JavaScript expression to return truthy value.
        
        Args:
            page: Playwright page object
            expression: JavaScript expression to evaluate
            timeout: Optional timeout in milliseconds
            
        Returns:
            True if expression became truthy, False if timeout
        """
        try:
            await page.wait_for_function(
                expression,
                timeout=timeout or self.timeout_ms
            )
            logger.debug(f"Function '{expression}' returned truthy")
            return True
        except PlaywrightTimeoutError:
            logger.debug(f"Function '{expression}' did not return truthy within timeout")
            return False
        except Exception as e:
            logger.warning(f"Wait for function failed: {e}")
            return False


def create_waiter_from_params(
    wait_seconds: int,
    strategy: Optional[str] = None
) -> DynamicContentWaiter:
    """
    Factory function to create a DynamicContentWaiter from parameters.
    
    Args:
        wait_seconds: Timeout in seconds
        strategy: Optional strategy name (defaults to TIMEOUT)
        
    Returns:
        DynamicContentWaiter instance
    """
    wait_strategy = WaitStrategy.TIMEOUT
    
    if strategy:
        try:
            wait_strategy = WaitStrategy(strategy.lower())
        except ValueError:
            logger.warning(f"Invalid wait strategy '{strategy}', using TIMEOUT")
    
    return DynamicContentWaiter(
        timeout_seconds=wait_seconds,
        strategy=wait_strategy
    )
