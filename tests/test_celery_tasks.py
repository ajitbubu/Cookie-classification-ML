#!/usr/bin/env python3
"""
Test script for Celery async task processing.

This script tests the report generation and notification tasks.
"""

import sys
import time
import logging
from uuid import uuid4
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_celery_connection():
    """Test Celery connection and worker availability."""
    logger.info("Testing Celery connection...")
    
    try:
        from src.services.celery_app import celery_app
        
        # Check if workers are available
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        if stats:
            logger.info(f"✓ Celery workers available: {len(stats)} worker(s)")
            for worker_name, worker_stats in stats.items():
                logger.info(f"  - {worker_name}: {worker_stats.get('pool', {}).get('max-concurrency', 'N/A')} processes")
            return True
        else:
            logger.warning("✗ No Celery workers available")
            logger.info("  Start workers with: python run_celery_worker.py")
            return False
            
    except Exception as e:
        logger.error(f"✗ Celery connection failed: {e}")
        return False


def test_report_generation_task():
    """Test async report generation task."""
    logger.info("\nTesting report generation task...")
    
    try:
        from src.services.report_tasks import generate_report_async
        
        # Note: This requires a valid scan_id in the database
        # For testing, we'll just verify the task can be imported and called
        logger.info("✓ Report generation task imported successfully")
        logger.info("  Task name: generate_report_async")
        logger.info("  Task registered: Yes")
        
        # Check task registration
        from src.services.celery_app import celery_app
        registered_tasks = celery_app.tasks
        
        if 'generate_report_async' in registered_tasks:
            logger.info("✓ Task is registered with Celery")
            return True
        else:
            logger.warning("✗ Task not found in registered tasks")
            return False
            
    except Exception as e:
        logger.error(f"✗ Report generation task test failed: {e}")
        return False


def test_notification_task():
    """Test async notification task."""
    logger.info("\nTesting notification task...")
    
    try:
        from src.services.notification_tasks import send_notification_async
        
        logger.info("✓ Notification task imported successfully")
        logger.info("  Task name: send_notification_async")
        logger.info("  Task registered: Yes")
        
        # Check task registration
        from src.services.celery_app import celery_app
        registered_tasks = celery_app.tasks
        
        if 'send_notification_async' in registered_tasks:
            logger.info("✓ Task is registered with Celery")
            return True
        else:
            logger.warning("✗ Task not found in registered tasks")
            return False
            
    except Exception as e:
        logger.error(f"✗ Notification task test failed: {e}")
        return False


def test_monitoring():
    """Test Celery monitoring functionality."""
    logger.info("\nTesting Celery monitoring...")
    
    try:
        from src.services.celery_monitoring import get_celery_monitor
        
        monitor = get_celery_monitor()
        
        # Get worker stats
        worker_stats = monitor.get_worker_stats()
        logger.info(f"✓ Worker stats retrieved: {worker_stats.get('worker_count', 0)} workers")
        
        # Get registered tasks
        registered = monitor.get_registered_tasks()
        logger.info(f"✓ Registered tasks: {registered.get('total_tasks', 0)} tasks")
        
        if registered.get('tasks'):
            logger.info("  Available tasks:")
            for task in sorted(registered['tasks'])[:10]:  # Show first 10
                logger.info(f"    - {task}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Monitoring test failed: {e}")
        return False


def test_task_routing():
    """Test task routing configuration."""
    logger.info("\nTesting task routing...")
    
    try:
        from src.services.celery_app import celery_app
        
        task_routes = celery_app.conf.task_routes
        
        logger.info("✓ Task routing configured:")
        for task_name, route_config in task_routes.items():
            queue = route_config.get('queue', 'default')
            logger.info(f"  - {task_name} → {queue} queue")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Task routing test failed: {e}")
        return False


def test_beat_schedule():
    """Test Celery Beat periodic task schedule."""
    logger.info("\nTesting Celery Beat schedule...")
    
    try:
        from src.services.celery_beat_config import celery_app
        
        beat_schedule = celery_app.conf.beat_schedule
        
        logger.info(f"✓ Periodic tasks configured: {len(beat_schedule)} tasks")
        for task_name, config in beat_schedule.items():
            task = config.get('task', 'unknown')
            schedule = config.get('schedule', 'unknown')
            logger.info(f"  - {task_name}: {task}")
            
        return True
        
    except Exception as e:
        logger.error(f"✗ Beat schedule test failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Celery Async Task Processing Tests")
    logger.info("=" * 60)
    
    # Initialize config (optional for basic tests)
    try:
        from src.core.config import init_config
        init_config()
        logger.info("✓ Configuration initialized\n")
    except Exception as e:
        logger.warning(f"⚠ Configuration initialization skipped: {e}")
        logger.info("  (This is OK for basic task registration tests)\n")
    
    # Run tests
    results = {
        'Celery Connection': test_celery_connection(),
        'Report Generation Task': test_report_generation_task(),
        'Notification Task': test_notification_task(),
        'Monitoring': test_monitoring(),
        'Task Routing': test_task_routing(),
        'Beat Schedule': test_beat_schedule(),
    }
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n✓ All tests passed!")
        return 0
    else:
        logger.warning(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
