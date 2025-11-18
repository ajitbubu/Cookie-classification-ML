"""
Enhanced scheduler service with distributed locking, database persistence,
dynamic updates, and job history tracking.

This module replaces the basic schedule_manager.py with a more robust
scheduler that supports multiple instances, database-backed schedules,
and comprehensive audit trails.
"""

import os
import time
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from apscheduler.executors.pool import ThreadPoolExecutor

from config import (
    API_URL,
    REQUEST_TIMEOUT,
    MAX_WORKERS,
    JOB_REPLACE_EXISTING_INSTANCE,
    JOB_MAX_INSTANCES,
    JOB_COALESCE,
    JOB_MISFIRE_GRACE_TIME,
    DEFAULT_BUTTON_SELECTOR
)
from cookie_scanner import scan_domain
from cache.redis_client import init_redis_client, get_redis_client
from database.connection import init_db_connection, get_db_connection
from services.distributed_lock import init_distributed_lock, get_distributed_lock
from services.schedule_repository import init_schedule_repository, get_schedule_repository
from services.schedule_watcher import init_schedule_watcher, get_schedule_watcher
from services.job_history import init_job_history, get_job_history

logger = logging.getLogger(__name__)


class EnhancedScheduler:
    """
    Enhanced scheduler with distributed locking, database persistence,
    and dynamic updates.
    """
    
    def __init__(
        self,
        max_workers: int = MAX_WORKERS,
        enable_api_sync: bool = True,
        api_sync_interval: int = 300,
        schedule_check_interval: int = 60
    ):
        """
        Initialize enhanced scheduler.
        
        Args:
            max_workers: Maximum concurrent scan workers
            enable_api_sync: Whether to sync schedules from API
            api_sync_interval: How often to sync from API (seconds)
            schedule_check_interval: How often to check for schedule changes (seconds)
        """
        self.max_workers = max_workers
        self.enable_api_sync = enable_api_sync
        self.api_sync_interval = api_sync_interval
        self.schedule_check_interval = schedule_check_interval
        
        # Initialize components
        self._init_components()
        
        # Setup APScheduler
        executors = {"default": ThreadPoolExecutor(max_workers=max_workers)}
        self.scheduler = BackgroundScheduler(executors=executors)
        self.scheduler.add_listener(self._job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        
        # Track active executions
        self.active_executions: Dict[str, str] = {}  # job_id -> execution_id
        
        logger.info("EnhancedScheduler initialized")
    
    def _init_components(self):
        """Initialize Redis, database, and service components."""
        # Initialize Redis
        redis_host = os.environ.get('REDIS_HOST', 'localhost')
        redis_port = int(os.environ.get('REDIS_PORT', 6379))
        redis_db = int(os.environ.get('REDIS_DB', 0))
        redis_password = os.environ.get('REDIS_PASSWORD')
        
        init_redis_client(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password
        )
        self.redis_client = get_redis_client()
        logger.info("Redis client initialized")
        
        # Initialize database
        init_db_connection()
        self.db = get_db_connection()
        logger.info("Database connection initialized")
        
        # Initialize distributed lock
        init_distributed_lock(self.redis_client)
        self.lock_manager = get_distributed_lock()
        logger.info("Distributed lock manager initialized")
        
        # Initialize schedule repository
        init_schedule_repository(self.db)
        self.schedule_repo = get_schedule_repository()
        logger.info("Schedule repository initialized")
        
        # Initialize job history
        init_job_history(self.db)
        self.job_history = get_job_history()
        logger.info("Job history initialized")
        
        # Initialize schedule watcher
        init_schedule_watcher(self.schedule_repo, self.schedule_check_interval)
        self.schedule_watcher = get_schedule_watcher()
        logger.info("Schedule watcher initialized")
    
    def _job_listener(self, event: Any) -> None:
        """
        Listen to job events and log results.
        
        Args:
            event: APScheduler job event
        """
        job_id = event.job_id
        execution_id = self.active_executions.get(job_id)
        
        if event.exception:
            logger.error(f"Job {job_id} failed: {event.exception}")
            if execution_id:
                self.job_history.complete_execution(
                    execution_id,
                    status='failed',
                    error_message=str(event.exception)
                )
        else:
            logger.info(f"Job {job_id} executed successfully")
            if execution_id:
                # Extract scan_id from return value if available
                scan_id = getattr(event.retval, 'get', lambda x: None)('scan_id')
                self.job_history.complete_execution(
                    execution_id,
                    status='success',
                    scan_id=scan_id
                )
        
        # Clean up active execution tracking
        if job_id in self.active_executions:
            del self.active_executions[job_id]
    
    def _create_scan_wrapper(self, schedule: Dict) -> callable:
        """
        Create a wrapper function for scan_domain that includes distributed locking
        and job history tracking.
        
        Args:
            schedule: Schedule dict from database
            
        Returns:
            Wrapper function
        """
        def scan_with_lock():
            schedule_id = schedule['schedule_id']
            domain = schedule['domain']
            domain_config_id = schedule['domain_config_id']
            
            # Try to acquire distributed lock
            lock_token = self.lock_manager.acquire(
                resource_id=schedule_id,
                timeout=300,  # 5 minutes
                blocking=False  # Don't block, skip if locked
            )
            
            if not lock_token:
                logger.info(
                    f"Skipping job for {domain} - already running on another instance"
                )
                return None
            
            try:
                # Start job execution tracking
                execution_id = self.job_history.start_execution(
                    schedule_id=schedule_id,
                    job_id=domain,  # Using domain as job_id
                    domain=domain,
                    domain_config_id=domain_config_id
                )
                
                # Track active execution
                if execution_id:
                    self.active_executions[domain] = execution_id
                
                # Build scan parameters
                scan_params = {
                    "domain_config_id": domain_config_id,
                    "domain": domain,
                    "domainUrl": domain,
                    "description": schedule.get('description', ''),
                    "maxPages": schedule.get('max_pages'),
                    "scanDepth": schedule.get('scan_depth'),
                    "maxRetries": schedule.get('max_retries', 3),
                    "customPages": schedule.get('custom_pages', []),
                    "accept_selector": schedule.get('accept_selector', DEFAULT_BUTTON_SELECTOR),
                }
                
                # Execute scan
                logger.info(f"Starting scheduled scan for {domain}")
                result = scan_domain(scan_params)
                
                # Update schedule run status
                self.schedule_repo.update_schedule_run_status(
                    schedule_id=schedule_id,
                    last_run=datetime.utcnow(),
                    status='success'
                )
                
                return result
                
            except Exception as e:
                logger.error(f"Error executing scheduled scan for {domain}: {e}")
                
                # Update schedule run status
                self.schedule_repo.update_schedule_run_status(
                    schedule_id=schedule_id,
                    last_run=datetime.utcnow(),
                    status='failed'
                )
                
                raise
            finally:
                # Always release the lock
                self.lock_manager.release(schedule_id, lock_token)
        
        return scan_with_lock
    
    def _build_cron_trigger(self, schedule: Dict) -> Optional[CronTrigger]:
        """
        Build APScheduler CronTrigger from schedule configuration.
        
        Args:
            schedule: Schedule dict from database
            
        Returns:
            CronTrigger or None if invalid
        """
        DAY_NAME_MAP = {
            "sunday": "sun",
            "monday": "mon",
            "tuesday": "tue",
            "wednesday": "wed",
            "thursday": "thu",
            "friday": "fri",
            "saturday": "sat",
        }
        
        frequency = schedule.get('frequency', '').lower()
        time_config = schedule.get('time_config', {})
        
        try:
            if frequency == 'hourly':
                return CronTrigger(minute=time_config.get('minute', 0))
            
            elif frequency == 'daily':
                return CronTrigger(
                    hour=time_config.get('hour', 0),
                    minute=time_config.get('minute', 0)
                )
            
            elif frequency == 'weekly':
                raw_day = time_config.get('day', 0)
                
                # Normalize day_of_week
                if isinstance(raw_day, str):
                    day_str = raw_day.strip().lower()
                    day_of_week = DAY_NAME_MAP.get(day_str, day_str)
                else:
                    day_of_week = raw_day
                
                return CronTrigger(
                    day_of_week=day_of_week,
                    hour=time_config.get('hour', 0),
                    minute=time_config.get('minute', 0)
                )
            
            elif frequency == 'monthly':
                day = time_config.get('day', 1)
                if day >= 28:
                    day = "last"
                
                return CronTrigger(
                    day=day,
                    hour=time_config.get('hour', 0),
                    minute=time_config.get('minute', 0)
                )
            
            else:
                logger.warning(f"Unknown frequency '{frequency}'")
                return None
                
        except Exception as e:
            logger.error(f"Error building cron trigger: {e}")
            return None
    
    def add_schedule_job(self, schedule: Dict) -> bool:
        """
        Add a schedule as an APScheduler job.
        
        Args:
            schedule: Schedule dict from database
            
        Returns:
            True if added successfully
        """
        if not schedule.get('enabled', True):
            logger.debug(f"Skipping disabled schedule {schedule['schedule_id']}")
            return False
        
        schedule_id = schedule['schedule_id']
        domain = schedule['domain']
        
        # Build cron trigger
        trigger = self._build_cron_trigger(schedule)
        if not trigger:
            logger.warning(f"Failed to build trigger for schedule {schedule_id}")
            return False
        
        # Create scan wrapper with locking
        scan_func = self._create_scan_wrapper(schedule)
        
        try:
            # Add job to scheduler
            self.scheduler.add_job(
                scan_func,
                trigger,
                id=domain,  # Use domain as job ID
                replace_existing=JOB_REPLACE_EXISTING_INSTANCE,
                max_instances=JOB_MAX_INSTANCES,
                coalesce=JOB_COALESCE,
                misfire_grace_time=JOB_MISFIRE_GRACE_TIME,
            )
            logger.info(f"Added job for schedule {schedule_id} ({domain})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add job for schedule {schedule_id}: {e}")
            return False
    
    def remove_schedule_job(self, schedule_id: str, domain: str) -> bool:
        """
        Remove a schedule job from APScheduler.
        
        Args:
            schedule_id: Schedule ID
            domain: Domain (used as job ID)
            
        Returns:
            True if removed successfully
        """
        try:
            self.scheduler.remove_job(domain)
            logger.info(f"Removed job for schedule {schedule_id} ({domain})")
            return True
        except Exception as e:
            logger.debug(f"Job {domain} not found or already removed: {e}")
            return False
    
    def sync_schedules_from_database(self) -> Dict[str, int]:
        """
        Sync all schedules from database to APScheduler.
        
        Returns:
            Dict with counts of added schedules
        """
        logger.info("Syncing schedules from database...")
        
        # Get all enabled schedules
        schedules = self.schedule_repo.get_all_schedules(enabled_only=True)
        
        # Clear existing jobs
        for job in self.scheduler.get_jobs():
            self.scheduler.remove_job(job.id)
        
        # Add schedules
        added = 0
        for schedule in schedules:
            if self.add_schedule_job(schedule):
                added += 1
        
        logger.info(f"Synced {added} schedules from database")
        return {'added': added}
    
    def sync_schedules_from_api(self) -> Dict[str, int]:
        """
        Fetch schedules from API and sync to database.
        
        Returns:
            Dict with sync statistics
        """
        logger.info("Syncing schedules from API...")
        
        try:
            response = requests.get(API_URL, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            payload = response.json()
            api_schedules = payload.get("data", [])
            
            # Sync to database
            stats = self.schedule_repo.sync_from_api(api_schedules)
            
            logger.info(
                f"API sync completed: {stats['created']} created, "
                f"{stats['updated']} updated, {stats['skipped']} skipped"
            )
            return stats
            
        except Exception as e:
            logger.error(f"Failed to sync schedules from API: {e}")
            return {'created': 0, 'updated': 0, 'skipped': 0}
    
    def handle_schedule_changes(self, changes: Dict):
        """
        Handle schedule changes detected by watcher.
        
        Args:
            changes: Dict with 'added', 'modified', 'removed' sets
        """
        # Handle removed schedules
        for schedule_id in changes['removed']:
            schedule = self.schedule_watcher.get_schedule_details(schedule_id)
            if schedule:
                self.remove_schedule_job(schedule_id, schedule['domain'])
        
        # Handle added schedules
        for schedule_id in changes['added']:
            schedule = self.schedule_watcher.get_schedule_details(schedule_id)
            if schedule:
                self.add_schedule_job(schedule)
        
        # Handle modified schedules (remove and re-add)
        for schedule_id in changes['modified']:
            schedule = self.schedule_watcher.get_schedule_details(schedule_id)
            if schedule:
                self.remove_schedule_job(schedule_id, schedule['domain'])
                self.add_schedule_job(schedule)
    
    def start(self):
        """Start the enhanced scheduler."""
        logger.info("Starting enhanced scheduler...")
        
        # Start APScheduler
        self.scheduler.start()
        
        # Initial delay
        time.sleep(5)
        
        # Sync from API if enabled
        if self.enable_api_sync:
            self.sync_schedules_from_api()
        
        # Load schedules from database
        self.sync_schedules_from_database()
        
        # Initialize schedule watcher
        self.schedule_watcher.initialize_from_database()
        
        logger.info("Enhanced scheduler started successfully")
    
    def run(self):
        """Run the scheduler (blocking)."""
        self.start()
        
        try:
            while True:
                # Periodic API sync if enabled
                if self.enable_api_sync:
                    time.sleep(self.api_sync_interval)
                    self.sync_schedules_from_api()
                    self.sync_schedules_from_database()
                else:
                    # Check for schedule changes
                    time.sleep(self.schedule_check_interval)
                    changes = self.schedule_watcher.check_once()
                    if any(changes.values()):
                        self.handle_schedule_changes(changes)
                        
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down enhanced scheduler...")
            self.scheduler.shutdown()
            self.redis_client.close()
            self.db.close_all_connections()
            logger.info("Enhanced scheduler stopped")


def run_enhanced_scheduler():
    """Main entry point for enhanced scheduler."""
    scheduler = EnhancedScheduler()
    scheduler.run()


if __name__ == "__main__":
    run_enhanced_scheduler()
