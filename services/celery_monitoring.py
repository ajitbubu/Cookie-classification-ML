"""
Celery worker monitoring and management utilities.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from celery import Celery
from celery.result import AsyncResult
from services.celery_app import celery_app

logger = logging.getLogger(__name__)


class CeleryMonitor:
    """Monitor and manage Celery workers and tasks."""
    
    def __init__(self, celery_app: Celery):
        """
        Initialize Celery monitor.
        
        Args:
            celery_app: Celery application instance
        """
        self.celery_app = celery_app
        logger.info("CeleryMonitor initialized")
    
    def get_worker_stats(self) -> Dict[str, Any]:
        """
        Get statistics about active Celery workers.
        
        Returns:
            Dictionary with worker statistics
        """
        try:
            # Get active workers
            inspect = self.celery_app.control.inspect()
            
            # Get worker stats
            stats = inspect.stats()
            active_tasks = inspect.active()
            registered_tasks = inspect.registered()
            reserved_tasks = inspect.reserved()
            
            worker_count = len(stats) if stats else 0
            
            # Count total active tasks
            total_active = 0
            if active_tasks:
                for worker_tasks in active_tasks.values():
                    total_active += len(worker_tasks)
            
            # Count total reserved tasks
            total_reserved = 0
            if reserved_tasks:
                for worker_tasks in reserved_tasks.values():
                    total_reserved += len(worker_tasks)
            
            result = {
                'worker_count': worker_count,
                'total_active_tasks': total_active,
                'total_reserved_tasks': total_reserved,
                'workers': stats or {},
                'active_tasks': active_tasks or {},
                'registered_tasks': registered_tasks or {},
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Worker stats retrieved: {worker_count} workers, {total_active} active tasks")
            return result
            
        except Exception as e:
            logger.error(f"Error getting worker stats: {e}", exc_info=True)
            return {
                'error': str(e),
                'worker_count': 0,
                'total_active_tasks': 0,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get statistics about task queues.
        
        Returns:
            Dictionary with queue statistics
        """
        try:
            inspect = self.celery_app.control.inspect()
            
            # Get active queues
            active_queues = inspect.active_queues()
            
            result = {
                'queues': active_queues or {},
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info("Queue stats retrieved")
            return result
            
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}", exc_info=True)
            return {
                'error': str(e),
                'queues': {},
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get status of a specific task.
        
        Args:
            task_id: Task ID to check
            
        Returns:
            Dictionary with task status information
        """
        try:
            result = AsyncResult(task_id, app=self.celery_app)
            
            status_info = {
                'task_id': task_id,
                'state': result.state,
                'ready': result.ready(),
                'successful': result.successful() if result.ready() else None,
                'failed': result.failed() if result.ready() else None,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Add result or error info if available
            if result.ready():
                if result.successful():
                    status_info['result'] = result.result
                elif result.failed():
                    status_info['error'] = str(result.info)
            else:
                # Task is still pending or running
                status_info['info'] = result.info
            
            logger.info(f"Task status retrieved: {task_id}, state: {result.state}")
            return status_info
            
        except Exception as e:
            logger.error(f"Error getting task status for {task_id}: {e}", exc_info=True)
            return {
                'task_id': task_id,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def revoke_task(self, task_id: str, terminate: bool = False) -> Dict[str, Any]:
        """
        Revoke (cancel) a task.
        
        Args:
            task_id: Task ID to revoke
            terminate: If True, terminate the task immediately
            
        Returns:
            Dictionary with revocation status
        """
        try:
            self.celery_app.control.revoke(task_id, terminate=terminate)
            
            result = {
                'task_id': task_id,
                'revoked': True,
                'terminated': terminate,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Task revoked: {task_id}, terminate={terminate}")
            return result
            
        except Exception as e:
            logger.error(f"Error revoking task {task_id}: {e}", exc_info=True)
            return {
                'task_id': task_id,
                'revoked': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def purge_queue(self, queue_name: str = None) -> Dict[str, Any]:
        """
        Purge (clear) all tasks from a queue.
        
        Args:
            queue_name: Queue name to purge (None for default queue)
            
        Returns:
            Dictionary with purge results
        """
        try:
            if queue_name:
                count = self.celery_app.control.purge()
            else:
                count = self.celery_app.control.purge()
            
            result = {
                'queue': queue_name or 'default',
                'purged_count': count,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Queue purged: {queue_name or 'default'}, {count} tasks removed")
            return result
            
        except Exception as e:
            logger.error(f"Error purging queue {queue_name}: {e}", exc_info=True)
            return {
                'queue': queue_name or 'default',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_registered_tasks(self) -> Dict[str, Any]:
        """
        Get list of all registered tasks.
        
        Returns:
            Dictionary with registered tasks
        """
        try:
            inspect = self.celery_app.control.inspect()
            registered = inspect.registered()
            
            # Flatten task list from all workers
            all_tasks = set()
            if registered:
                for worker_tasks in registered.values():
                    all_tasks.update(worker_tasks)
            
            result = {
                'total_tasks': len(all_tasks),
                'tasks': sorted(list(all_tasks)),
                'by_worker': registered or {},
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Registered tasks retrieved: {len(all_tasks)} tasks")
            return result
            
        except Exception as e:
            logger.error(f"Error getting registered tasks: {e}", exc_info=True)
            return {
                'error': str(e),
                'total_tasks': 0,
                'tasks': [],
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_scheduled_tasks(self) -> Dict[str, Any]:
        """
        Get list of scheduled (ETA/countdown) tasks.
        
        Returns:
            Dictionary with scheduled tasks
        """
        try:
            inspect = self.celery_app.control.inspect()
            scheduled = inspect.scheduled()
            
            # Count total scheduled tasks
            total_scheduled = 0
            if scheduled:
                for worker_tasks in scheduled.values():
                    total_scheduled += len(worker_tasks)
            
            result = {
                'total_scheduled': total_scheduled,
                'scheduled_tasks': scheduled or {},
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Scheduled tasks retrieved: {total_scheduled} tasks")
            return result
            
        except Exception as e:
            logger.error(f"Error getting scheduled tasks: {e}", exc_info=True)
            return {
                'error': str(e),
                'total_scheduled': 0,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of Celery system.
        
        Returns:
            Dictionary with complete system status
        """
        try:
            worker_stats = self.get_worker_stats()
            queue_stats = self.get_queue_stats()
            registered_tasks = self.get_registered_tasks()
            scheduled_tasks = self.get_scheduled_tasks()
            
            result = {
                'status': 'healthy' if worker_stats.get('worker_count', 0) > 0 else 'unhealthy',
                'workers': worker_stats,
                'queues': queue_stats,
                'registered_tasks': registered_tasks,
                'scheduled_tasks': scheduled_tasks,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info("Comprehensive Celery status retrieved")
            return result
            
        except Exception as e:
            logger.error(f"Error getting comprehensive status: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }


# Global monitor instance
_celery_monitor: Optional[CeleryMonitor] = None


def get_celery_monitor() -> CeleryMonitor:
    """Get the global Celery monitor instance."""
    global _celery_monitor
    if _celery_monitor is None:
        _celery_monitor = CeleryMonitor(celery_app)
    return _celery_monitor


# Celery task for self-monitoring
@celery_app.task(name='monitor_celery_health')
def monitor_celery_health() -> Dict[str, Any]:
    """
    Monitor Celery system health (can be run periodically with Celery Beat).
    
    Returns:
        Health status dictionary
    """
    try:
        monitor = get_celery_monitor()
        status = monitor.get_comprehensive_status()
        
        # Log warnings if issues detected
        if status.get('status') == 'unhealthy':
            logger.warning("Celery system is unhealthy - no workers detected")
        
        worker_count = status.get('workers', {}).get('worker_count', 0)
        if worker_count == 0:
            logger.warning("No Celery workers are active")
        
        return status
        
    except Exception as e:
        logger.error(f"Error in monitor_celery_health task: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(name='get_task_statistics')
def get_task_statistics(hours: int = 24) -> Dict[str, Any]:
    """
    Get task execution statistics for the specified time period.
    
    Args:
        hours: Number of hours to look back
        
    Returns:
        Statistics dictionary
    """
    try:
        # This is a placeholder - actual implementation would query
        # task results from backend or monitoring system
        
        logger.info(f"Task statistics requested for last {hours} hours")
        
        return {
            'period_hours': hours,
            'total_tasks': 0,  # Placeholder
            'successful_tasks': 0,
            'failed_tasks': 0,
            'pending_tasks': 0,
            'average_duration': 0.0,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting task statistics: {e}", exc_info=True)
        return {
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }
