"""
Analytics cache manager for caching computed metrics and reports.

Implements:
- Redis-based caching for analytics data
- Cache invalidation on new scans
- Cache warming for frequently accessed data
"""

import logging
import json
from typing import Any, Optional, Callable, List, Dict
from datetime import datetime, timedelta
from functools import wraps

from cache.redis_client import RedisClient, get_redis_client
from models.scan import ScanResult
from models.report import ComplianceMetrics, TrendData

logger = logging.getLogger(__name__)


class AnalyticsCacheManager:
    """Manage caching for analytics data."""
    
    # Cache TTLs (in seconds)
    CACHE_TTLS = {
        'metrics': 3600,        # 1 hour
        'trends': 3600,         # 1 hour
        'reports': 1800,        # 30 minutes
        'comparisons': 1800,    # 30 minutes
        'anomalies': 3600,      # 1 hour
    }
    
    def __init__(self, redis_client: Optional[RedisClient] = None):
        """
        Initialize analytics cache manager.
        
        Args:
            redis_client: Redis client instance (uses global if None)
        """
        self.redis = redis_client or get_redis_client()
        logger.info("AnalyticsCacheManager initialized")
    
    def _build_cache_key(self, prefix: str, *parts: str) -> str:
        """
        Build cache key for analytics data.
        
        Args:
            prefix: Key prefix (metrics, trends, reports, etc.)
            *parts: Additional key parts
            
        Returns:
            Formatted cache key
        """
        return self.redis._build_key('analytics_' + prefix, *parts)
    
    def cache_metrics(
        self,
        scan_id: str,
        metrics: ComplianceMetrics,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache compliance metrics for a scan.
        
        Args:
            scan_id: Scan ID
            metrics: Compliance metrics to cache
            ttl: Time to live in seconds (uses default if None)
            
        Returns:
            True if successful
        """
        key = self._build_cache_key('metrics', scan_id)
        ttl = ttl or self.CACHE_TTLS['metrics']
        
        try:
            success = self.redis.set_json(key, metrics.dict(), ttl=ttl)
            if success:
                logger.info(f"Cached metrics for scan {scan_id} (TTL: {ttl}s)")
            return success
        except Exception as e:
            logger.error(f"Error caching metrics for scan {scan_id}: {e}")
            return False
    
    def get_cached_metrics(self, scan_id: str) -> Optional[ComplianceMetrics]:
        """
        Get cached compliance metrics for a scan.
        
        Args:
            scan_id: Scan ID
            
        Returns:
            ComplianceMetrics object or None if not cached
        """
        key = self._build_cache_key('metrics', scan_id)
        
        try:
            data = self.redis.get_json(key)
            if data:
                logger.debug(f"Cache HIT: metrics for scan {scan_id}")
                return ComplianceMetrics(**data)
            logger.debug(f"Cache MISS: metrics for scan {scan_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving cached metrics for scan {scan_id}: {e}")
            return None
    
    def cache_trend_data(
        self,
        domain: str,
        metric: str,
        trend_data: TrendData,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache trend analysis data.
        
        Args:
            domain: Domain
            metric: Metric name
            trend_data: Trend data to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful
        """
        key = self._build_cache_key('trends', domain, metric)
        ttl = ttl or self.CACHE_TTLS['trends']
        
        try:
            success = self.redis.set_json(key, trend_data.dict(), ttl=ttl)
            if success:
                logger.info(f"Cached trend data for {domain}/{metric} (TTL: {ttl}s)")
            return success
        except Exception as e:
            logger.error(f"Error caching trend data for {domain}/{metric}: {e}")
            return False
    
    def get_cached_trend_data(
        self,
        domain: str,
        metric: str
    ) -> Optional[TrendData]:
        """
        Get cached trend analysis data.
        
        Args:
            domain: Domain
            metric: Metric name
            
        Returns:
            TrendData object or None if not cached
        """
        key = self._build_cache_key('trends', domain, metric)
        
        try:
            data = self.redis.get_json(key)
            if data:
                logger.debug(f"Cache HIT: trend data for {domain}/{metric}")
                return TrendData(**data)
            logger.debug(f"Cache MISS: trend data for {domain}/{metric}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving cached trend data for {domain}/{metric}: {e}")
            return None
    
    def cache_report(
        self,
        report_id: str,
        report_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache report data.
        
        Args:
            report_id: Report ID
            report_data: Report data to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful
        """
        key = self._build_cache_key('reports', report_id)
        ttl = ttl or self.CACHE_TTLS['reports']
        
        try:
            success = self.redis.set_json(key, report_data, ttl=ttl)
            if success:
                logger.info(f"Cached report {report_id} (TTL: {ttl}s)")
            return success
        except Exception as e:
            logger.error(f"Error caching report {report_id}: {e}")
            return False
    
    def get_cached_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached report data.
        
        Args:
            report_id: Report ID
            
        Returns:
            Report data or None if not cached
        """
        key = self._build_cache_key('reports', report_id)
        
        try:
            data = self.redis.get_json(key)
            if data:
                logger.debug(f"Cache HIT: report {report_id}")
                return data
            logger.debug(f"Cache MISS: report {report_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving cached report {report_id}: {e}")
            return None
    
    def invalidate_scan_cache(self, scan_id: str) -> int:
        """
        Invalidate all cached data for a scan.
        
        Args:
            scan_id: Scan ID
            
        Returns:
            Number of keys deleted
        """
        keys_to_delete = [
            self._build_cache_key('metrics', scan_id),
        ]
        
        try:
            deleted = self.redis.delete(*keys_to_delete)
            logger.info(f"Invalidated cache for scan {scan_id}: {deleted} keys deleted")
            return deleted
        except Exception as e:
            logger.error(f"Error invalidating cache for scan {scan_id}: {e}")
            return 0
    
    def invalidate_domain_cache(self, domain: str) -> int:
        """
        Invalidate all cached analytics data for a domain.
        
        This is called when a new scan is completed for a domain
        to ensure trend data and comparisons are recalculated.
        
        Args:
            domain: Domain name
            
        Returns:
            Number of keys deleted
        """
        # Note: Redis doesn't support pattern deletion efficiently
        # In production, consider using Redis SCAN with pattern matching
        # For now, we'll track known metrics and delete those keys
        
        metrics_to_invalidate = [
            'total_cookies',
            'compliance_score',
            'third_party_ratio',
            'first_party_ratio',
            'cookies_after_consent',
            'cookies_before_consent'
        ]
        
        keys_to_delete = []
        for metric in metrics_to_invalidate:
            keys_to_delete.append(self._build_cache_key('trends', domain, metric))
        
        try:
            deleted = self.redis.delete(*keys_to_delete)
            logger.info(f"Invalidated domain cache for {domain}: {deleted} keys deleted")
            return deleted
        except Exception as e:
            logger.error(f"Error invalidating domain cache for {domain}: {e}")
            return 0
    
    def warm_cache(
        self,
        scan_results: List[ScanResult],
        compute_metrics_fn: Callable[[ScanResult], ComplianceMetrics]
    ) -> int:
        """
        Warm cache with frequently accessed data.
        
        Pre-computes and caches metrics for a list of scan results.
        
        Args:
            scan_results: List of scan results to warm cache for
            compute_metrics_fn: Function to compute metrics
            
        Returns:
            Number of items cached
        """
        cached_count = 0
        
        for scan_result in scan_results:
            try:
                # Check if already cached
                if self.get_cached_metrics(str(scan_result.scan_id)):
                    continue
                
                # Compute and cache metrics
                metrics = compute_metrics_fn(scan_result)
                if self.cache_metrics(str(scan_result.scan_id), metrics):
                    cached_count += 1
            except Exception as e:
                logger.error(
                    f"Error warming cache for scan {scan_result.scan_id}: {e}"
                )
        
        logger.info(f"Cache warming complete: {cached_count} items cached")
        return cached_count
    
    def get_or_compute_metrics(
        self,
        scan_id: str,
        compute_fn: Callable[[], ComplianceMetrics]
    ) -> ComplianceMetrics:
        """
        Get metrics from cache or compute and cache them.
        
        Args:
            scan_id: Scan ID
            compute_fn: Function to compute metrics if not cached
            
        Returns:
            ComplianceMetrics object
        """
        # Try to get from cache
        cached = self.get_cached_metrics(scan_id)
        if cached:
            return cached
        
        # Compute metrics
        logger.debug(f"Computing metrics for scan {scan_id}")
        metrics = compute_fn()
        
        # Cache for future use
        self.cache_metrics(scan_id, metrics)
        
        return metrics
    
    def get_or_compute_trend(
        self,
        domain: str,
        metric: str,
        compute_fn: Callable[[], TrendData]
    ) -> TrendData:
        """
        Get trend data from cache or compute and cache it.
        
        Args:
            domain: Domain
            metric: Metric name
            compute_fn: Function to compute trend data if not cached
            
        Returns:
            TrendData object
        """
        # Try to get from cache
        cached = self.get_cached_trend_data(domain, metric)
        if cached:
            return cached
        
        # Compute trend data
        logger.debug(f"Computing trend data for {domain}/{metric}")
        trend_data = compute_fn()
        
        # Cache for future use
        self.cache_trend_data(domain, metric, trend_data)
        
        return trend_data
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            # Note: This is a simplified version
            # In production, you'd track hits/misses more comprehensively
            stats = {
                'redis_available': self.redis.ping(),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Cache stats: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'error': str(e)}
    
    def clear_all_analytics_cache(self) -> bool:
        """
        Clear all analytics cache data.
        
        WARNING: Use with caution! This clears all cached analytics data.
        
        Returns:
            True if successful
        """
        try:
            # In production, use SCAN to find and delete keys with pattern
            # For now, log a warning
            logger.warning("clear_all_analytics_cache called - implement pattern-based deletion")
            return True
        except Exception as e:
            logger.error(f"Error clearing analytics cache: {e}")
            return False


def cached_metrics(ttl: Optional[int] = None):
    """
    Decorator to cache metrics computation.
    
    Args:
        ttl: Time to live in seconds
        
    Usage:
        @cached_metrics(ttl=3600)
        def calculate_metrics(scan_result: ScanResult) -> ComplianceMetrics:
            # ... computation logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, scan_result: ScanResult, *args, **kwargs) -> ComplianceMetrics:
            # Get cache manager (assumes it's available)
            try:
                cache_manager = AnalyticsCacheManager()
                scan_id = str(scan_result.scan_id)
                
                # Try to get from cache
                cached = cache_manager.get_cached_metrics(scan_id)
                if cached:
                    return cached
                
                # Compute metrics
                metrics = func(self, scan_result, *args, **kwargs)
                
                # Cache result
                cache_manager.cache_metrics(scan_id, metrics, ttl=ttl)
                
                return metrics
            except Exception as e:
                logger.warning(f"Cache decorator error: {e}, computing without cache")
                return func(self, scan_result, *args, **kwargs)
        
        return wrapper
    return decorator


def cached_trend(ttl: Optional[int] = None):
    """
    Decorator to cache trend analysis.
    
    Args:
        ttl: Time to live in seconds
        
    Usage:
        @cached_trend(ttl=3600)
        def analyze_trends(domain: str, ...) -> TrendData:
            # ... computation logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, domain: str, *args, **kwargs) -> TrendData:
            # Extract metric name from kwargs or use default
            metric = kwargs.get('metric', 'total_cookies')
            
            try:
                cache_manager = AnalyticsCacheManager()
                
                # Try to get from cache
                cached = cache_manager.get_cached_trend_data(domain, metric)
                if cached:
                    return cached
                
                # Compute trend data
                trend_data = func(self, domain, *args, **kwargs)
                
                # Cache result
                cache_manager.cache_trend_data(domain, metric, trend_data, ttl=ttl)
                
                return trend_data
            except Exception as e:
                logger.warning(f"Cache decorator error: {e}, computing without cache")
                return func(self, domain, *args, **kwargs)
        
        return wrapper
    return decorator
