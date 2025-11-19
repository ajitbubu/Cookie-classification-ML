"""
Distributed locking service using Redis.

This module provides distributed locking capabilities to prevent duplicate
job execution across multiple scheduler instances.
"""

import logging
import time
import uuid
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DistributedLock:
    """
    Distributed lock implementation using Redis.
    
    Prevents duplicate job execution across multiple scheduler instances
    by acquiring exclusive locks before job execution.
    """
    
    def __init__(self, redis_client, lock_prefix: str = "lock:schedule"):
        """
        Initialize distributed lock manager.
        
        Args:
            redis_client: RedisClient instance
            lock_prefix: Prefix for lock keys
        """
        self.redis_client = redis_client
        self.lock_prefix = lock_prefix
        self.instance_id = str(uuid.uuid4())[:8]  # Unique instance identifier
        logger.info(f"DistributedLock initialized with instance_id: {self.instance_id}")
    
    def _build_lock_key(self, resource_id: str) -> str:
        """Build lock key for a resource."""
        return f"{self.lock_prefix}:{resource_id}"
    
    def acquire(
        self,
        resource_id: str,
        timeout: int = 60,
        blocking: bool = True,
        blocking_timeout: Optional[int] = None
    ) -> Optional[str]:
        """
        Acquire a distributed lock for a resource.
        
        Args:
            resource_id: Unique identifier for the resource (e.g., schedule_id or domain)
            timeout: Lock timeout in seconds (auto-release after this time)
            blocking: Whether to block waiting for lock
            blocking_timeout: How long to wait for lock in seconds (None = forever)
            
        Returns:
            Lock token if acquired, None otherwise
        """
        lock_key = self._build_lock_key(resource_id)
        lock_token = f"{self.instance_id}:{uuid.uuid4()}"
        
        start_time = time.time()
        
        while True:
            # Try to acquire lock using SET NX (set if not exists)
            acquired = self.redis_client.set(
                lock_key,
                lock_token,
                ttl=timeout,
                nx=True  # Only set if key doesn't exist
            )
            
            if acquired:
                logger.debug(f"Lock acquired for {resource_id} with token {lock_token}")
                return lock_token
            
            # If not blocking, return immediately
            if not blocking:
                logger.debug(f"Failed to acquire lock for {resource_id} (non-blocking)")
                return None
            
            # Check if blocking timeout exceeded
            if blocking_timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= blocking_timeout:
                    logger.warning(
                        f"Failed to acquire lock for {resource_id} "
                        f"after {elapsed:.2f}s (timeout: {blocking_timeout}s)"
                    )
                    return None
            
            # Wait a bit before retrying
            time.sleep(0.1)
    
    def release(self, resource_id: str, lock_token: str) -> bool:
        """
        Release a distributed lock.
        
        Args:
            resource_id: Resource identifier
            lock_token: Token returned by acquire()
            
        Returns:
            True if lock was released, False otherwise
        """
        lock_key = self._build_lock_key(resource_id)
        
        # Use Lua script to atomically check token and delete
        # This prevents releasing someone else's lock
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        try:
            result = self.redis_client.client.eval(lua_script, 1, lock_key, lock_token)
            if result:
                logger.debug(f"Lock released for {resource_id}")
                return True
            else:
                logger.warning(
                    f"Failed to release lock for {resource_id} "
                    f"(token mismatch or already released)"
                )
                return False
        except Exception as e:
            logger.error(f"Error releasing lock for {resource_id}: {e}")
            return False
    
    def extend(self, resource_id: str, lock_token: str, additional_time: int) -> bool:
        """
        Extend the timeout of an existing lock.
        
        Args:
            resource_id: Resource identifier
            lock_token: Token returned by acquire()
            additional_time: Additional seconds to extend the lock
            
        Returns:
            True if lock was extended, False otherwise
        """
        lock_key = self._build_lock_key(resource_id)
        
        # Use Lua script to atomically check token and extend TTL
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """
        
        try:
            result = self.redis_client.client.eval(
                lua_script, 1, lock_key, lock_token, additional_time
            )
            if result:
                logger.debug(f"Lock extended for {resource_id} by {additional_time}s")
                return True
            else:
                logger.warning(f"Failed to extend lock for {resource_id} (token mismatch)")
                return False
        except Exception as e:
            logger.error(f"Error extending lock for {resource_id}: {e}")
            return False
    
    def is_locked(self, resource_id: str) -> bool:
        """
        Check if a resource is currently locked.
        
        Args:
            resource_id: Resource identifier
            
        Returns:
            True if locked, False otherwise
        """
        lock_key = self._build_lock_key(resource_id)
        return self.redis_client.exists(lock_key) > 0
    
    def get_lock_owner(self, resource_id: str) -> Optional[str]:
        """
        Get the current owner (token) of a lock.
        
        Args:
            resource_id: Resource identifier
            
        Returns:
            Lock token if locked, None otherwise
        """
        lock_key = self._build_lock_key(resource_id)
        return self.redis_client.get(lock_key)
    
    @contextmanager
    def lock(
        self,
        resource_id: str,
        timeout: int = 60,
        blocking: bool = True,
        blocking_timeout: Optional[int] = None
    ):
        """
        Context manager for acquiring and releasing locks.
        
        Usage:
            with lock_manager.lock("schedule_123"):
                # Execute job
                pass
        
        Args:
            resource_id: Resource identifier
            timeout: Lock timeout in seconds
            blocking: Whether to block waiting for lock
            blocking_timeout: How long to wait for lock
            
        Yields:
            True if lock acquired, False otherwise
        """
        lock_token = self.acquire(
            resource_id,
            timeout=timeout,
            blocking=blocking,
            blocking_timeout=blocking_timeout
        )
        
        try:
            yield lock_token is not None
        finally:
            if lock_token:
                self.release(resource_id, lock_token)


# Singleton instance
_distributed_lock: Optional[DistributedLock] = None


def get_distributed_lock() -> DistributedLock:
    """Get the global distributed lock instance."""
    global _distributed_lock
    if _distributed_lock is None:
        raise RuntimeError(
            "Distributed lock not initialized. Call init_distributed_lock() first."
        )
    return _distributed_lock


def init_distributed_lock(redis_client, lock_prefix: str = "lock:schedule") -> DistributedLock:
    """Initialize the global distributed lock instance."""
    global _distributed_lock
    _distributed_lock = DistributedLock(redis_client, lock_prefix)
    return _distributed_lock
