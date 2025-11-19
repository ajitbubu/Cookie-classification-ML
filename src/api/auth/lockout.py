"""
Account lockout mechanism for preventing brute force attacks.

Tracks failed login attempts and locks accounts after exceeding threshold.
"""

import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta
from uuid import UUID

from src.cache.redis_client import get_redis_client
from src.api.auth.audit import get_audit_logger

logger = logging.getLogger(__name__)


class AccountLockoutManager:
    """
    Manager for account lockout functionality.
    
    Tracks failed login attempts in Redis and locks accounts after
    exceeding the configured threshold within a time window.
    """
    
    def __init__(
        self,
        max_attempts: int = 5,
        lockout_duration_minutes: int = 15,
        attempt_window_minutes: int = 15
    ):
        """
        Initialize account lockout manager.
        
        Args:
            max_attempts: Maximum failed attempts before lockout
            lockout_duration_minutes: Duration of lockout in minutes
            attempt_window_minutes: Time window for counting attempts
        """
        self._redis = None
        self._audit_logger = None
        self.max_attempts = max_attempts
        self.lockout_duration_minutes = lockout_duration_minutes
        self.attempt_window_minutes = attempt_window_minutes
        
        logger.info(
            f"Account lockout manager initialized: "
            f"max_attempts={max_attempts}, "
            f"lockout_duration={lockout_duration_minutes}min, "
            f"window={attempt_window_minutes}min"
        )
    
    @property
    def redis(self):
        """Lazy load Redis client."""
        if self._redis is None:
            self._redis = get_redis_client()
        return self._redis
    
    @property
    def audit_logger(self):
        """Lazy load audit logger."""
        if self._audit_logger is None:
            self._audit_logger = get_audit_logger()
        return self._audit_logger
    
    def _get_attempt_key(self, email: str) -> str:
        """Get Redis key for tracking login attempts."""
        return f"login_attempts:{email}"
    
    def _get_lockout_key(self, email: str) -> str:
        """Get Redis key for account lockout status."""
        return f"account_locked:{email}"
    
    def is_locked(self, email: str) -> Tuple[bool, Optional[datetime]]:
        """
        Check if an account is locked.
        
        Args:
            email: Email address to check
            
        Returns:
            Tuple of (is_locked, unlock_time)
        """
        lockout_key = self._get_lockout_key(email)
        
        # Check if lockout key exists
        lockout_data = self.redis.get(lockout_key)
        if lockout_data:
            # Account is locked
            ttl = self.redis.client.ttl(lockout_key)
            if ttl > 0:
                unlock_time = datetime.utcnow() + timedelta(seconds=ttl)
                logger.info(f"Account {email} is locked until {unlock_time}")
                return True, unlock_time
            else:
                # Lockout expired, clean up
                self.redis.delete(lockout_key)
                return False, None
        
        return False, None
    
    def record_failed_attempt(
        self,
        email: str,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, int, Optional[datetime]]:
        """
        Record a failed login attempt.
        
        Args:
            email: Email address
            ip_address: IP address of the attempt
            
        Returns:
            Tuple of (should_lock, attempt_count, unlock_time)
        """
        attempt_key = self._get_attempt_key(email)
        
        # Increment attempt counter
        attempt_count = self.redis.incr(attempt_key)
        
        # Set expiration on first attempt
        if attempt_count == 1:
            self.redis.expire(attempt_key, self.attempt_window_minutes * 60)
        
        logger.info(
            f"Failed login attempt {attempt_count}/{self.max_attempts} "
            f"for {email} from {ip_address}"
        )
        
        # Check if we should lock the account
        if attempt_count >= self.max_attempts:
            unlock_time = self._lock_account(email, attempt_count, ip_address)
            return True, attempt_count, unlock_time
        
        return False, attempt_count, None
    
    def _lock_account(
        self,
        email: str,
        failed_attempts: int,
        ip_address: Optional[str] = None
    ) -> datetime:
        """
        Lock an account.
        
        Args:
            email: Email address to lock
            failed_attempts: Number of failed attempts
            ip_address: IP address of the attempts
            
        Returns:
            Unlock time
        """
        lockout_key = self._get_lockout_key(email)
        lockout_duration_seconds = self.lockout_duration_minutes * 60
        
        # Set lockout in Redis
        self.redis.set(
            lockout_key,
            datetime.utcnow().isoformat(),
            ttl=lockout_duration_seconds
        )
        
        unlock_time = datetime.utcnow() + timedelta(seconds=lockout_duration_seconds)
        
        logger.warning(
            f"Account locked: {email} after {failed_attempts} failed attempts. "
            f"Unlock time: {unlock_time}"
        )
        
        # Log to audit trail
        self.audit_logger.log_account_lockout(
            email=email,
            ip_address=ip_address,
            failed_attempts=failed_attempts
        )
        
        return unlock_time
    
    def reset_attempts(self, email: str):
        """
        Reset failed login attempts for an account.
        
        Args:
            email: Email address
        """
        attempt_key = self._get_attempt_key(email)
        self.redis.delete(attempt_key)
        logger.info(f"Reset login attempts for {email}")
    
    def unlock_account(self, email: str, admin_user_id: Optional[UUID] = None):
        """
        Manually unlock an account (admin action).
        
        Args:
            email: Email address to unlock
            admin_user_id: ID of admin performing the unlock
        """
        lockout_key = self._get_lockout_key(email)
        attempt_key = self._get_attempt_key(email)
        
        # Remove lockout and attempts
        self.redis.delete(lockout_key, attempt_key)
        
        logger.info(f"Account unlocked: {email} by admin {admin_user_id}")
        
        # Log to audit trail
        from src.api.auth.audit import AuditAction, ResourceType, AuditStatus
        self.audit_logger.log_event(
            action=AuditAction.ACCOUNT_UNLOCKED,
            resource_type=ResourceType.USER,
            status=AuditStatus.SUCCESS,
            user_id=admin_user_id,
            details={
                "email": email,
                "reason": "Manual unlock by administrator"
            }
        )
    
    def get_attempt_count(self, email: str) -> int:
        """
        Get current failed attempt count for an account.
        
        Args:
            email: Email address
            
        Returns:
            Number of failed attempts
        """
        attempt_key = self._get_attempt_key(email)
        count = self.redis.get(attempt_key)
        return int(count) if count else 0
    
    def get_lockout_info(self, email: str) -> dict:
        """
        Get detailed lockout information for an account.
        
        Args:
            email: Email address
            
        Returns:
            Dictionary with lockout information
        """
        is_locked, unlock_time = self.is_locked(email)
        attempt_count = self.get_attempt_count(email)
        
        info = {
            "email": email,
            "is_locked": is_locked,
            "unlock_time": unlock_time.isoformat() if unlock_time else None,
            "failed_attempts": attempt_count,
            "max_attempts": self.max_attempts,
            "remaining_attempts": max(0, self.max_attempts - attempt_count)
        }
        
        if is_locked and unlock_time:
            info["locked_for_seconds"] = int((unlock_time - datetime.utcnow()).total_seconds())
        
        return info


# Singleton instance
_lockout_manager: Optional[AccountLockoutManager] = None


def get_lockout_manager() -> AccountLockoutManager:
    """Get the global account lockout manager instance."""
    global _lockout_manager
    if _lockout_manager is None:
        _lockout_manager = AccountLockoutManager()
    return _lockout_manager


def init_lockout_manager(
    max_attempts: int = 5,
    lockout_duration_minutes: int = 15,
    attempt_window_minutes: int = 15
) -> AccountLockoutManager:
    """
    Initialize the global account lockout manager.
    
    Args:
        max_attempts: Maximum failed attempts before lockout
        lockout_duration_minutes: Duration of lockout in minutes
        attempt_window_minutes: Time window for counting attempts
        
    Returns:
        AccountLockoutManager instance
    """
    global _lockout_manager
    _lockout_manager = AccountLockoutManager(
        max_attempts=max_attempts,
        lockout_duration_minutes=lockout_duration_minutes,
        attempt_window_minutes=attempt_window_minutes
    )
    return _lockout_manager
