"""
Batch database operations for improved performance.

This module provides utilities for batch inserts and updates,
significantly improving performance when dealing with large datasets.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class BatchOperations:
    """
    Provides batch database operations for improved performance.
    
    Uses executemany() and COPY operations for efficient bulk inserts.
    """
    
    def __init__(self, db_connection):
        """
        Initialize batch operations.
        
        Args:
            db_connection: DatabaseConnection instance
        """
        self.db = db_connection
    
    def batch_insert_cookies(
        self,
        cookies: List[Dict[str, Any]],
        scan_id: str,
        batch_size: int = 1000
    ) -> int:
        """
        Batch insert cookies for a scan with categorization metadata.
        
        Uses executemany() for efficient bulk inserts. Processes cookies
        in batches to avoid memory issues with very large datasets.
        
        Args:
            cookies: List of cookie dicts with categorization
            scan_id: Scan ID to associate cookies with
            batch_size: Number of cookies to insert per batch
            
        Returns:
            Number of cookies inserted
        """
        if not cookies:
            return 0
        
        insert_query = """
            INSERT INTO cookies (
                cookie_id, scan_id, name, domain, path, hashed_value,
                cookie_duration, size, http_only, secure, same_site,
                category, vendor, cookie_type, set_after_accept,
                iab_purposes, description, source, metadata
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        
        total_inserted = 0
        categorization_stats = {
            "DB": 0,
            "ML_High": 0,
            "ML_Low": 0,
            "IAB": 0,
            "IAB_ML_Blend": 0,
            "RulesJSON": 0,
            "Rules_ML_Agree": 0,
            "Fallback": 0
        }
        
        # Process in batches
        for i in range(0, len(cookies), batch_size):
            batch = cookies[i:i + batch_size]
            params_list = []
            
            for cookie in batch:
                import json
                
                # Build metadata with ML classification info
                metadata = cookie.get('metadata', {})
                if cookie.get('ml_confidence') is not None:
                    metadata['ml_confidence'] = cookie.get('ml_confidence')
                if cookie.get('ml_probabilities') is not None:
                    metadata['ml_probabilities'] = cookie.get('ml_probabilities')
                if cookie.get('classification_evidence') is not None:
                    metadata['classification_evidence'] = cookie.get('classification_evidence')
                if cookie.get('requires_review') is not None:
                    metadata['requires_review'] = cookie.get('requires_review')
                
                # Track categorization source stats
                source = cookie.get('source', 'Fallback')
                categorization_stats[source] = categorization_stats.get(source, 0) + 1
                
                params = (
                    str(uuid.uuid4()),  # cookie_id
                    scan_id,
                    cookie.get('name'),
                    cookie.get('domain'),
                    cookie.get('path', '/'),
                    cookie.get('hashed_value'),
                    cookie.get('cookie_duration'),
                    cookie.get('size'),
                    cookie.get('http_only', False),
                    cookie.get('secure', False),
                    cookie.get('same_site'),
                    cookie.get('category'),
                    cookie.get('vendor'),
                    cookie.get('cookie_type'),
                    cookie.get('set_after_accept', False),
                    json.dumps(cookie.get('iab_purposes', [])),
                    cookie.get('description'),
                    cookie.get('source'),
                    json.dumps(metadata)
                )
                params_list.append(params)
            
            try:
                self.db.execute_many(insert_query, params_list)
                total_inserted += len(batch)
                logger.debug(f"Inserted batch of {len(batch)} cookies")
            except Exception as e:
                logger.error(f"Failed to insert cookie batch: {e}")
                raise
        
        logger.info(f"Batch inserted {total_inserted} cookies for scan {scan_id}")
        logger.info(f"Categorization sources: {categorization_stats}")
        return total_inserted
    
    def batch_insert_scan_results(
        self,
        scan_results: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> int:
        """
        Batch insert scan results.
        
        Args:
            scan_results: List of scan result dicts
            batch_size: Number of results to insert per batch
            
        Returns:
            Number of scan results inserted
        """
        if not scan_results:
            return 0
        
        insert_query = """
            INSERT INTO scan_results (
                scan_id, domain_config_id, domain, scan_mode, timestamp_utc,
                status, duration_seconds, total_cookies, page_count,
                error, params
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        
        total_inserted = 0
        
        for i in range(0, len(scan_results), batch_size):
            batch = scan_results[i:i + batch_size]
            params_list = []
            
            for result in batch:
                import json
                params = (
                    result.get('scan_id', str(uuid.uuid4())),
                    result.get('domain_config_id'),
                    result.get('domain'),
                    result.get('scan_mode', 'deep'),
                    result.get('timestamp_utc', datetime.utcnow()),
                    result.get('status', 'success'),
                    result.get('duration_seconds'),
                    result.get('total_cookies', 0),
                    result.get('page_count', 0),
                    result.get('error'),
                    json.dumps(result.get('params', {}))
                )
                params_list.append(params)
            
            try:
                self.db.execute_many(insert_query, params_list)
                total_inserted += len(batch)
                logger.debug(f"Inserted batch of {len(batch)} scan results")
            except Exception as e:
                logger.error(f"Failed to insert scan results batch: {e}")
                raise
        
        logger.info(f"Batch inserted {total_inserted} scan results")
        return total_inserted
    
    def batch_update_schedules(
        self,
        updates: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> int:
        """
        Batch update schedules.
        
        Args:
            updates: List of dicts with 'schedule_id' and fields to update
            batch_size: Number of updates per batch
            
        Returns:
            Number of schedules updated
        """
        if not updates:
            return 0
        
        update_query = """
            UPDATE schedules
            SET 
                last_run = %s,
                next_run = %s,
                last_status = %s,
                updated_at = NOW()
            WHERE schedule_id = %s
        """
        
        total_updated = 0
        
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]
            params_list = []
            
            for update in batch:
                params = (
                    update.get('last_run'),
                    update.get('next_run'),
                    update.get('last_status'),
                    update['schedule_id']
                )
                params_list.append(params)
            
            try:
                self.db.execute_many(update_query, params_list)
                total_updated += len(batch)
                logger.debug(f"Updated batch of {len(batch)} schedules")
            except Exception as e:
                logger.error(f"Failed to update schedules batch: {e}")
                raise
        
        logger.info(f"Batch updated {total_updated} schedules")
        return total_updated
    
    def bulk_delete_old_records(
        self,
        table: str,
        timestamp_column: str,
        days: int,
        batch_size: int = 1000
    ) -> int:
        """
        Bulk delete old records from a table.
        
        Deletes records in batches to avoid long-running transactions.
        
        Args:
            table: Table name
            timestamp_column: Column to filter by date
            days: Delete records older than this many days
            batch_size: Number of records to delete per batch
            
        Returns:
            Total number of records deleted
        """
        total_deleted = 0
        
        while True:
            # Delete in batches using LIMIT
            delete_query = f"""
                DELETE FROM {table}
                WHERE {timestamp_column} < NOW() - INTERVAL '%s days'
                AND ctid IN (
                    SELECT ctid FROM {table}
                    WHERE {timestamp_column} < NOW() - INTERVAL '%s days'
                    LIMIT %s
                )
            """
            
            try:
                # Get count before deletion
                count_query = f"""
                    SELECT COUNT(*) as count
                    FROM {table}
                    WHERE {timestamp_column} < NOW() - INTERVAL '%s days'
                    LIMIT %s
                """
                result = self.db.execute_query(
                    count_query,
                    (days, batch_size),
                    fetch=True
                )
                batch_count = result[0]['count'] if result else 0
                
                if batch_count == 0:
                    break
                
                # Delete batch
                self.db.execute_query(
                    delete_query,
                    (days, days, batch_size),
                    fetch=False
                )
                
                total_deleted += batch_count
                logger.debug(f"Deleted batch of {batch_count} records from {table}")
                
                # If we deleted less than batch_size, we're done
                if batch_count < batch_size:
                    break
                    
            except Exception as e:
                logger.error(f"Failed to delete batch from {table}: {e}")
                raise
        
        logger.info(f"Bulk deleted {total_deleted} old records from {table}")
        return total_deleted
    
    def vacuum_analyze_table(self, table: str) -> bool:
        """
        Run VACUUM ANALYZE on a table to update statistics and reclaim space.
        
        Args:
            table: Table name
            
        Returns:
            True if successful
        """
        try:
            # Note: VACUUM cannot run inside a transaction block
            conn = self.db.get_connection()
            old_isolation_level = conn.isolation_level
            conn.set_isolation_level(0)  # AUTOCOMMIT mode
            
            try:
                with conn.cursor() as cur:
                    cur.execute(f"VACUUM ANALYZE {table}")
                logger.info(f"VACUUM ANALYZE completed for {table}")
                return True
            finally:
                conn.set_isolation_level(old_isolation_level)
                self.db.return_connection(conn)
                
        except Exception as e:
            logger.error(f"Failed to VACUUM ANALYZE {table}: {e}")
            return False
    
    def refresh_materialized_views(self, concurrent: bool = True) -> bool:
        """
        Refresh all analytics materialized views.
        
        Args:
            concurrent: Whether to use CONCURRENTLY (allows reads during refresh)
            
        Returns:
            True if successful
        """
        try:
            concurrent_str = "CONCURRENTLY" if concurrent else ""
            
            views = [
                'mv_domain_scan_summary',
                'mv_cookie_category_stats'
            ]
            
            for view in views:
                query = f"REFRESH MATERIALIZED VIEW {concurrent_str} {view}"
                self.db.execute_query(query, fetch=False)
                logger.info(f"Refreshed materialized view: {view}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to refresh materialized views: {e}")
            return False
    
    def get_table_statistics(self, table: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics about a table (size, row count, etc.).
        
        Args:
            table: Table name
            
        Returns:
            Dict with table statistics
        """
        query = """
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
                pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - 
                              pg_relation_size(schemaname||'.'||tablename)) AS indexes_size,
                n_live_tup AS row_count,
                n_dead_tup AS dead_rows,
                last_vacuum,
                last_autovacuum,
                last_analyze,
                last_autoanalyze
            FROM pg_stat_user_tables
            WHERE tablename = %s
        """
        
        try:
            result = self.db.execute_query(query, (table,), fetch=True)
            if result:
                return dict(result[0])
            return None
        except Exception as e:
            logger.error(f"Failed to get statistics for {table}: {e}")
            return None


# Singleton instance
_batch_operations: Optional[BatchOperations] = None


def get_batch_operations() -> BatchOperations:
    """Get the global batch operations instance."""
    global _batch_operations
    if _batch_operations is None:
        raise RuntimeError(
            "Batch operations not initialized. Call init_batch_operations() first."
        )
    return _batch_operations


def init_batch_operations(db_connection) -> BatchOperations:
    """Initialize the global batch operations instance."""
    global _batch_operations
    _batch_operations = BatchOperations(db_connection)
    return _batch_operations
