"""
Query optimizer utilities and optimized query patterns.

This module provides pre-optimized queries for common operations,
using best practices for PostgreSQL performance.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class QueryOptimizer:
    """
    Provides optimized query patterns for common database operations.
    
    Uses techniques like:
    - Proper index usage
    - Query result limiting
    - Efficient JOINs
    - Materialized view usage
    - Query result caching hints
    """
    
    def __init__(self, db_connection):
        """
        Initialize query optimizer.
        
        Args:
            db_connection: DatabaseConnection instance
        """
        self.db = db_connection
    
    def get_recent_scans_optimized(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
        domain: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent scans with optimized query.
        
        Uses covering index and efficient filtering.
        
        Args:
            limit: Maximum results
            offset: Pagination offset
            status: Filter by status (optional)
            domain: Filter by domain (optional)
            
        Returns:
            List of scan result dicts
        """
        # Build query with optional filters
        where_clauses = []
        params = []
        
        if status:
            where_clauses.append("status = %s")
            params.append(status)
        
        if domain:
            where_clauses.append("domain = %s")
            params.append(domain)
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "TRUE"
        
        # Optimized query using appropriate indexes
        query = f"""
            SELECT 
                scan_id, domain_config_id, domain, scan_mode,
                timestamp_utc, status, duration_seconds, total_cookies,
                page_count, created_at
            FROM scan_results
            WHERE {where_clause}
            ORDER BY timestamp_utc DESC
            LIMIT %s OFFSET %s
        """
        
        params.extend([limit, offset])
        
        try:
            result = self.db.execute_query(query, tuple(params), fetch=True)
            return [dict(row) for row in result] if result else []
        except Exception as e:
            logger.error(f"Failed to get recent scans: {e}")
            return []
    
    def get_scan_with_cookies_optimized(
        self,
        scan_id: str,
        include_cookies: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get scan result with cookies using optimized query.
        
        Uses single query with LEFT JOIN for efficiency.
        
        Args:
            scan_id: Scan ID
            include_cookies: Whether to include cookie details
            
        Returns:
            Scan dict with cookies array
        """
        if not include_cookies:
            # Simple query without cookies
            query = """
                SELECT 
                    scan_id, domain_config_id, domain, scan_mode,
                    timestamp_utc, status, duration_seconds, total_cookies,
                    page_count, error, params, created_at
                FROM scan_results
                WHERE scan_id = %s
            """
            
            try:
                result = self.db.execute_query(query, (scan_id,), fetch=True)
                if result:
                    scan = dict(result[0])
                    scan['cookies'] = []
                    return scan
                return None
            except Exception as e:
                logger.error(f"Failed to get scan {scan_id}: {e}")
                return None
        
        # Optimized query with cookies using JSON aggregation
        query = """
            SELECT 
                sr.scan_id, sr.domain_config_id, sr.domain, sr.scan_mode,
                sr.timestamp_utc, sr.status, sr.duration_seconds, sr.total_cookies,
                sr.page_count, sr.error, sr.params, sr.created_at,
                COALESCE(
                    json_agg(
                        json_build_object(
                            'cookie_id', c.cookie_id,
                            'name', c.name,
                            'domain', c.domain,
                            'path', c.path,
                            'category', c.category,
                            'cookie_type', c.cookie_type,
                            'vendor', c.vendor,
                            'http_only', c.http_only,
                            'secure', c.secure,
                            'same_site', c.same_site,
                            'size', c.size,
                            'cookie_duration', c.cookie_duration
                        ) ORDER BY c.name
                    ) FILTER (WHERE c.cookie_id IS NOT NULL),
                    '[]'::json
                ) as cookies
            FROM scan_results sr
            LEFT JOIN cookies c ON sr.scan_id = c.scan_id
            WHERE sr.scan_id = %s
            GROUP BY sr.scan_id
        """
        
        try:
            result = self.db.execute_query(query, (scan_id,), fetch=True)
            if result:
                return dict(result[0])
            return None
        except Exception as e:
            logger.error(f"Failed to get scan with cookies {scan_id}: {e}")
            return None
    
    def get_domain_scan_history_optimized(
        self,
        domain: str,
        days: int = 30,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get scan history for a domain using optimized query.
        
        Uses composite index on (domain, timestamp_utc).
        
        Args:
            domain: Domain name
            days: Number of days to look back
            limit: Maximum results
            
        Returns:
            List of scan result dicts
        """
        query = """
            SELECT 
                scan_id, domain, scan_mode, timestamp_utc,
                status, duration_seconds, total_cookies, page_count
            FROM scan_results
            WHERE domain = %s
                AND timestamp_utc >= NOW() - INTERVAL '%s days'
            ORDER BY timestamp_utc DESC
            LIMIT %s
        """
        
        try:
            result = self.db.execute_query(query, (domain, days, limit), fetch=True)
            return [dict(row) for row in result] if result else []
        except Exception as e:
            logger.error(f"Failed to get scan history for {domain}: {e}")
            return []
    
    def get_cookie_statistics_optimized(
        self,
        scan_id: str
    ) -> Dict[str, Any]:
        """
        Get cookie statistics for a scan using optimized aggregation.
        
        Single query with multiple aggregations for efficiency.
        
        Args:
            scan_id: Scan ID
            
        Returns:
            Dict with cookie statistics
        """
        query = """
            SELECT 
                COUNT(*) as total_cookies,
                COUNT(DISTINCT name) as unique_cookies,
                COUNT(CASE WHEN cookie_type = 'First Party' THEN 1 END) as first_party,
                COUNT(CASE WHEN cookie_type = 'Third Party' THEN 1 END) as third_party,
                COUNT(CASE WHEN category = 'Necessary' THEN 1 END) as necessary,
                COUNT(CASE WHEN category = 'Functional' THEN 1 END) as functional,
                COUNT(CASE WHEN category = 'Analytics' THEN 1 END) as analytics,
                COUNT(CASE WHEN category = 'Advertising' THEN 1 END) as advertising,
                COUNT(CASE WHEN http_only = TRUE THEN 1 END) as http_only_count,
                COUNT(CASE WHEN secure = TRUE THEN 1 END) as secure_count,
                COUNT(DISTINCT vendor) FILTER (WHERE vendor IS NOT NULL) as unique_vendors,
                AVG(size) FILTER (WHERE size IS NOT NULL) as avg_size
            FROM cookies
            WHERE scan_id = %s
        """
        
        try:
            result = self.db.execute_query(query, (scan_id,), fetch=True)
            if result:
                return dict(result[0])
            return {}
        except Exception as e:
            logger.error(f"Failed to get cookie statistics for {scan_id}: {e}")
            return {}
    
    def get_domain_summary_from_mv(
        self,
        domain: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get domain summary from materialized view (fast).
        
        Uses pre-computed statistics for instant results.
        
        Args:
            domain: Filter by domain (optional)
            limit: Maximum results
            
        Returns:
            List of domain summary dicts
        """
        if domain:
            query = """
                SELECT *
                FROM mv_domain_scan_summary
                WHERE domain = %s
            """
            params = (domain,)
        else:
            query = """
                SELECT *
                FROM mv_domain_scan_summary
                ORDER BY last_scan_time DESC
                LIMIT %s
            """
            params = (limit,)
        
        try:
            result = self.db.execute_query(query, params, fetch=True)
            return [dict(row) for row in result] if result else []
        except Exception as e:
            logger.error(f"Failed to get domain summary from MV: {e}")
            return []
    
    def get_active_scans_optimized(self) -> List[Dict[str, Any]]:
        """
        Get currently active scans using partial index.
        
        Uses partial index on active scans for fast lookup.
        
        Returns:
            List of active scan dicts
        """
        query = """
            SELECT 
                scan_id, domain, scan_mode, timestamp_utc, status
            FROM scan_results
            WHERE status IN ('pending', 'running')
            ORDER BY timestamp_utc DESC
        """
        
        try:
            result = self.db.execute_query(query, fetch=True)
            return [dict(row) for row in result] if result else []
        except Exception as e:
            logger.error(f"Failed to get active scans: {e}")
            return []
    
    def get_failed_jobs_optimized(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent failed jobs using partial index.
        
        Uses partial index on failed jobs for fast lookup.
        
        Args:
            hours: Number of hours to look back
            limit: Maximum results
            
        Returns:
            List of failed job execution dicts
        """
        query = """
            SELECT 
                execution_id, schedule_id, job_id, domain,
                started_at, completed_at, duration_seconds,
                error_message
            FROM job_executions
            WHERE status = 'failed'
                AND started_at >= NOW() - INTERVAL '%s hours'
            ORDER BY started_at DESC
            LIMIT %s
        """
        
        try:
            result = self.db.execute_query(query, (hours, limit), fetch=True)
            return [dict(row) for row in result] if result else []
        except Exception as e:
            logger.error(f"Failed to get failed jobs: {e}")
            return []
    
    def get_pending_notifications_optimized(
        self,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get pending notifications using partial index.
        
        Uses partial index on pending notifications for fast lookup.
        
        Args:
            limit: Maximum results
            
        Returns:
            List of pending notification dicts
        """
        query = """
            SELECT 
                notification_id, user_id, event, channel,
                created_at, retry_count, data
            FROM notifications
            WHERE status = 'pending'
            ORDER BY created_at
            LIMIT %s
        """
        
        try:
            result = self.db.execute_query(query, (limit,), fetch=True)
            return [dict(row) for row in result] if result else []
        except Exception as e:
            logger.error(f"Failed to get pending notifications: {e}")
            return []
    
    def get_upcoming_schedules_optimized(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming scheduled jobs using optimized index.
        
        Uses composite index on (next_run, domain) with enabled filter.
        
        Args:
            hours: Number of hours to look ahead
            limit: Maximum results
            
        Returns:
            List of schedule dicts
        """
        query = """
            SELECT 
                schedule_id, domain_config_id, domain, frequency,
                time_config, next_run, last_run, last_status
            FROM schedules
            WHERE enabled = TRUE
                AND next_run IS NOT NULL
                AND next_run <= NOW() + INTERVAL '%s hours'
            ORDER BY next_run
            LIMIT %s
        """
        
        try:
            result = self.db.execute_query(query, (hours, limit), fetch=True)
            return [dict(row) for row in result] if result else []
        except Exception as e:
            logger.error(f"Failed to get upcoming schedules: {e}")
            return []
    
    def explain_query(self, query: str, params: Tuple = None) -> Optional[str]:
        """
        Get EXPLAIN ANALYZE output for a query.
        
        Useful for debugging query performance.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            EXPLAIN output as string
        """
        explain_query = f"EXPLAIN ANALYZE {query}"
        
        try:
            result = self.db.execute_query(explain_query, params, fetch=True)
            if result:
                return "\n".join([row['QUERY PLAN'] for row in result])
            return None
        except Exception as e:
            logger.error(f"Failed to explain query: {e}")
            return None


# Singleton instance
_query_optimizer: Optional[QueryOptimizer] = None


def get_query_optimizer() -> QueryOptimizer:
    """Get the global query optimizer instance."""
    global _query_optimizer
    if _query_optimizer is None:
        raise RuntimeError(
            "Query optimizer not initialized. Call init_query_optimizer() first."
        )
    return _query_optimizer


def init_query_optimizer(db_connection) -> QueryOptimizer:
    """Initialize the global query optimizer instance."""
    global _query_optimizer
    _query_optimizer = QueryOptimizer(db_connection)
    return _query_optimizer
