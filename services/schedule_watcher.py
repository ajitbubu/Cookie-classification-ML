"""
Schedule watcher for dynamic schedule updates.

This module monitors the database for schedule changes and updates
APScheduler jobs dynamically without requiring service restart.
"""

import logging
import time
import hashlib
import json
from typing import Dict, Set, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ScheduleWatcher:
    """
    Watches for schedule changes in the database and updates APScheduler dynamically.
    
    Monitors schedules in the database and detects changes (additions, updates, deletions)
    to update the scheduler without requiring a service restart.
    """
    
    def __init__(
        self,
        schedule_repository,
        check_interval: int = 60
    ):
        """
        Initialize schedule watcher.
        
        Args:
            schedule_repository: ScheduleRepository instance
            check_interval: How often to check for changes (seconds)
        """
        self.schedule_repo = schedule_repository
        self.check_interval = check_interval
        self.schedule_hashes: Dict[str, str] = {}  # schedule_id -> hash
        self.last_check: Optional[datetime] = None
        logger.info(f"ScheduleWatcher initialized (check_interval={check_interval}s)")
    
    def _compute_schedule_hash(self, schedule: Dict) -> str:
        """
        Compute hash of schedule configuration.
        
        Args:
            schedule: Schedule dict
            
        Returns:
            Hash string
        """
        # Include fields that affect job scheduling
        relevant_fields = {
            'domain': schedule.get('domain'),
            'frequency': schedule.get('frequency'),
            'time_config': schedule.get('time_config'),
            'enabled': schedule.get('enabled'),
            'profile_id': schedule.get('profile_id')
        }
        
        # Convert to JSON string and hash
        json_str = json.dumps(relevant_fields, sort_keys=True)
        return hashlib.md5(json_str.encode()).hexdigest()
    
    def detect_changes(self) -> Dict[str, Set[str]]:
        """
        Detect schedule changes since last check.
        
        Returns:
            Dict with sets of schedule_ids for 'added', 'modified', 'removed'
        """
        changes = {
            'added': set(),
            'modified': set(),
            'removed': set()
        }
        
        try:
            # Get current schedules from database
            current_schedules = self.schedule_repo.get_all_schedules(enabled_only=False)
            current_ids = set()
            current_hashes = {}
            
            for schedule in current_schedules:
                schedule_id = schedule['schedule_id']
                current_ids.add(schedule_id)
                
                # Compute hash of current schedule
                schedule_hash = self._compute_schedule_hash(schedule)
                current_hashes[schedule_id] = schedule_hash
                
                # Check if schedule is new or modified
                if schedule_id not in self.schedule_hashes:
                    changes['added'].add(schedule_id)
                elif self.schedule_hashes[schedule_id] != schedule_hash:
                    changes['modified'].add(schedule_id)
            
            # Check for removed schedules
            previous_ids = set(self.schedule_hashes.keys())
            changes['removed'] = previous_ids - current_ids
            
            # Update stored hashes
            self.schedule_hashes = current_hashes
            self.last_check = datetime.utcnow()
            
            # Log changes
            if any(changes.values()):
                logger.info(
                    f"Schedule changes detected: "
                    f"{len(changes['added'])} added, "
                    f"{len(changes['modified'])} modified, "
                    f"{len(changes['removed'])} removed"
                )
            
            return changes
            
        except Exception as e:
            logger.error(f"Error detecting schedule changes: {e}")
            return changes
    
    def get_schedule_details(self, schedule_id: str) -> Optional[Dict]:
        """
        Get full schedule details from database.
        
        Args:
            schedule_id: Schedule ID
            
        Returns:
            Schedule dict or None
        """
        try:
            return self.schedule_repo.get_schedule(schedule_id)
        except Exception as e:
            logger.error(f"Error getting schedule {schedule_id}: {e}")
            return None
    
    def initialize_from_database(self) -> Dict[str, int]:
        """
        Initialize watcher state from current database schedules.
        
        Returns:
            Dict with count of schedules loaded
        """
        try:
            schedules = self.schedule_repo.get_all_schedules(enabled_only=False)
            
            for schedule in schedules:
                schedule_id = schedule['schedule_id']
                schedule_hash = self._compute_schedule_hash(schedule)
                self.schedule_hashes[schedule_id] = schedule_hash
            
            self.last_check = datetime.utcnow()
            
            logger.info(f"Initialized watcher with {len(schedules)} schedules")
            return {'loaded': len(schedules)}
            
        except Exception as e:
            logger.error(f"Error initializing watcher from database: {e}")
            return {'loaded': 0}
    
    def watch(self, callback_fn):
        """
        Start watching for schedule changes (blocking).
        
        Args:
            callback_fn: Function to call when changes detected.
                        Should accept changes dict as parameter.
        """
        logger.info("Starting schedule watcher...")
        
        # Initialize from database
        self.initialize_from_database()
        
        try:
            while True:
                time.sleep(self.check_interval)
                
                # Detect changes
                changes = self.detect_changes()
                
                # Call callback if there are changes
                if any(changes.values()):
                    try:
                        callback_fn(changes)
                    except Exception as e:
                        logger.error(f"Error in watcher callback: {e}")
                        
        except (KeyboardInterrupt, SystemExit):
            logger.info("Schedule watcher stopped")
    
    def check_once(self) -> Dict[str, Set[str]]:
        """
        Perform a single check for changes.
        
        Returns:
            Dict with sets of schedule_ids for 'added', 'modified', 'removed'
        """
        return self.detect_changes()


# Singleton instance
_schedule_watcher: Optional[ScheduleWatcher] = None


def get_schedule_watcher() -> ScheduleWatcher:
    """Get the global schedule watcher instance."""
    global _schedule_watcher
    if _schedule_watcher is None:
        raise RuntimeError(
            "Schedule watcher not initialized. Call init_schedule_watcher() first."
        )
    return _schedule_watcher


def init_schedule_watcher(
    schedule_repository,
    check_interval: int = 60
) -> ScheduleWatcher:
    """
    Initialize the global schedule watcher instance.
    
    Args:
        schedule_repository: ScheduleRepository instance
        check_interval: How often to check for changes (seconds)
        
    Returns:
        ScheduleWatcher instance
    """
    global _schedule_watcher
    _schedule_watcher = ScheduleWatcher(schedule_repository, check_interval)
    return _schedule_watcher
