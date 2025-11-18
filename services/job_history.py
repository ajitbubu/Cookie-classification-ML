"""
Job execution history and audit trail service.

This module tracks all scheduled job executions, including success/failure status,
execution duration, and error details for auditing and monitoring purposes.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)


class JobHistory:
    """
    Service for tracking job execution history and audit trail.
    
    Logs all job executions to the database with detailed information
    about execution status, duration, and any errors encountered.
    """
    
    def __init__(self, db_connection):
        """
        Initialize job history service.
        
        Args:
            db_connection: DatabaseConnection instance
        """
        self.db = db_connection
    
    def start_execution(
        self,
        schedule_id: str,
        job_id: str,
        domain: str,
        domain_config_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Record the start of a job execution.
        
        Args:
            schedule_id: Schedule ID
            job_id: APScheduler job ID
            domain: Domain being scanned
            domain_config_id: Domain configuration ID
            metadata: Additional metadata
            
        Returns:
            Execution ID if recorded, None otherwise
        """
        execution_id = str(uuid.uuid4())
        
        query = """
            INSERT INTO job_executions (
                execution_id, schedule_id, job_id, domain, domain_config_id,
                status, started_at, metadata
            )
            VALUES (%s, %s, %s, %s, %s, 'started', NOW(), %s)
            RETURNING execution_id
        """
        
        try:
            import json
            result = self.db.execute_query(
                query,
                (
                    execution_id,
                    schedule_id,
                    job_id,
                    domain,
                    domain_config_id,
                    json.dumps(metadata or {})
                ),
                fetch=True
            )
            
            if result:
                logger.debug(f"Started execution {execution_id} for job {job_id}")
                return result[0]['execution_id']
            return None
        except Exception as e:
            logger.error(f"Failed to record job start for {job_id}: {e}")
            return None
    
    def complete_execution(
        self,
        execution_id: str,
        status: str,
        scan_id: Optional[str] = None,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Record the completion of a job execution.
        
        Args:
            execution_id: Execution ID from start_execution()
            status: Execution status (success, failed, cancelled)
            scan_id: Scan ID if scan was created
            error_message: Error message if failed
            error_details: Additional error details
            
        Returns:
            True if recorded, False otherwise
        """
        query = """
            UPDATE job_executions
            SET 
                status = %s,
                completed_at = NOW(),
                duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at)),
                scan_id = %s,
                error_message = %s,
                error_details = %s
            WHERE execution_id = %s
        """
        
        try:
            import json
            self.db.execute_query(
                query,
                (
                    status,
                    scan_id,
                    error_message,
                    json.dumps(error_details) if error_details else None,
                    execution_id
                ),
                fetch=False
            )
            logger.debug(f"Completed execution {execution_id} with status {status}")
            return True
        except Exception as e:
            logger.error(f"Failed to record job completion for {execution_id}: {e}")
            return False
    
    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a job execution by ID.
        
        Args:
            execution_id: Execution ID
            
        Returns:
            Execution dict if found, None otherwise
        """
        query = """
            SELECT 
                execution_id, schedule_id, job_id, domain, domain_config_id,
                status, started_at, completed_at, duration_seconds, scan_id,
                error_message, error_details, metadata, created_at
            FROM job_executions
            WHERE execution_id = %s
        """
        
        try:
            result = self.db.execute_query(query, (execution_id,), fetch=True)
            if result:
                return dict(result[0])
            return None
        except Exception as e:
            logger.error(f"Failed to get execution {execution_id}: {e}")
            return None
    
    def get_executions_by_schedule(
        self,
        schedule_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get job executions for a specific schedule.
        
        Args:
            schedule_id: Schedule ID
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of execution dicts
        """
        query = """
            SELECT 
                execution_id, schedule_id, job_id, domain, domain_config_id,
                status, started_at, completed_at, duration_seconds, scan_id,
                error_message, error_details, metadata, created_at
            FROM job_executions
            WHERE schedule_id = %s
            ORDER BY started_at DESC
            LIMIT %s OFFSET %s
        """
        
        try:
            result = self.db.execute_query(query, (schedule_id, limit, offset), fetch=True)
            return [dict(row) for row in result] if result else []
        except Exception as e:
            logger.error(f"Failed to get executions for schedule {schedule_id}: {e}")
            return []
    
    def get_executions_by_domain(
        self,
        domain: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get job executions for a specific domain.
        
        Args:
            domain: Domain name
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of execution dicts
        """
        query = """
            SELECT 
                execution_id, schedule_id, job_id, domain, domain_config_id,
                status, started_at, completed_at, duration_seconds, scan_id,
                error_message, error_details, metadata, created_at
            FROM job_executions
            WHERE domain = %s
            ORDER BY started_at DESC
            LIMIT %s OFFSET %s
        """
        
        try:
            result = self.db.execute_query(query, (domain, limit, offset), fetch=True)
            return [dict(row) for row in result] if result else []
        except Exception as e:
            logger.error(f"Failed to get executions for domain {domain}: {e}")
            return []
    
    def get_recent_executions(
        self,
        hours: int = 24,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent job executions.
        
        Args:
            hours: Number of hours to look back
            status: Filter by status (optional)
            
        Returns:
            List of execution dicts
        """
        query = """
            SELECT 
                execution_id, schedule_id, job_id, domain, domain_config_id,
                status, started_at, completed_at, duration_seconds, scan_id,
                error_message, error_details, metadata, created_at
            FROM job_executions
            WHERE started_at >= NOW() - INTERVAL '%s hours'
        """
        
        params = [hours]
        
        if status:
            query += " AND status = %s"
            params.append(status)
        
        query += " ORDER BY started_at DESC"
        
        try:
            result = self.db.execute_query(query, tuple(params), fetch=True)
            return [dict(row) for row in result] if result else []
        except Exception as e:
            logger.error(f"Failed to get recent executions: {e}")
            return []
    
    def get_execution_statistics(
        self,
        schedule_id: Optional[str] = None,
        domain: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get execution statistics.
        
        Args:
            schedule_id: Filter by schedule ID (optional)
            domain: Filter by domain (optional)
            days: Number of days to analyze
            
        Returns:
            Dict with statistics
        """
        where_clauses = ["started_at >= NOW() - INTERVAL '%s days'"]
        params = [days]
        
        if schedule_id:
            where_clauses.append("schedule_id = %s")
            params.append(schedule_id)
        
        if domain:
            where_clauses.append("domain = %s")
            params.append(domain)
        
        where_clause = " AND ".join(where_clauses)
        
        query = f"""
            SELECT 
                COUNT(*) as total_executions,
                COUNT(CASE WHEN status = 'success' THEN 1 END) as successful,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled,
                AVG(CASE WHEN duration_seconds IS NOT NULL THEN duration_seconds END) as avg_duration,
                MIN(CASE WHEN duration_seconds IS NOT NULL THEN duration_seconds END) as min_duration,
                MAX(CASE WHEN duration_seconds IS NOT NULL THEN duration_seconds END) as max_duration
            FROM job_executions
            WHERE {where_clause}
        """
        
        try:
            result = self.db.execute_query(query, tuple(params), fetch=True)
            if result:
                stats = dict(result[0])
                # Calculate success rate
                total = stats.get('total_executions', 0)
                successful = stats.get('successful', 0)
                stats['success_rate'] = (successful / total * 100) if total > 0 else 0
                return stats
            return {}
        except Exception as e:
            logger.error(f"Failed to get execution statistics: {e}")
            return {}
    
    def cleanup_old_executions(self, days: int = 90) -> int:
        """
        Clean up old job execution records.
        
        Args:
            days: Delete executions older than this many days
            
        Returns:
            Number of records deleted
        """
        query = """
            DELETE FROM job_executions
            WHERE started_at < NOW() - INTERVAL '%s days'
        """
        
        try:
            # Get count before deletion
            count_query = """
                SELECT COUNT(*) as count
                FROM job_executions
                WHERE started_at < NOW() - INTERVAL '%s days'
            """
            result = self.db.execute_query(count_query, (days,), fetch=True)
            count = result[0]['count'] if result else 0
            
            # Delete old records
            self.db.execute_query(query, (days,), fetch=False)
            
            logger.info(f"Cleaned up {count} job execution records older than {days} days")
            return count
        except Exception as e:
            logger.error(f"Failed to cleanup old executions: {e}")
            return 0


# Singleton instance
_job_history: Optional[JobHistory] = None


def get_job_history() -> JobHistory:
    """Get the global job history instance."""
    global _job_history
    if _job_history is None:
        raise RuntimeError(
            "Job history not initialized. Call init_job_history() first."
        )
    return _job_history


def init_job_history(db_connection) -> JobHistory:
    """Initialize the global job history instance."""
    global _job_history
    _job_history = JobHistory(db_connection)
    return _job_history
