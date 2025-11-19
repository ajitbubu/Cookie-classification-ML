"""
Test distributed locking functionality.
"""

import time
import logging
from cache.redis_client import init_redis_client
from services.distributed_lock import init_distributed_lock

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_basic_lock_acquire_release():
    """Test basic lock acquisition and release."""
    logger.info("Test 1: Basic lock acquire and release")
    
    # Initialize Redis client
    redis_client = init_redis_client(host='localhost', port=6379, db=0)
    
    # Initialize distributed lock
    lock_manager = init_distributed_lock(redis_client)
    
    # Acquire lock
    resource_id = "test_schedule_123"
    lock_token = lock_manager.acquire(resource_id, timeout=10, blocking=False)
    
    if lock_token:
        logger.info(f"✓ Lock acquired successfully: {lock_token}")
        
        # Verify lock is held
        is_locked = lock_manager.is_locked(resource_id)
        logger.info(f"✓ Lock status verified: {is_locked}")
        
        # Release lock
        released = lock_manager.release(resource_id, lock_token)
        logger.info(f"✓ Lock released: {released}")
        
        # Verify lock is released
        is_locked_after = lock_manager.is_locked(resource_id)
        logger.info(f"✓ Lock status after release: {is_locked_after}")
        
        return True
    else:
        logger.error("✗ Failed to acquire lock")
        return False


def test_duplicate_prevention():
    """Test that duplicate lock acquisition is prevented."""
    logger.info("\nTest 2: Duplicate lock prevention")
    
    redis_client = init_redis_client(host='localhost', port=6379, db=0)
    lock_manager = init_distributed_lock(redis_client)
    
    resource_id = "test_schedule_456"
    
    # First acquisition
    lock_token1 = lock_manager.acquire(resource_id, timeout=10, blocking=False)
    logger.info(f"✓ First lock acquired: {lock_token1}")
    
    # Second acquisition should fail (non-blocking)
    lock_token2 = lock_manager.acquire(resource_id, timeout=10, blocking=False)
    
    if lock_token2 is None:
        logger.info("✓ Second lock acquisition correctly prevented")
        success = True
    else:
        logger.error("✗ Second lock should not have been acquired")
        success = False
    
    # Release first lock
    if lock_token1:
        lock_manager.release(resource_id, lock_token1)
        logger.info("✓ First lock released")
    
    return success


def test_lock_timeout():
    """Test that locks auto-expire after timeout."""
    logger.info("\nTest 3: Lock timeout")
    
    redis_client = init_redis_client(host='localhost', port=6379, db=0)
    lock_manager = init_distributed_lock(redis_client)
    
    resource_id = "test_schedule_789"
    
    # Acquire lock with short timeout
    lock_token = lock_manager.acquire(resource_id, timeout=2, blocking=False)
    logger.info(f"✓ Lock acquired with 2s timeout: {lock_token}")
    
    # Verify lock is held
    is_locked = lock_manager.is_locked(resource_id)
    logger.info(f"✓ Lock is held: {is_locked}")
    
    # Wait for timeout
    logger.info("  Waiting 3 seconds for lock to expire...")
    time.sleep(3)
    
    # Verify lock has expired
    is_locked_after = lock_manager.is_locked(resource_id)
    
    if not is_locked_after:
        logger.info("✓ Lock correctly expired after timeout")
        return True
    else:
        logger.error("✗ Lock should have expired")
        return False


def test_context_manager():
    """Test lock context manager."""
    logger.info("\nTest 4: Context manager")
    
    redis_client = init_redis_client(host='localhost', port=6379, db=0)
    lock_manager = init_distributed_lock(redis_client)
    
    resource_id = "test_schedule_context"
    
    # Use context manager
    with lock_manager.lock(resource_id, timeout=10, blocking=False) as acquired:
        if acquired:
            logger.info("✓ Lock acquired via context manager")
            is_locked = lock_manager.is_locked(resource_id)
            logger.info(f"✓ Lock is held inside context: {is_locked}")
        else:
            logger.error("✗ Failed to acquire lock via context manager")
            return False
    
    # Verify lock is released after context
    is_locked_after = lock_manager.is_locked(resource_id)
    
    if not is_locked_after:
        logger.info("✓ Lock correctly released after context exit")
        return True
    else:
        logger.error("✗ Lock should have been released")
        return False


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Testing Distributed Lock Implementation")
    logger.info("=" * 60)
    
    try:
        results = []
        
        results.append(("Basic lock acquire/release", test_basic_lock_acquire_release()))
        results.append(("Duplicate prevention", test_duplicate_prevention()))
        results.append(("Lock timeout", test_lock_timeout()))
        results.append(("Context manager", test_context_manager()))
        
        logger.info("\n" + "=" * 60)
        logger.info("Test Results Summary")
        logger.info("=" * 60)
        
        for test_name, passed in results:
            status = "✓ PASS" if passed else "✗ FAIL"
            logger.info(f"{status}: {test_name}")
        
        all_passed = all(result[1] for result in results)
        
        if all_passed:
            logger.info("\n✓ All tests passed!")
        else:
            logger.info("\n✗ Some tests failed")
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}", exc_info=True)
