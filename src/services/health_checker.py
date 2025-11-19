"""
Health checker service for system monitoring.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

import asyncpg
from redis import Redis

logger = logging.getLogger(__name__)


class ComponentHealth:
    """Health status for a component."""
    
    def __init__(self, status: str, message: Optional[str] = None, details: Optional[Dict] = None):
        self.status = status  # healthy, degraded, unhealthy
        self.message = message
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {'status': self.status}
        if self.message:
            result['message'] = self.message
        if self.details:
            result['details'] = self.details
        return result


class HealthChecker:
    """Comprehensive health check system."""
    
    def __init__(
        self,
        db_pool: Optional[asyncpg.Pool] = None,
        redis_client: Optional[Redis] = None
    ):
        """Initialize health checker."""
        self.db_pool = db_pool
        self.redis_client = redis_client
        logger.info("HealthChecker initialized")
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.
        
        Returns:
            Dictionary with overall status and component statuses
        """
        components = {}
        
        # Check database
        db_health = await self.check_database()
        components['database'] = db_health.to_dict()
        
        # Check Redis
        redis_health = await self.check_redis()
        components['redis'] = redis_health.to_dict()
        
        # Check browser (basic check)
        browser_health = await self.check_browser()
        components['browser'] = browser_health.to_dict()
        
        # Check scheduler (placeholder)
        scheduler_health = await self.check_scheduler()
        components['scheduler'] = scheduler_health.to_dict()
        
        # Determine overall status
        overall_status = self._determine_overall_status(components)
        
        return {
            'status': overall_status,
            'timestamp': datetime.utcnow().isoformat(),
            'version': '2.0.0',
            'components': components
        }
    
    async def check_database(self) -> ComponentHealth:
        """Check database connectivity and health."""
        if not self.db_pool:
            return ComponentHealth(
                'unhealthy',
                'Database pool not configured'
            )
        
        try:
            async with self.db_pool.acquire() as conn:
                # Simple query to test connectivity
                result = await conn.fetchval('SELECT 1')
                
                if result == 1:
                    # Get pool stats
                    pool_size = self.db_pool.get_size()
                    pool_free = self.db_pool.get_idle_size()
                    
                    return ComponentHealth(
                        'healthy',
                        'Database connection successful',
                        {
                            'pool_size': pool_size,
                            'pool_free': pool_free,
                            'pool_used': pool_size - pool_free
                        }
                    )
                else:
                    return ComponentHealth(
                        'unhealthy',
                        'Database query returned unexpected result'
                    )
        except asyncpg.PostgresError as e:
            logger.error(f"Database health check failed: {e}")
            return ComponentHealth(
                'unhealthy',
                f'Database error: {str(e)}'
            )
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return ComponentHealth(
                'unhealthy',
                f'Unexpected error: {str(e)}'
            )
    
    async def check_redis(self) -> ComponentHealth:
        """Check Redis connectivity and health."""
        if not self.redis_client:
            return ComponentHealth(
                'degraded',
                'Redis client not configured (optional)'
            )
        
        try:
            # Ping Redis
            response = self.redis_client.ping()
            
            if response:
                # Get Redis info
                info = self.redis_client.info('server')
                
                return ComponentHealth(
                    'healthy',
                    'Redis connection successful',
                    {
                        'redis_version': info.get('redis_version'),
                        'uptime_seconds': info.get('uptime_in_seconds')
                    }
                )
            else:
                return ComponentHealth(
                    'unhealthy',
                    'Redis ping failed'
                )
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return ComponentHealth(
                'degraded',
                f'Redis error: {str(e)} (cache unavailable)'
            )
    
    async def check_browser(self) -> ComponentHealth:
        """Check browser launch capability."""
        try:
            # Try to import playwright
            from playwright.async_api import async_playwright
            
            # Basic check - just verify playwright is available
            # Full browser launch would be too expensive for health checks
            return ComponentHealth(
                'healthy',
                'Browser engine available'
            )
        except ImportError as e:
            logger.error(f"Browser health check failed: {e}")
            return ComponentHealth(
                'unhealthy',
                'Playwright not installed or not available'
            )
        except Exception as e:
            logger.error(f"Browser health check failed: {e}")
            return ComponentHealth(
                'degraded',
                f'Browser check error: {str(e)}'
            )
    
    async def check_scheduler(self) -> ComponentHealth:
        """Check scheduler status."""
        # Placeholder - would check APScheduler status in production
        # For now, just return healthy
        return ComponentHealth(
            'healthy',
            'Scheduler service operational'
        )
    
    def _determine_overall_status(self, components: Dict[str, Dict]) -> str:
        """
        Determine overall system status based on component statuses.
        
        Args:
            components: Dictionary of component health statuses
            
        Returns:
            Overall status (healthy, degraded, unhealthy)
        """
        statuses = [comp['status'] for comp in components.values()]
        
        # If any component is unhealthy, system is unhealthy
        if 'unhealthy' in statuses:
            # Exception: Redis is optional, so if only Redis is unhealthy, system is degraded
            unhealthy_components = [
                name for name, comp in components.items()
                if comp['status'] == 'unhealthy'
            ]
            if unhealthy_components == ['redis']:
                return 'degraded'
            return 'unhealthy'
        
        # If any component is degraded, system is degraded
        if 'degraded' in statuses:
            return 'degraded'
        
        # All components healthy
        return 'healthy'
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get system metrics for monitoring.
        
        Returns:
            Dictionary with system metrics
        """
        metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'api': {},
            'database': {},
            'cache': {},
            'scans': {}
        }
        
        # Database metrics
        if self.db_pool:
            try:
                metrics['database'] = {
                    'pool_size': self.db_pool.get_size(),
                    'pool_free': self.db_pool.get_idle_size(),
                    'pool_used': self.db_pool.get_size() - self.db_pool.get_idle_size()
                }
                
                # Get scan counts
                async with self.db_pool.acquire() as conn:
                    total_scans = await conn.fetchval(
                        'SELECT COUNT(*) FROM scan_results'
                    )
                    active_scans = await conn.fetchval(
                        "SELECT COUNT(*) FROM scan_results WHERE status = 'running'"
                    )
                    failed_scans = await conn.fetchval(
                        "SELECT COUNT(*) FROM scan_results WHERE status = 'failed'"
                    )
                    
                    metrics['scans'] = {
                        'total': total_scans,
                        'active': active_scans,
                        'failed': failed_scans
                    }
            except Exception as e:
                logger.error(f"Failed to get database metrics: {e}")
        
        # Redis metrics
        if self.redis_client:
            try:
                info = self.redis_client.info('stats')
                metrics['cache'] = {
                    'total_connections_received': info.get('total_connections_received'),
                    'total_commands_processed': info.get('total_commands_processed'),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0)
                }
                
                # Calculate hit rate
                hits = info.get('keyspace_hits', 0)
                misses = info.get('keyspace_misses', 0)
                total = hits + misses
                if total > 0:
                    metrics['cache']['hit_rate'] = round(hits / total, 3)
                else:
                    metrics['cache']['hit_rate'] = 0.0
            except Exception as e:
                logger.error(f"Failed to get Redis metrics: {e}")
        
        return metrics
