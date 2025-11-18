"""
Audit logging system for security-relevant events.

This module provides comprehensive audit logging for:
- Authentication attempts (success and failure)
- Configuration changes (profiles, schedules)
- Data access operations (scan retrieval, report generation)
- Administrative actions
"""

import logging
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum

from database.connection import get_db_connection

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Enumeration of auditable actions."""
    
    # Authentication actions
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    API_KEY_CREATED = "api_key_created"
    API_KEY_DELETED = "api_key_deleted"
    API_KEY_USED = "api_key_used"
    PASSWORD_CHANGED = "password_changed"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    
    # Configuration changes
    PROFILE_CREATED = "profile_created"
    PROFILE_UPDATED = "profile_updated"
    PROFILE_DELETED = "profile_deleted"
    SCHEDULE_CREATED = "schedule_created"
    SCHEDULE_UPDATED = "schedule_updated"
    SCHEDULE_DELETED = "schedule_deleted"
    SCHEDULE_ENABLED = "schedule_enabled"
    SCHEDULE_DISABLED = "schedule_disabled"
    NOTIFICATION_PREFERENCES_UPDATED = "notification_preferences_updated"
    
    # Data access operations
    SCAN_CREATED = "scan_created"
    SCAN_ACCESSED = "scan_accessed"
    SCAN_DELETED = "scan_deleted"
    SCAN_CANCELLED = "scan_cancelled"
    REPORT_GENERATED = "report_generated"
    REPORT_ACCESSED = "report_accessed"
    REPORT_DOWNLOADED = "report_downloaded"
    DATA_EXPORTED = "data_exported"
    
    # Administrative actions
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    ROLE_CHANGED = "role_changed"
    SYSTEM_CONFIG_CHANGED = "system_config_changed"


class ResourceType(str, Enum):
    """Enumeration of resource types."""
    
    USER = "user"
    API_KEY = "api_key"
    PROFILE = "profile"
    SCHEDULE = "schedule"
    SCAN = "scan"
    REPORT = "report"
    NOTIFICATION = "notification"
    SYSTEM = "system"


class AuditStatus(str, Enum):
    """Enumeration of audit event statuses."""
    
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"


class AuditLogger:
    """
    Audit logger for security-relevant events.
    
    Logs all security-relevant events to the audit_logs table for
    compliance, security monitoring, and forensic analysis.
    """
    
    def __init__(self):
        """Initialize audit logger."""
        self.db = get_db_connection()
    
    def log_event(
        self,
        action: AuditAction,
        resource_type: ResourceType,
        status: AuditStatus,
        user_id: Optional[UUID] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log an audit event.
        
        Args:
            action: Action performed
            resource_type: Type of resource affected
            status: Status of the action (success, failure, error)
            user_id: ID of user performing the action
            resource_id: ID of the affected resource
            ip_address: IP address of the client
            user_agent: User agent string
            details: Additional context about the action
            
        Returns:
            True if logged successfully, False otherwise
        """
        try:
            query = """
                INSERT INTO audit_logs (
                    user_id, action, resource_type, resource_id,
                    ip_address, user_agent, status, details
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                str(user_id) if user_id else None,
                action.value if isinstance(action, AuditAction) else action,
                resource_type.value if isinstance(resource_type, ResourceType) else resource_type,
                resource_id,
                ip_address,
                user_agent,
                status.value if isinstance(status, AuditStatus) else status,
                details or {}
            )
            
            self.db.execute_query(query, params, fetch=False)
            
            logger.debug(
                f"Audit log created: action={action}, resource_type={resource_type}, "
                f"status={status}, user_id={user_id}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            # Don't raise exception - audit logging should not break application flow
            return False
    
    def log_authentication(
        self,
        success: bool,
        email: str,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        reason: Optional[str] = None
    ) -> bool:
        """
        Log an authentication attempt.
        
        Args:
            success: Whether authentication succeeded
            email: Email address used for authentication
            user_id: User ID (if authentication succeeded)
            ip_address: IP address of the client
            user_agent: User agent string
            reason: Reason for failure (if applicable)
            
        Returns:
            True if logged successfully
        """
        action = AuditAction.LOGIN_SUCCESS if success else AuditAction.LOGIN_FAILURE
        status = AuditStatus.SUCCESS if success else AuditStatus.FAILURE
        
        details = {"email": email}
        if reason:
            details["reason"] = reason
        
        return self.log_event(
            action=action,
            resource_type=ResourceType.USER,
            status=status,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
    
    def log_configuration_change(
        self,
        action: AuditAction,
        resource_type: ResourceType,
        resource_id: str,
        user_id: UUID,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> bool:
        """
        Log a configuration change.
        
        Args:
            action: Action performed (created, updated, deleted)
            resource_type: Type of resource (profile, schedule, etc.)
            resource_id: ID of the resource
            user_id: ID of user making the change
            changes: Dictionary of changes made
            ip_address: IP address of the client
            
        Returns:
            True if logged successfully
        """
        details = {}
        if changes:
            details["changes"] = changes
        
        return self.log_event(
            action=action,
            resource_type=resource_type,
            status=AuditStatus.SUCCESS,
            user_id=user_id,
            resource_id=resource_id,
            ip_address=ip_address,
            details=details
        )
    
    def log_data_access(
        self,
        action: AuditAction,
        resource_type: ResourceType,
        resource_id: str,
        user_id: UUID,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log a data access operation.
        
        Args:
            action: Action performed (accessed, downloaded, exported)
            resource_type: Type of resource (scan, report)
            resource_id: ID of the resource
            user_id: ID of user accessing the data
            ip_address: IP address of the client
            metadata: Additional metadata about the access
            
        Returns:
            True if logged successfully
        """
        return self.log_event(
            action=action,
            resource_type=resource_type,
            status=AuditStatus.SUCCESS,
            user_id=user_id,
            resource_id=resource_id,
            ip_address=ip_address,
            details=metadata or {}
        )
    
    def log_account_lockout(
        self,
        email: str,
        ip_address: Optional[str] = None,
        failed_attempts: int = 0
    ) -> bool:
        """
        Log an account lockout event.
        
        Args:
            email: Email address of the locked account
            ip_address: IP address of the client
            failed_attempts: Number of failed attempts that triggered lockout
            
        Returns:
            True if logged successfully
        """
        return self.log_event(
            action=AuditAction.ACCOUNT_LOCKED,
            resource_type=ResourceType.USER,
            status=AuditStatus.SUCCESS,
            ip_address=ip_address,
            details={
                "email": email,
                "failed_attempts": failed_attempts,
                "reason": "Too many failed login attempts"
            }
        )
    
    def get_audit_logs(
        self,
        user_id: Optional[UUID] = None,
        action: Optional[AuditAction] = None,
        resource_type: Optional[ResourceType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """
        Retrieve audit logs with filtering.
        
        Args:
            user_id: Filter by user ID
            action: Filter by action
            resource_type: Filter by resource type
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of audit log records
        """
        try:
            conditions = []
            params = []
            
            if user_id:
                conditions.append("user_id = %s")
                params.append(str(user_id))
            
            if action:
                conditions.append("action = %s")
                params.append(action.value if isinstance(action, AuditAction) else action)
            
            if resource_type:
                conditions.append("resource_type = %s")
                params.append(resource_type.value if isinstance(resource_type, ResourceType) else resource_type)
            
            if start_date:
                conditions.append("created_at >= %s")
                params.append(start_date)
            
            if end_date:
                conditions.append("created_at <= %s")
                params.append(end_date)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = f"""
                SELECT 
                    audit_id, user_id, action, resource_type, resource_id,
                    ip_address, user_agent, status, details, created_at
                FROM audit_logs
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            
            params.extend([limit, offset])
            
            results = self.db.execute_query(query, tuple(params), fetch=True)
            return results or []
            
        except Exception as e:
            logger.error(f"Failed to retrieve audit logs: {e}")
            return []
    
    def get_user_activity(
        self,
        user_id: UUID,
        days: int = 30,
        limit: int = 100
    ) -> list:
        """
        Get recent activity for a specific user.
        
        Args:
            user_id: User ID
            days: Number of days to look back
            limit: Maximum number of records
            
        Returns:
            List of audit log records
        """
        try:
            query = """
                SELECT 
                    audit_id, action, resource_type, resource_id,
                    ip_address, status, details, created_at
                FROM audit_logs
                WHERE user_id = %s
                    AND created_at >= NOW() - INTERVAL '%s days'
                ORDER BY created_at DESC
                LIMIT %s
            """
            
            results = self.db.execute_query(
                query,
                (str(user_id), days, limit),
                fetch=True
            )
            return results or []
            
        except Exception as e:
            logger.error(f"Failed to retrieve user activity: {e}")
            return []
    
    def get_failed_login_attempts(
        self,
        email: Optional[str] = None,
        ip_address: Optional[str] = None,
        minutes: int = 15
    ) -> int:
        """
        Get count of failed login attempts within a time window.
        
        Args:
            email: Email address to check
            ip_address: IP address to check
            minutes: Time window in minutes
            
        Returns:
            Count of failed login attempts
        """
        try:
            conditions = ["action = %s", "status = %s", "created_at >= NOW() - INTERVAL '%s minutes'"]
            params = [AuditAction.LOGIN_FAILURE.value, AuditStatus.FAILURE.value, minutes]
            
            if email:
                conditions.append("details->>'email' = %s")
                params.append(email)
            
            if ip_address:
                conditions.append("ip_address = %s")
                params.append(ip_address)
            
            where_clause = " AND ".join(conditions)
            
            query = f"""
                SELECT COUNT(*) as count
                FROM audit_logs
                WHERE {where_clause}
            """
            
            result = self.db.execute_query(query, tuple(params), fetch=True)
            return result[0]['count'] if result else 0
            
        except Exception as e:
            logger.error(f"Failed to get failed login attempts: {e}")
            return 0


# Singleton instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
