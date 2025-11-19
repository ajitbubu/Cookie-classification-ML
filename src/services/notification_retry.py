"""
Retry logic with exponential backoff for notification delivery.
"""

import asyncio
import logging
import functools
from typing import Callable, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ExponentialBackoff:
    """
    Exponential backoff calculator for retry delays.
    """
    
    def __init__(
        self,
        base_delay: float = 2.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0
    ):
        """
        Initialize exponential backoff calculator.
        
        Args:
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            multiplier: Multiplier for each retry
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt number.
        
        Args:
            attempt: Attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (self.multiplier ** attempt)
        return min(delay, self.max_delay)


def retry_with_exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    multiplier: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying async functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        multiplier: Multiplier for each retry
        exceptions: Tuple of exceptions to catch and retry
        
    Returns:
        Decorated function
        
    Example:
        @retry_with_exponential_backoff(max_retries=3)
        async def send_notification():
            # Your code here
            pass
    """
    backoff = ExponentialBackoff(base_delay, max_delay, multiplier)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    # Execute the function
                    result = await func(*args, **kwargs)
                    
                    # Log success if this was a retry
                    if attempt > 0:
                        logger.info(
                            f"{func.__name__} succeeded on attempt {attempt + 1}/{max_retries + 1}"
                        )
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    
                    # Check if we should retry
                    if attempt < max_retries:
                        delay = backoff.calculate_delay(attempt)
                        logger.warning(
                            f"{func.__name__} failed on attempt {attempt + 1}/{max_retries + 1}: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}",
                            exc_info=True
                        )
            
            # All retries exhausted, raise the last exception
            raise last_exception
        
        return wrapper
    return decorator


class RetryableNotificationDelivery:
    """
    Wrapper for notification delivery with retry logic.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 2.0,
        max_delay: float = 60.0
    ):
        """
        Initialize retryable notification delivery.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
        """
        self.max_retries = max_retries
        self.backoff = ExponentialBackoff(base_delay, max_delay)
    
    async def deliver_with_retry(
        self,
        delivery_func: Callable,
        *args,
        **kwargs
    ) -> tuple[bool, Optional[str]]:
        """
        Deliver notification with retry logic.
        
        Args:
            delivery_func: Async function to call for delivery
            *args: Positional arguments for delivery function
            **kwargs: Keyword arguments for delivery function
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Attempt delivery
                success = await delivery_func(*args, **kwargs)
                
                if success:
                    if attempt > 0:
                        logger.info(f"Delivery succeeded on attempt {attempt + 1}/{self.max_retries + 1}")
                    return True, None
                else:
                    last_error = "Delivery function returned False"
                    
                    # Retry if not last attempt
                    if attempt < self.max_retries:
                        delay = self.backoff.calculate_delay(attempt)
                        logger.warning(
                            f"Delivery failed on attempt {attempt + 1}/{self.max_retries + 1}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                    
            except Exception as e:
                last_error = str(e)
                logger.error(
                    f"Delivery error on attempt {attempt + 1}/{self.max_retries + 1}: {e}",
                    exc_info=True
                )
                
                # Retry if not last attempt
                if attempt < self.max_retries:
                    delay = self.backoff.calculate_delay(attempt)
                    logger.warning(f"Retrying in {delay:.2f}s...")
                    await asyncio.sleep(delay)
        
        # All retries exhausted
        logger.error(f"Delivery failed after {self.max_retries + 1} attempts: {last_error}")
        return False, last_error


class RetryStats:
    """
    Statistics tracker for retry operations.
    """
    
    def __init__(self):
        """Initialize retry statistics."""
        self.total_attempts = 0
        self.successful_first_attempt = 0
        self.successful_after_retry = 0
        self.failed_after_all_retries = 0
        self.total_retry_count = 0
        self.last_reset = datetime.utcnow()
    
    def record_success(self, attempt: int):
        """
        Record a successful delivery.
        
        Args:
            attempt: Attempt number (0-indexed)
        """
        self.total_attempts += 1
        
        if attempt == 0:
            self.successful_first_attempt += 1
        else:
            self.successful_after_retry += 1
            self.total_retry_count += attempt
    
    def record_failure(self, attempts: int):
        """
        Record a failed delivery after all retries.
        
        Args:
            attempts: Total number of attempts made
        """
        self.total_attempts += 1
        self.failed_after_all_retries += 1
        self.total_retry_count += (attempts - 1)
    
    def get_stats(self) -> dict:
        """
        Get retry statistics.
        
        Returns:
            Dictionary of statistics
        """
        success_rate = 0.0
        if self.total_attempts > 0:
            success_rate = (
                (self.successful_first_attempt + self.successful_after_retry) /
                self.total_attempts * 100
            )
        
        avg_retries = 0.0
        if self.total_attempts > 0:
            avg_retries = self.total_retry_count / self.total_attempts
        
        return {
            'total_attempts': self.total_attempts,
            'successful_first_attempt': self.successful_first_attempt,
            'successful_after_retry': self.successful_after_retry,
            'failed_after_all_retries': self.failed_after_all_retries,
            'success_rate': round(success_rate, 2),
            'average_retries': round(avg_retries, 2),
            'since': self.last_reset.isoformat()
        }
    
    def reset(self):
        """Reset statistics."""
        self.total_attempts = 0
        self.successful_first_attempt = 0
        self.successful_after_retry = 0
        self.failed_after_all_retries = 0
        self.total_retry_count = 0
        self.last_reset = datetime.utcnow()


# Global retry stats instance
_retry_stats = RetryStats()


def get_retry_stats() -> RetryStats:
    """Get the global retry statistics instance."""
    return _retry_stats
